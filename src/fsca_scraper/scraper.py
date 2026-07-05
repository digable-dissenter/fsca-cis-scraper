import random
import time
from datetime import datetime, timezone
import requests
from sqlalchemy.orm import Session
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, MofNCompleteColumn

from fsca_scraper.config import (
    BASE_URL,
    REQUEST_DELAY_MIN_SECONDS,
    REQUEST_DELAY_MAX_SECONDS,
    BROWSER_USER_AGENT,
)
from fsca_scraper.database import (
    get_engine,
    create_tables,
    get_session,
    ManagementCompany,
    Scheme,
    Portfolio,
)
from fsca_scraper.parser import (
    parse_manco_list,
    parse_manco_details,
    parse_manco_schemes,
    parse_portfolios,
)

console = Console()


def get_headers() -> dict:
    return {
        "User-Agent": BROWSER_USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
    }


def make_request_with_retry(
    url: str, method: str = "POST", data: dict = None, max_retries: int = 3
) -> requests.Response | None:
    headers = get_headers()
    for attempt in range(max_retries):
        try:
            # Random delay before every request to respect server limits
            delay = random.uniform(
                REQUEST_DELAY_MIN_SECONDS, REQUEST_DELAY_MAX_SECONDS
            )
            time.sleep(delay)

            if method == "POST":
                r = requests.post(url, data=data, headers=headers, timeout=30)
            else:
                r = requests.get(url, params=data, headers=headers, timeout=30)

            if r.status_code == 200:
                return r
            else:
                console.print(
                    f"[yellow]Attempt {attempt + 1}: Received status code {r.status_code}[/yellow]"
                )
        except requests.RequestException as e:
            console.print(f"[yellow]Attempt {attempt + 1} failed: {e}[/yellow]")

    return None


def fetch_all_manco_ids() -> list[str]:
    """Retrieve all unique Manco Numbers for both Local and Foreign managers."""
    manco_ids = set()

    for category in ["L", "F"]:
        cat_desc = "Local" if category == "L" else "Foreign"
        console.print(f"Fetching [cyan]{cat_desc}[/cyan] management companies list...")

        payload = {
            "Manco_Name": "",
            "Scheme_Name": "",
            "Company_Type": "",
            "Local_Foreign": category,
            "APPNAME": "Web",
            "PRGNAME": "Display_Results",
            "ARGUMENTS": "Manco_Name,Scheme_Name,Portfolio_Name",
            "bSubmit": "Submit",
        }

        r = make_request_with_retry(BASE_URL, method="POST", data=payload)
        if r:
            ids = parse_manco_list(r.text)
            console.print(f"  Found {len(ids)} management companies.")
            manco_ids.update(ids)
        else:
            console.print(
                f"[red]Failed to retrieve {cat_desc} management companies list.[/red]"
            )

    return sorted(list(manco_ids), key=lambda x: int(x) if x.isdigit() else x)


