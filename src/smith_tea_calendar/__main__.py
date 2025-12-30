import asyncio

import click

from .scraper import ScraperConfig, SmithTeaScraper


@click.command(context_settings={"auto_envvar_prefix": "SMITH_TEA"})
@click.option("--email", required=True)
@click.option("--password", required=True)
@ScraperConfig.add_options
@click.pass_context
def cli(ctx: click.Context, **kwargs) -> None:
    async def run():
        scraper = SmithTeaScraper()
        async for event in scraper.run(ctx):
            print(event)

    asyncio.run(run())


if __name__ == "__main__":
    cli()
