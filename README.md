# 🍵 smith-tea-calendar
This program creates an iCal file containing upcoming 
[Smith Tea](https://smithtea.com) subscription renewals by scraping your
account details. I wrote this program because I wanted a better way to track
when my orders would renew by tracking that information in my calendar.

## Usage
This program uses Playwright to scrape the website. You will need to use
Playwright to install a headless Chromium browser to perform the scraping.

```bash
$ uvx playwright install chromium
```

Once complete, you can run the program as follows:

```bash
$ SMITH_TEA_EMAIL="..." SMITH_TEA_PASSWORD="..." uvx smith-tea-calendar
```

All arguments can be specified as environment variables with the `SMITH_TEA_`
prefix. It's generally safer to specify credentials this way as environmment
variables aren't visible to other programs and users.

If at any point the website is update and the built-in CSS selectors used to 
navigate the site break, you can use any of the `--selector-*` flags to change
these selectors. For a full listing of options, just use the `--help` flag.
