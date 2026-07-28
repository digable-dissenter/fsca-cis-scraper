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


@cli.command("scrape-fsp")
@click.option("--name", type=str, default=None, help="FSP Name (partial match).")
@click.option("--fsp-no", type=str, default=None, help="Specific FSP Number.")
def scrape_fsp(name: str | None, fsp_no: str | None) -> None:
    """Search and scrape FAIS FSP details."""
    from fsca_scraper.database import get_engine, get_session, create_tables
    from fsca_scraper.scraper import search_and_scrape_fsps

    engine = get_engine()
    create_tables(engine)
    session = get_session(engine)
    try:
        search_and_scrape_fsps(session, name=name, fsp_no=fsp_no)
    finally:
        session.close()


@cli.command("verify-experience")
@click.option("--fsp-no", type=str, required=True, help="FSP Number to verify.")
@click.option("--ki-exp", type=int, default=0, help="Actual experience of Key Individuals in months.")
@click.option("--rep-exp", type=int, default=0, help="Actual experience of Representatives in months.")
def verify_experience(fsp_no: str, ki_exp: int, rep_exp: int) -> None:
    """Verify FSP personnel experience compliance against approved products."""
    from fsca_scraper.database import get_engine, get_session, Fsp
    from fsca_scraper.experience import validate_experience, ADVICE, INTERMEDIARY
    from rich.table import Table
    from rich.console import Console

    console = Console()
    engine = get_engine()
    session = get_session(engine)

    try:
        fsp = session.query(Fsp).filter_by(fsp_no=fsp_no).first()
        if not fsp:
            console.print(f"[red]FSP No {fsp_no} not found in database. Run 'scrape-fsp' first.[/red]")
            return

        console.print(f"\n[bold]Experience Compliance Report for FSP {fsp_no}: {fsp.name}[/bold]")
        console.print(f"Key Individual Actual Experience: [cyan]{ki_exp} months[/cyan]")
        console.print(f"Representative Actual Experience: [cyan]{rep_exp} months[/cyan]\n")

        # 1. General FSP Approved Products Table
        if fsp.approved_products:
            table = Table(title="FSP Approved Products and Experience Validation (BN 194 of 2017)")
            table.add_column("Category", style="cyan")
            table.add_column("Product", style="magenta")
            table.add_column("Service Type", style="yellow")
            table.add_column("Required (Months)", justify="right")
            table.add_column("KI Status", justify="center")
            table.add_column("Rep Status", justify="center")

            for prod in fsp.approved_products:
                has_advice = prod.advice_automated or prod.advice_non_automated
                has_intermediary = prod.intermediary_scripted or prod.intermediary_other
                
                # If all are False (e.g. category header or generic approval), check both
                if not has_advice and not has_intermediary:
                    has_advice = True
                    has_intermediary = True

                if has_advice:
                    ki_ok, ki_req = validate_experience(prod.category, prod.product_name, ADVICE, ki_exp)
                    rep_ok, rep_req = validate_experience(prod.category, prod.product_name, ADVICE, rep_exp)
                    
                    ki_status = "[green]PASS[/green]" if ki_ok else f"[red]FAIL ({ki_exp}/{ki_req}m)[/red]"
                    rep_status = "[green]PASS[/green]" if rep_ok else f"[red]FAIL ({rep_exp}/{rep_req}m)[/red]"
                    
                    table.add_row(
                        prod.category,
                        prod.product_name,
                        "Advice",
                        str(ki_req),
                        ki_status,
                        rep_status
                    )
                
                if has_intermediary:
                    ki_ok, ki_req = validate_experience(prod.category, prod.product_name, INTERMEDIARY, ki_exp)
                    rep_ok, rep_req = validate_experience(prod.category, prod.product_name, INTERMEDIARY, rep_exp)
                    
                    ki_status = "[green]PASS[/green]" if ki_ok else f"[red]FAIL ({ki_exp}/{ki_req}m)[/red]"
                    rep_status = "[green]PASS[/green]" if rep_ok else f"[red]FAIL ({rep_exp}/{rep_req}m)[/red]"
                    
                    table.add_row(
                        prod.category,
                        prod.product_name,
                        "Intermediary",
                        str(ki_req),
                        ki_status,
                        rep_status
                    )

            console.print(table)

        # 2. Detailed Key Individuals Table
        if fsp.key_individuals:
            console.print("\n[bold]Key Individuals Experience Compliance (BN 194 of 2017)[/bold]")
            ki_table = Table()
            ki_table.add_column("Key Individual", style="cyan")
            ki_table.add_column("Class of Business", style="magenta")
            ki_table.add_column("Category", style="yellow")
            ki_table.add_column("Required (Months)", justify="right")
            ki_table.add_column("Status", justify="center")

            for ki in fsp.key_individuals:
                if ki.cobs:
                    for cob in ki.cobs:
                        cats = []
                        if cob.category_i: cats.append("Category I")
                        if cob.category_ii: cats.append("Category II")
                        if cob.category_iia: cats.append("Category IIA")
                        if cob.category_iii: cats.append("Category III")
                        if cob.category_iv: cats.append("Category IV")
                        
                        for cat in cats:
                            req_months = 12
                            ki_ok = ki_exp >= req_months
                            status = "[green]PASS[/green]" if ki_ok else f"[red]FAIL ({ki_exp}/{req_months}m)[/red]"
                            
                            ki_table.add_row(
                                f"{ki.full_names} {ki.surname}",
                                cob.cob_description,
                                cat,
                                str(req_months),
                                status
                            )
                else:
                    ki_table.add_row(
                        f"{ki.full_names} {ki.surname}",
                        "General Category/Oversight",
                        "N/A",
                        "12",
                        "[green]PASS[/green]" if ki_exp >= 12 else f"[red]FAIL ({ki_exp}/12m)[/red]"
                    )
            console.print(ki_table)

        # 2b. Sole Proprietors Table
        if fsp.sole_proprietors:
            console.print("\n[bold]Sole Proprietors Experience Compliance (BN 194 of 2017)[/bold]")
            sp_table = Table()
            sp_table.add_column("Sole Proprietor", style="cyan")
            sp_table.add_column("Category", style="yellow")
            sp_table.add_column("Product", style="magenta")
            sp_table.add_column("Service Type", style="yellow")
            sp_table.add_column("Required (Months)", justify="right")
            sp_table.add_column("KI Status (12m limit)", justify="center")
            sp_table.add_column("Rep Status", justify="center")

            for sp in fsp.sole_proprietors:
                if sp.products:
                    for rp in sp.products:
                        cat_str = f"Category {rp.category}"
                        if rp.category == "20":
                            cat_str = "Category IIA"
                        elif rp.category == "4":
                            cat_str = "Category IV"
                        
                        ki_ok = ki_exp >= 12
                        ki_status = "[green]PASS[/green]" if ki_ok else f"[red]FAIL ({ki_exp}/12m)[/red]"
                        
                        if rp.advice:
                            ok, req_m = validate_experience(cat_str, rp.product_name, ADVICE, rep_exp)
                            rep_status = "[green]PASS[/green]" if ok else f"[red]FAIL ({rep_exp}/{req_m}m)[/red]"
                            sp_table.add_row(
                                f"{sp.full_names} {sp.surname}",
                                cat_str,
                                rp.product_name,
                                "Advice",
                                str(req_m),
                                ki_status,
                                rep_status
                            )
                        if rp.intermediary_scripted or rp.intermediary_other:
                            ok, req_m = validate_experience(cat_str, rp.product_name, INTERMEDIARY, rep_exp)
                            rep_status = "[green]PASS[/green]" if ok else f"[red]FAIL ({rep_exp}/{req_m}m)[/red]"
                            sp_table.add_row(
                                f"{sp.full_names} {sp.surname}",
                                cat_str,
                                rp.product_name,
                                "Intermediary",
                                str(req_m),
                                ki_status,
                                rep_status
                            )
                else:
                    for prod in fsp.approved_products:
                        ki_ok = ki_exp >= 12
                        ki_status = "[green]PASS[/green]" if ki_ok else f"[red]FAIL ({ki_exp}/12m)[/red]"
                        
                        ok, req_m = validate_experience(prod.category, prod.product_name, ADVICE, rep_exp)
                        rep_status = "[green]PASS[/green]" if ok else f"[red]FAIL ({rep_exp}/{req_m}m)[/red]"
                        
                        sp_table.add_row(
                            f"{sp.full_names} {sp.surname}",
                            prod.category,
                            prod.product_name,
                            "General Advice",
                            str(req_m),
                            ki_status,
                            rep_status
                        )
            console.print(sp_table)

        # 3. Detailed Representatives Table
        if fsp.representatives:
            console.print("\n[bold]Representatives Experience Compliance (BN 194 of 2017)[/bold]")
            rep_table = Table()
            rep_table.add_column("Representative", style="cyan")
            rep_table.add_column("Category", style="yellow")
            rep_table.add_column("Product", style="magenta")
            rep_table.add_column("Service Type", style="yellow")
            rep_table.add_column("Required (Months)", justify="right")
            rep_table.add_column("Status", justify="center")
            rep_table.add_column("Supervision", justify="center")

            for rep in fsp.representatives:
                if rep.products:
                    for rp in rep.products:
                        cat_str = f"Category {rp.category}"
                        if rp.category == "20":
                            cat_str = "Category IIA"
                        elif rp.category == "4":
                            cat_str = "Category IV"
                        
                        if rp.advice:
                            ok, req_m = validate_experience(cat_str, rp.product_name, ADVICE, rep_exp)
                            status = "[green]PASS[/green]" if ok else f"[red]FAIL ({rep_exp}/{req_m}m)[/red]"
                            supervision = "[yellow]YES[/yellow]" if rp.under_supervision else "NO"
                            rep_table.add_row(
                                f"{rep.full_names} {rep.surname}",
                                cat_str,
                                rp.product_name,
                                "Advice",
                                str(req_m),
                                status,
                                supervision
                            )
                        if rp.intermediary_scripted or rp.intermediary_other:
                            ok, req_m = validate_experience(cat_str, rp.product_name, INTERMEDIARY, rep_exp)
                            status = "[green]PASS[/green]" if ok else f"[red]FAIL ({rep_exp}/{req_m}m)[/red]"
                            supervision = "[yellow]YES[/yellow]" if rp.under_supervision else "NO"
                            rep_table.add_row(
                                f"{rep.full_names} {rep.surname}",
                                cat_str,
                                rp.product_name,
                                "Intermediary",
                                str(req_m),
                                status,
                                supervision
                            )
                else:
                    for prod in fsp.approved_products:
                        cat_str = prod.category
                        ok, req_m = validate_experience(cat_str, prod.product_name, ADVICE, rep_exp)
                        status = "[green]PASS[/green]" if ok else f"[red]FAIL ({rep_exp}/{req_m}m)[/red]"
                        rep_table.add_row(
                            f"{rep.full_names} {rep.surname}",
                            cat_str,
                            prod.product_name,
                            "General Advice",
                            str(req_m),
                            status,
                            "N/A"
                        )
            console.print(rep_table)

    finally:
        session.close()


@cli.command("serve")
@click.option("--host", type=str, default="127.0.0.1", help="Host address to bind to.")
@click.option("--port", type=int, default=8000, help="Port to listen on.")
def serve(host: str, port: int) -> None:
    """Start the FastAPI Analytics & Geolocator web server."""
    import uvicorn
    click.echo(f"Starting server on http://{host}:{port}")
    uvicorn.run("fsca_scraper.app:app", host=host, port=port, reload=True)

