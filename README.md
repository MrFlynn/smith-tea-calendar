# 🍵 smith-tea-calendar
This program creates an iCal file containing upcoming 
[Smith Tea](https://smithtea.com) subscription renewals by scraping your
account details. I wrote this program because I wanted a better way to track
when my orders would renew by tracking that information in my calendar.

## Usage
All arguments can be specified as environment variables with the `SMITH_TEA_`
prefix. It's generally safer to specify credentials this way as environmment
variables aren't generally visible to other programs and users.

If at any point the website is updated and the built-in CSS selectors used to
navigate the site break, you can use any of the `--selector-*` flags to change
them. For a full listing of options, including all selector flags, use the
`--help` flag.

### With `uv`
This program uses Playwright to scrape you orders. You will need to first run
Playwright to install a headless Chromium browser before using the tool the
first time.

```bash
$ uvx playwright install chromium
```

Once chromium has been installed, you can run the program as follows:

```bash
$ uvx smith-tea-calendar --email "..." --password "..."
```

### With `docker`
Alternatively, you can run the tool inside a Docker image. This may be useful
if you want to run this as periodic job in a container-native environment.

```bash
# Or clone the repository and use that copy of the script.
$ mkdir -p scripts/; curl -o scripts/entrypoint.sh \
    https://raw.githubusercontent.com/mrflynn/smith-tea-calendar/refs/heads/main/scripts/entrypoint.sh

$ docker run --entrypoint /entrypoint.sh \
    -v ./scripts/entrypoint.sh:/entrypoint.sh:ro \
    -v $(pwd):/data \
    -e SMITH_TEA_EMAIL="..." -e SMITH_TEA_PASSWORD="..." \
    --ipc host \
    mcr.microsoft.com/playwright/python:v1.57.0 /data/orders.ics
```

Microsoft has some additional recommendations for running Playwright in a
Docker container, the docs for which can be found
[here](https://playwright.dev/python/docs/docker).
