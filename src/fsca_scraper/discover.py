import sys
from pathlib import Path

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from rich.console import Console
from rich.panel import Panel

from fsca_scraper.config import (
    DISCOVERY_DIR,
    SEARCH_URL,
    BROWSER_USER_AGENT,
    PAGE_LOAD_TIMEOUT_MS,
)

console = Console()


def save_html(content: str, filename: str) -> Path:
    DISCOVERY_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DISCOVERY_DIR / filename
    filepath.write_text(content, encoding="utf-8")
    console.print(f"  Saved: [green]{filepath}[/green]")
    return filepath


def extract_links(page) -> list[dict]:
    return page.evaluate("""
        () => {
            return Array.from(document.querySelectorAll('a[href]')).map(a => ({
                text: a.textContent.trim(),
                href: a.href
            }));
        }
    """)


def run_discovery() -> None:
    console.print(Panel("FSCA CIS Portal - Discovery", style="bold cyan"))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(user_agent=BROWSER_USER_AGENT)
        page = context.new_page()
        page.set_default_timeout(PAGE_LOAD_TIMEOUT_MS)

        try:
            console.print("\n[bold]Step 1:[/bold] Navigating to search page...")
            page.goto(SEARCH_URL, wait_until="networkidle")
            save_html(page.content(), "00_search_form.html")

            form_fields = page.evaluate("""
                () => {
                    const form = document.querySelector('form');
                    if (!form) return [];
                    return Array.from(form.elements).map(el => ({
                        name: el.name,
                        type: el.type,
                        tag: el.tagName,
                        value: el.value
                    }));
                }
            """)
            console.print("  Form fields:")
            for field in form_fields:
                console.print(f"    {field}")

            console.print("\n[bold]Step 2:[/bold] Submitting search (all results)...")
            submit_button = page.query_selector(
                'input[type="submit"], button[type="submit"]'
            )
            if submit_button:
                submit_button.click()
            else:
                console.print("  [yellow]No submit button, using form.submit()[/yellow]")
                page.evaluate("document.querySelector('form').submit()")

            page.wait_for_load_state("networkidle")
            console.print(f"  Results URL: [blue]{page.url}[/blue]")
            save_html(page.content(), "01_search_results.html")

            console.print("\n[bold]Step 3:[/bold] Analyzing result links...")
            links = extract_links(page)
            mgrqispi_links = [
                link for link in links if "mgrqispi" in link.get("href", "").lower()
            ]

            console.print(f"  Total links: {len(links)}")
            console.print(f"  Portal links: {len(mgrqispi_links)}")
            for link in mgrqispi_links[:10]:
                console.print(
                    f"    [cyan]{link['text'][:60]}[/cyan] -> {link['href']}"
                )
            if len(mgrqispi_links) > 10:
                console.print(f"    ... and {len(mgrqispi_links) - 10} more")

            if not mgrqispi_links:
                console.print("  [yellow]No portal links found. All links:[/yellow]")
                for link in links:
                    console.print(f"    {link['text'][:60]} -> {link['href']}")
                return

            first_link = mgrqispi_links[0]
            console.print(
                f"\n[bold]Step 4:[/bold] Clicking: [cyan]{first_link['text'][:60]}[/cyan]"
            )
            page.goto(first_link["href"], wait_until="networkidle")
            console.print(f"  Detail URL: [blue]{page.url}[/blue]")
            save_html(page.content(), "02_company_detail.html")

            detail_links = extract_links(page)
            detail_portal_links = [
                link
                for link in detail_links
                if "mgrqispi" in link.get("href", "").lower()
            ]
            console.print(
                f"  Detail page portal links ({len(detail_portal_links)}):"
            )
            for link in detail_portal_links:
                console.print(
                    f"    [cyan]{link['text'][:80]}[/cyan] -> {link['href']}"
                )

            download_links = [
                link
                for link in detail_links
                if any(
                    kw in link.get("text", "").lower()
                    for kw in ("download", "spreadsheet")
                )
                or any(
                    ext in link.get("href", "").lower()
                    for ext in (".xls", ".csv", ".xlsx")
                )
            ]
            if download_links:
                console.print("  Spreadsheet downloads:")
                for link in download_links:
                    console.print(
                        f"    [green]{link['text']}[/green] -> {link['href']}"
                    )

        except PlaywrightTimeout as e:
            console.print(f"\n[red]Timeout: {e}[/red]")
            save_html(page.content(), "error_page.html")
            sys.exit(1)
        except Exception as e:
            console.print(f"\n[red]Error: {e}[/red]")
            try:
                save_html(page.content(), "error_page.html")
            except Exception:
                pass
            raise
        finally:
            browser.close()

    console.print("\n[bold green]Discovery complete![/bold green]")
    console.print(f"HTML files saved in: {DISCOVERY_DIR}")
