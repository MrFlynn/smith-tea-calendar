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

from playwright.async_api import async_playwright


async def main() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()

        # Go to login page
        page = await browser.new_page()
        await page.goto("https://www.smithtea.com/account/login")
        await page.wait_for_load_state("domcontentloaded")

        print("got to login page")

        # Step 1: sign in
        await page.locator("#CustomerEmail").fill(
            os.getenv("SMITH_TEA_EMAIL", ""), force=True
        )
        await page.locator("#CustomerPassword").fill(
            os.getenv("SMITH_TEA_PASSWORD", ""),
            force=True,
        )

        await page.get_by_label("Close dialog").click(force=True)

        await page.locator("button div:has-text('Sign in')").is_visible()
        await page.locator("button div:has-text('Sign in')").click(force=True)

        await page.screenshot(path="login.png", full_page=True)

        print("signed in")

        # Step 2: navigate to orders
        await page.wait_for_load_state("domcontentloaded")
        await page.locator("a:has-text('Manage Subscriptions')").click()

        print("loading manage subscriptions")

        # Step 3: navigate to subscriptions
        await page.wait_for_load_state("domcontentloaded")
        await page.locator("a[aria-label='Future orders']").click()
        await page.wait_for_load_state("domcontentloaded")

        print("loading future orders")

        # Step 4: get subscriptions
        for order in await page.locator(".recharge-component-order-item").all():
            print(await order.locator(".recharge-heading").text_content())
            print(await order.locator(".recharge-text").text_content())
            print("---")

        await browser.close()

    return


if __name__ == "__main__":
    asyncio.run(main())