def scrape_manco_details(
    session: Session, manco_id: str
) -> tuple[ManagementCompany | None, int, int]:
    """Fetch details, schemes, and portfolios for a single management company and save to DB."""
    payload = {
        "Manco_No": manco_id,
        "APPNAME": "Web",
        "PRGNAME": "Display_Manco_Details",
        "ARGUMENTS": "Manco_No",
    }

    r = make_request_with_retry(BASE_URL, method="POST", data=payload)
    if not r:
        console.print(
            f"[red]Failed to fetch details for Manco No: {manco_id}[/red]"
        )
        return None, 0, 0

    html = r.text
    details = parse_manco_details(html)
    if not details:
        console.print(f"[yellow]No details parsed for Manco No: {manco_id}[/yellow]")
        return None, 0, 0

    # Ensure manager_no matches what we requested
    if "manager_no" not in details:
        details["manager_no"] = manco_id

    # Create or update ManagementCompany
    manco = (
        session.query(ManagementCompany)
        .filter_by(manager_no=details["manager_no"])
        .first()
    )
    if not manco:
        manco = ManagementCompany(
            manager_no=details["manager_no"],
            name=details.get("name", "Unknown"),
            company_type=details.get("company_type"),
            company_no=details.get("company_no"),
            local_foreign=details.get("local_foreign"),
            physical_address=details.get("physical_address"),
            telephone=details.get("telephone"),
            fax=details.get("fax"),
            email=details.get("email"),
            website=details.get("website"),
            fsca_url=f"{BASE_URL}?APPNAME=Web&PRGNAME=Display_Manco_Details&ARGUMENTS=Manco_No&Manco_No={manco_id}",
            scraped_at=datetime.now(timezone.utc),
        )
        session.add(manco)
    else:
        manco.name = details.get("name", manco.name)
        manco.company_type = details.get("company_type", manco.company_type)
        manco.company_no = details.get("company_no", manco.company_no)
        manco.local_foreign = details.get("local_foreign", manco.local_foreign)
        manco.physical_address = details.get(
            "physical_address", manco.physical_address
        )
        manco.telephone = details.get("telephone", manco.telephone)
        manco.fax = details.get("fax", manco.fax)
        manco.email = details.get("email", manco.email)
        manco.website = details.get("website", manco.website)
        manco.scraped_at = datetime.now(timezone.utc)

    session.flush()  # Populates manco.id

    # Parse and update Schemes
    schemes_data = parse_manco_schemes(html)
    scheme_count = len(schemes_data)
    portfolio_count = 0

    # Retrieve existing schemes to prevent duplicates
    existing_schemes = {
        s.scheme_no: s for s in session.query(Scheme).filter_by(management_company_id=manco.id).all()
    }

    for s_data in schemes_data:
        scheme_no = s_data["scheme_no"]
        scheme = existing_schemes.get(scheme_no)

        if not scheme:
            scheme = Scheme(
                scheme_no=scheme_no,
                name=s_data.get("name", "Unknown"),
                type_of_scheme=s_data.get("type_of_scheme"),
                representative_name=s_data.get("representative_name"),
                status=s_data.get("status"),
                management_company_id=manco.id,
                scraped_at=datetime.now(timezone.utc),
            )
            session.add(scheme)
        else:
            scheme.name = s_data.get("name", scheme.name)
            scheme.type_of_scheme = s_data.get("type_of_scheme", scheme.type_of_scheme)
            scheme.representative_name = s_data.get(
                "representative_name", scheme.representative_name
            )
            scheme.status = s_data.get("status", scheme.status)
            scheme.scraped_at = datetime.now(timezone.utc)

        session.flush()

        # Fetch Portfolios for this Scheme
        p_payload = {
            "MancoNo": manco_id,
            "SchemeNo": scheme_no,
            "APPNAME": "Web",
            "PRGNAME": "Display_Portfolios",
            "ARGUMENTS": "MancoNo,SchemeNo",
        }

        pr = make_request_with_retry(BASE_URL, method="POST", data=p_payload)
        if pr:
            portfolios_data = parse_portfolios(pr.text)
            portfolio_count += len(portfolios_data)

            # Retrieve existing portfolios to prevent duplicates
            existing_portfolios = {
                p.portfolio_no: p
                for p in session.query(Portfolio).filter_by(scheme_id=scheme.id).all()
            }

            for p_data in portfolios_data:
                p_no = p_data["portfolio_no"]
                portfolio = existing_portfolios.get(p_no)

                if not portfolio:
                    portfolio = Portfolio(
                        portfolio_no=p_no,
                        name=p_data.get("name", "Unknown"),
                        scheme_id=scheme.id,
                        scraped_at=datetime.now(timezone.utc),
                    )
                    session.add(portfolio)
                else:
                    portfolio.name = p_data.get("name", portfolio.name)
                    portfolio.scraped_at = datetime.now(timezone.utc)

    session.commit()
    return manco, scheme_count, portfolio_count


def run_scraper(limit: int | None = None) -> None:
    """Core function to run the full scraping job."""
    console.print("[bold green]Starting FSCA CIS Scraper...[/bold green]")

    engine = get_engine()
    create_tables(engine)
    session = get_session(engine)

    try:
        manco_ids = fetch_all_manco_ids()
        if not manco_ids:
            console.print("[red]No management companies found to scrape.[/red]")
            return

        if limit:
            console.print(f"[yellow]Limiting scrape to first {limit} companies.[/yellow]")
            manco_ids = manco_ids[:limit]

        total_companies = len(manco_ids)
        total_schemes = 0
        total_portfolios = 0

        console.print(
            f"Beginning scrape of {total_companies} management companies..."
        )

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=False,
        ) as progress:
            task = progress.add_task(
                "Scraping companies", total=total_companies
            )

            for manco_id in manco_ids:
                progress.update(
                    task,
                    description=f"Scraping Manco ID {manco_id}",
                )
                try:
                    manco, s_count, p_count = scrape_manco_details(
                        session, manco_id
                    )
                    if manco:
                        total_schemes += s_count
                        total_portfolios += p_count
                except Exception as e:
                    console.print(
                        f"\n[red]Error scraping Manco ID {manco_id}: {e}[/red]"
                    )
                    session.rollback()

                progress.advance(task)

        console.print("\n[bold green]Scraping completed successfully![/bold green]")
        console.print(f"  Management Companies scraped: [green]{total_companies}[/green]")
        console.print(f"  Schemes scraped: [green]{total_schemes}[/green]")
        console.print(f"  Portfolios scraped: [green]{total_portfolios}[/green]")

    finally:
        session.close()
