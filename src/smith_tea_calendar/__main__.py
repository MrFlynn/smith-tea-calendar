import asyncio
import pathlib
from datetime import date, datetime

import click
from ical.calendar import Calendar
from ical.calendar_stream import IcsCalendarStream
from ical.event import Event
from ical.exceptions import CalendarParseError

from .scraper import ScraperConfig, SmithTeaScraper


@click.command(context_settings={"auto_envvar_prefix": "SMITH_TEA"})
@click.option("--email", required=True)
@click.option("--password", required=True)
@ScraperConfig.add_options
@click.argument(
    "calendar",
    type=click.Path(
        exists=False,
        file_okay=True,
        dir_okay=False,
        readable=True,
        writable=True,
        path_type=pathlib.Path,
    ),
    default=pathlib.Path("orders.ics"),
)
@click.pass_context
def cli(ctx: click.Context, calendar: pathlib.Path, **kwargs) -> None:
    asyncio.run(run(ctx, calendar))


async def run(ctx: click.Context, calendar_file: pathlib.Path):
    scraper = SmithTeaScraper()
    calendar_file_exists = not calendar_file.exists()

    with calendar_file.open("w+") as ics_file:
        calendar = Calendar(prodid="github.com/mrflynn/smith-tea-calendar")

        if calendar_file_exists:
            try:
                calendar = IcsCalendarStream.calendar_from_ics(ics_file.read())
            except CalendarParseError:
                pass

        def event_keys(event: Event) -> tuple[date | datetime | str | None, ...]:
            return (event.dtstart, event.summary, event.description)

        calendar.events.extend(
            filter(
                lambda new_event: event_keys(new_event)
                not in {
                    event_keys(existing_event) for existing_event in calendar.events
                },
                [event async for event in scraper.run(ctx)],
            )
        )

        ics_file.seek(0)
        ics_file.write(IcsCalendarStream.calendar_to_ics(calendar))
        ics_file.truncate()


if __name__ == "__main__":
    cli()
