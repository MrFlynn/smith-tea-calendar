import itertools
import logging
import re
import sys
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime

import click
from ical.event import Event, EventStatus
from playwright.async_api import Error, Page, async_playwright, expect

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Configuration class holding CSS selectors with Click-compatible defaults."""

    login_email: str = "#CustomerEmail"
    login_password: str = "#CustomerPassword"
    sign_in_button: str = "button div:has-text('Sign in')"
    manage_subscriptions: str = "a:has-text('Manage Subscriptions')"
    future_orders: str = "a[aria-label='Future orders']"
    order_item: str = ".recharge-component-order-item"
    order_text: str = ".recharge-text"
    order_heading: str = ".recharge-heading"

    @staticmethod
    def add_options(func: Callable) -> Callable:
        """Decorator to add Click options based on ScraperConfig fields."""

        for name, default in ScraperConfig.__dataclass_fields__.items():
            option = click.option(
                f"--selector-{name.replace('_', '-')}",
                default=default.default,
                help=f"CSS selector for {name}",
            )

            func = option(func)

        return func


class SmithTeaScraper:
    """Scrape your Smith Tea account for upcoming subscription renewals"""

    def __init__(self, config: ScraperConfig | None = None) -> None:
        self.config = config or ScraperConfig()

    async def _login(self, ctx: click.Context, page: Page) -> None:
        # TODO: hack to close dialogs. Ideally we should just be able to ignore any dialogs
        # being up and just continue with waiting.
        await page.get_by_label("Close dialog").click(force=True)

        await page.locator(self.config.login_email).fill(ctx.params.get("email", ""))
        await page.locator(self.config.login_password).fill(
            ctx.params.get("password", "")
        )
        await page.locator(self.config.sign_in_button).click()

        logger.debug("Successfully logged into Smith Tea account")

    async def _goto_subscriptions(self, page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.locator(self.config.manage_subscriptions).click()

        logger.debug("Loaded subscriptions")

    async def _goto_future_orders(self, page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.locator(self.config.future_orders).click()

        # Wait for orders to be loaded on the page.
        await expect(page.locator(self.config.order_item).first).to_be_visible(
            timeout=10000
        )

        logger.debug("Loaded future orders")

    async def _extract_orders(self, page: Page) -> AsyncIterator[Event]:
        i = 0
        for i, order in enumerate(await page.locator(self.config.order_item).all()):
            try:
                summary = "Smith Tea Subscription Renewal"
                description_lines = list(
                    itertools.chain.from_iterable(
                        map(
                            lambda text: text.split("\n"),
                            await order.locator(
                                self.config.order_text
                            ).all_text_contents(),
                        )
                    )
                )

                if len(description_lines) == 1:
                    if match := re.match(
                        r"^\d+ x (.*) (?:\[.*\])?$", description_lines[0]
                    ):
                        summary = f"Smith Tea Order - {match.group(1)}"

                yield Event(
                    dtstart=datetime.strptime(
                        await order.locator(self.config.order_heading).text_content()
                        or "",
                        "%a, %B %d, %Y",
                    ).replace(tzinfo=datetime.now().astimezone().tzinfo),
                    summary=summary,
                    description="\n".join(
                        [
                            *description_lines,
                            "",
                            "Manage your order at https://www.smithtea.com/tools/recurring/login",
                        ]
                    ),
                    status=EventStatus.CONFIRMED,
                )
            except ValueError:
                logger.exception("Invalid date in recurring order")

        logger.info(f"Found {i + 1} new orders")

    async def run(self, ctx: click.Context) -> AsyncIterator[Event]:
        """
        Execute scraping. Starts a headless Chromium instance, logs into your account, navigates
        to the right page, and scrapes upcomning orders and returns them in a parsed iCal format.
        """

        # Extract ScraperConfig from context if provided via add_options
        for name in ScraperConfig.__dataclass_fields__:
            if f"selector_{name}" in ctx.params:
                setattr(self.config, name, ctx.params[f"selector_{name}"])

        logger.debug("Configured selectors", extra=self.config.__dict__)

        async with async_playwright() as playwright:
            try:
                browser = await playwright.chromium.launch()

                page = await browser.new_page()
                _ = await page.goto(
                    "https://www.smithtea.com/account/login",
                    wait_until="domcontentloaded",
                )

                logger.debug("Launched chrome and loaded login page")

                await self._login(ctx, page)
                await self._goto_subscriptions(page)
                await self._goto_future_orders(page)

                async for event in self._extract_orders(page):
                    yield event

                await browser.close()
            except Error:
                logging.critical(
                    "Error occured while scraping subscriptions. The page layout may have changed, ",
                    "so you may need to use inspect element to determine which CSS selectors to ",
                    "use so this program can correctly navigate the site. Ensure you have the ",
                    "correct credentials.",
                    exc_info=True,
                )

                sys.exit(1)
