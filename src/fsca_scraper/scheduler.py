import time
from datetime import datetime, timezone
from typing import Callable

from rich.console import Console

console = Console()


def run_on_schedule(task: Callable[[], None], interval_hours: int) -> None:
    """Run a task repeatedly at a fixed interval."""
    interval_seconds = interval_hours * 3600

    console.print(f"[bold]Scheduled mode:[/bold] running every {interval_hours} hour(s)")
    console.print("Press Ctrl+C to stop.\n")

    while True:
        start_time = datetime.now(timezone.utc)
        console.print(f"[dim]Run started at {start_time.isoformat()}[/dim]")

        try:
            task()
        except Exception as e:
            console.print(f"[red]Task failed: {e}[/red]")

        elapsed = (datetime.now(timezone.utc) - start_time).total_seconds()
        sleep_duration = max(0, interval_seconds - elapsed)

        next_run = datetime.now(timezone.utc).timestamp() + sleep_duration
        next_run_dt = datetime.fromtimestamp(next_run, tz=timezone.utc)
        console.print(f"[dim]Next run at {next_run_dt.isoformat()}[/dim]\n")

        try:
            time.sleep(sleep_duration)
        except KeyboardInterrupt:
            console.print("\n[yellow]Scheduler stopped.[/yellow]")
            break
