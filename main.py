# Notes
## Login page:
### email: id=CustomerEmail
### password: id=CustomerPassword
### button: contains div with text "Sign in"
#
## Account Page:
### Click link with text "Manage Subscriptions"
### Sometimes contains promotions, so I'll need to figure out how to handle that
#
## Future orders:
### Click a with aria-label "Future orders"
### Orders can be retrieved from class "recharge-component-order-item"
#### Date for order can be retrieved from class ".recharge-heading"
#### Order contents can be retrieved from class ".recharge-text"

import asyncio
import os
from datetime import datetime

from playwright.async_api import async_playwright, expect


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)

        # Go to login page
        page = await browser.new_page()
        _ = await page.goto(
            "https://www.smithtea.com/account/login", wait_until="domcontentloaded"
        )

        print("got to login page")

        # Step 1: sign in
        await page.get_by_label("Close dialog").click(force=True)

        await page.locator("#CustomerEmail").fill(os.getenv("SMITH_TEA_EMAIL", ""))
        await page.locator("#CustomerPassword").fill(
            os.getenv("SMITH_TEA_PASSWORD", "")
        )
        await page.locator("button div:has-text('Sign in')").click()

        print("signed in")

        # Step 2: navigate to orders
        await page.wait_for_load_state("domcontentloaded")
        await page.locator("a:has-text('Manage Subscriptions')").click()

        print("loading manage subscriptions")

        # Step 3: navigate to subscriptions
        await page.wait_for_load_state("domcontentloaded")
        await page.locator("a[aria-label='Future orders']").click()
        await expect(
            page.locator(".recharge-component-order-item").first
        ).to_be_visible(timeout=10000)

        print("loading future orders")

        # Step 4: get subscriptions
        for order in await page.locator(".recharge-component-order-item").all():
            try:
                print(
                    datetime.strptime(
                        await order.locator(".recharge-heading").text_content() or "",
                        "%a, %B %d, %Y",
                    )
                )
                print(await order.locator(".recharge-text").text_content())
                print("---")
            except ValueError:
                pass

        await browser.close()

    return


if __name__ == "__main__":
    asyncio.run(main())
