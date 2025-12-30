import argparse
import itertools
import re
from collections.abc import AsyncIterator
from datetime import datetime

from ical.event import Event, EventStatus
from playwright.async_api import Page, async_playwright, expect


class SmithTeaScraper:
    def __init__(self) -> None:
        pass

    async def _login(self, page: Page, args: argparse.Namespace) -> None:
        # TODO: hack to close dialogs. Ideally we should just be able to ignore any dialogs
        # being up and just continue with waiting.
        await page.get_by_label("Close dialog").click(force=True)

        await page.locator("#CustomerEmail").fill(args.login_email)
        await page.locator("#CustomerPassword").fill(args.login_password)
        await page.locator("button div:has-text('Sign in')").click()

    async def _goto_subscriptions(self, page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.locator("a:has-text('Manage Subscriptions')").click()

    async def _goto_future_orders(self, page: Page) -> None:
        await page.wait_for_load_state("domcontentloaded")
        await page.locator("a[aria-label='Future orders']").click()

        # Wait for orders to be loaded on the page.
        await expect(
            page.locator(".recharge-component-order-item").first
        ).to_be_visible(timeout=10000)

    async def _extract_orders(self, page: Page) -> AsyncIterator[Event]:
        for order in await page.locator(".recharge-component-order-item").all():
            try:
                summary = "Smith Tea Subscription Renewal"
                description_lines = list(
                    itertools.chain.from_iterable(
                        map(
                            lambda text: text.split("\n"),
                            await order.locator(".recharge_text").all_text_contents(),
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
                        await order.locator(".recharge-heading").text_content() or "",
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

    async def run(self, args: argparse.Namespace) -> AsyncIterator[Event]:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch()

            page = await browser.new_page()
            _ = await page.goto(
                "https://www.smithtea.com/account/login", wait_until="domcontentloaded"
            )

            await self._login(page, args)
            await self._goto_subscriptions(page)
            await self._goto_future_orders(page)

            async for event in self._extract_orders(page):
                yield event

            await browser.close()
