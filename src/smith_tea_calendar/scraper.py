import itertools
import re
from collections.abc import AsyncIterator, Callable
from dataclasses import dataclass
from datetime import datetime

import click
from ical.event import Event, EventStatus
from playwright.async_api import Page, async_playwright, expect


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

    async def _goto_subscriptions(self, page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.locator(self.config.manage_subscriptions).click()

    async def _goto_future_orders(self, page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.locator(self.config.future_orders).click()

        # Wait for orders to be loaded on the page.
        await expect(page.locator(self.config.order_item).first).to_be_visible(
            timeout=10000
        )

    async def _extract_orders(self, page: Page) -> AsyncIterator[Event]:
        for order in await page.locator(self.config.order_item).all():
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
                    ),
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
                pass

    async def run(self, ctx: click.Context) -> AsyncIterator[Event]:
        # Extract ScraperConfig from context if provided via add_options
        for name in ScraperConfig.__dataclass_fields__:
            if f"selector_{name}" in ctx.params:
                setattr(self, name, ctx.params[f"selector_{name}"])

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()

            page = await browser.new_page()
            _ = await page.goto(
                "https://www.smithtea.com/account/login", wait_until="domcontentloaded"
            )

            await self._login(ctx, page)
            await self._goto_subscriptions(page)
            await self._goto_future_orders(page)

            async for event in self._extract_orders(page):
                yield event

            await browser.close()
