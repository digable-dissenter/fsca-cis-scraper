import click

from fsca_scraper.discover import run_discovery


@click.group()
def cli() -> None:
    """FSCA Collective Investment Schemes scraper."""


@cli.command()
def discover() -> None:
    """Run discovery to capture portal HTML structure."""
    run_discovery()


@cli.command()
@click.option(
    "--schedule",
    type=int,
    default=None,
    help="Re-run every N hours.",
)
@click.option(
    "--limit",
    type=int,
    default=None,
    help="Limit to first N management companies (for testing).",
)
def scrape(schedule: int | None, limit: int | None) -> None:
    """Scrape all management companies, schemes, and portfolios."""
    from fsca_scraper.scraper import run_scraper

    if schedule:
        from fsca_scraper.scheduler import run_on_schedule

        run_on_schedule(lambda: run_scraper(limit=limit), interval_hours=schedule)
    else:
        run_scraper(limit=limit)
