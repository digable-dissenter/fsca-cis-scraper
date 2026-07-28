import asyncio
import httpx
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
    Fsp,
    FspComplianceOfficer,
    FspRepresentative,
    FspKeyIndividual,
    FspApprovedProduct,
    FspRepresentativeProduct,
    FspKeyIndividualClassOfBusiness,
    FspKeyIndividualCrypto,
    FspSoleProprietor,
    FspSoleProprietorProduct,
)
from fsca_scraper.parser import (
    parse_manco_list,
    parse_manco_details,
    parse_manco_schemes,
    parse_portfolios,
    parse_fsp_search_results,
    parse_fsp_details,
    parse_rep_products,
    parse_ki_cob,
    parse_fsp_reps,
    parse_fsp_sole_proprietors,
    parse_reps_pagination,
    has_next_page,
)
from fsca_scraper.experience import get_product_codes
from fsca_scraper.schemas import FspDetailsSchema

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


async def fetch_all_manco_ids_async(client: httpx.AsyncClient) -> list[str]:
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

        r = await make_async_request_with_retry(client, BASE_URL, method="POST", data=payload)
        if r:
            ids = parse_manco_list(r.text)
            console.print(f"  Found {len(ids)} management companies.")
            manco_ids.update(ids)
        else:
            console.print(f"[red]Failed to retrieve {cat_desc} management companies list.[/red]")

    return sorted(list(manco_ids), key=lambda x: int(x) if x.isdigit() else x)


def fetch_all_manco_ids() -> list[str]:
    """Retrieve all unique Manco Numbers (Synchronous Wrapper)."""
    async def run():
        async with httpx.AsyncClient() as client:
            return await fetch_all_manco_ids_async(client)
    return run_async(run())


async def scrape_manco_data(client: httpx.AsyncClient, manco_id: str, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        console.print(f"Scraping Manco details for [cyan]{manco_id}[/cyan]...")
        payload = {
            "Manco_No": manco_id,
            "APPNAME": "Web",
            "PRGNAME": "Display_Manco_Details",
            "ARGUMENTS": "Manco_No",
        }
        
        r = await make_async_request_with_retry(client, BASE_URL, method="POST", data=payload)
        if not r:
            return None
            
        details = parse_manco_details(r.text)
        if not details:
            return None
            
        if "manager_no" not in details:
            details["manager_no"] = manco_id
            
        schemes_data = parse_manco_schemes(r.text)
        
        # Concurrently fetch portfolios for each scheme
        portfolio_tasks = []
        for s_data in schemes_data:
            scheme_no = s_data["scheme_no"]
            p_payload = {
                "MancoNo": manco_id,
                "SchemeNo": scheme_no,
                "APPNAME": "Web",
                "PRGNAME": "Display_Portfolios",
                "ARGUMENTS": "MancoNo,SchemeNo",
            }
            portfolio_tasks.append((s_data, make_async_request_with_retry(client, BASE_URL, method="POST", data=p_payload)))
            
        if portfolio_tasks:
            results = await asyncio.gather(*[task for _, task in portfolio_tasks], return_exceptions=True)
            
            for idx, (s_data, _) in enumerate(portfolio_tasks):
                res = results[idx]
                s_data["portfolios"] = parse_portfolios(res.text) if res and not isinstance(res, Exception) else []
        else:
            for s_data, _ in portfolio_tasks:
                s_data["portfolios"] = []
                
        details["schemes"] = schemes_data
        return details


def save_manco_details_to_db(session: Session, data: dict) -> tuple[ManagementCompany, int, int]:
    from fsca_scraper.schemas import split_physical_address
    l1, l2, l3, l4, pc = split_physical_address(data.get("physical_address"))
    
    manco = session.query(ManagementCompany).filter_by(manager_no=data["manager_no"]).first()
    if not manco:
        manco = ManagementCompany(
            manager_no=data["manager_no"],
            name=data.get("name", "Unknown"),
            company_type=data.get("company_type"),
            company_no=data.get("company_no"),
            local_foreign=data.get("local_foreign"),
            physical_address=data.get("physical_address"),
            address_line_1=l1,
            address_line_2=l2,
            address_line_3=l3,
            address_line_4=l4,
            postal_code=pc,
            telephone=data.get("telephone"),
            fax=data.get("fax"),
            email=data.get("email"),
            website=data.get("website"),
            fsca_url=f"{BASE_URL}?APPNAME=Web&PRGNAME=Display_Manco_Details&ARGUMENTS=Manco_No&Manco_No={data['manager_no']}",
            scraped_at=datetime.now(timezone.utc),
        )
        session.add(manco)
    else:
        manco.name = data.get("name", manco.name)
        manco.company_type = data.get("company_type", manco.company_type)
        manco.company_no = data.get("company_no", manco.company_no)
        manco.local_foreign = data.get("local_foreign", data.get("local_foreign"))
        manco.physical_address = data.get("physical_address", manco.physical_address)
        manco.address_line_1 = l1
        manco.address_line_2 = l2
        manco.address_line_3 = l3
        manco.address_line_4 = l4
        manco.postal_code = pc
        manco.telephone = data.get("telephone", manco.telephone)
        manco.fax = data.get("fax", manco.fax)
        manco.email = data.get("email", manco.email)
        manco.website = data.get("website", manco.website)
        manco.scraped_at = datetime.now(timezone.utc)
        
    session.flush()
    
    existing_schemes = {
        s.scheme_no: s for s in session.query(Scheme).filter_by(management_company_id=manco.id).all()
    }
    
    scheme_count = 0
    portfolio_count = 0
    
    for s_data in data.get("schemes", []):
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
            scheme.representative_name = s_data.get("representative_name", scheme.representative_name)
            scheme.status = s_data.get("status", scheme.status)
            scheme.scraped_at = datetime.now(timezone.utc)
            
        session.flush()
        scheme_count += 1
        
        existing_portfolios = {
            p.portfolio_no: p for p in session.query(Portfolio).filter_by(scheme_id=scheme.id).all()
        }
        
        for p_data in s_data.get("portfolios", []):
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
            portfolio_count += 1
            
    session.commit()
    return manco, scheme_count, portfolio_count


def scrape_manco_details(session: Session, manco_id: str) -> tuple[ManagementCompany | None, int, int]:
    """Fetch details, schemes, and portfolios for a single management company and save to DB."""
    async def run_single():
        async with httpx.AsyncClient() as client:
            return await scrape_manco_data(client, manco_id, asyncio.Semaphore(1))
    res_dict = run_async(run_single())
    if not res_dict:
        return None, 0, 0
    return save_manco_details_to_db(session, res_dict)


async def run_scraper_async(session: Session, limit: int | None = None, max_concurrency: int = 15):
    limits = httpx.Limits(max_keepalive_connections=max_concurrency, max_connections=max_concurrency * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        manco_ids = await fetch_all_manco_ids_async(client)
        if not manco_ids:
            console.print("[red]No management companies found to scrape.[/red]")
            return
            
        if limit:
            manco_ids = manco_ids[:limit]
            
        total_companies = len(manco_ids)
        total_schemes = 0
        total_portfolios = 0
        
        semaphore = asyncio.Semaphore(max_concurrency)
        tasks = []
        for mid in manco_ids:
            tasks.append(scrape_manco_data(client, mid, semaphore))
            
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            transient=False,
        ) as progress:
            task = progress.add_task("Scraping Mancos", total=total_companies)
            
            for future in asyncio.as_completed(tasks):
                try:
                    res_dict = await future
                    if res_dict:
                        manco, s_count, p_count = await asyncio.to_thread(save_manco_details_to_db, session, res_dict)
                        total_schemes += s_count
                        total_portfolios += p_count
                except Exception as e:
                    console.print(f"[red]Error scraping Manco: {e}[/red]")
                progress.advance(task)
                
    console.print("\n[bold green]Scraping completed successfully![/bold green]")
    console.print(f"  Management Companies scraped: [green]{total_companies}[/green]")
    console.print(f"  Schemes scraped: [green]{total_schemes}[/green]")
    console.print(f"  Portfolios scraped: [green]{total_portfolios}[/green]")


def run_scraper(limit: int | None = None) -> None:
    """Core function to run the full scraping job."""
    console.print("[bold green]Starting FSCA CIS Scraper...[/bold green]")
    engine = get_engine()
    create_tables(engine)
    session = get_session(engine)
    try:
        run_async(run_scraper_async(session, limit=limit))
    finally:
        session.close()


# Helper to check/create event loop to support nested asyncio.run or existing loop
def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
    return loop.run_until_complete(coro)


async def make_async_request_with_retry(
    client: httpx.AsyncClient, url: str, method: str = "POST", data: dict = None, max_retries: int = 4
) -> httpx.Response | None:
    headers = {
        "User-Agent": BROWSER_USER_AGENT,
        "Content-Type": "application/x-www-form-urlencoded",
    }
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                backoff_sec = (2 ** attempt) + random.uniform(0.5, 1.5)
                console.print(f"[yellow]Retrying request (attempt {attempt + 1}/{max_retries}) in {backoff_sec:.2f}s...[/yellow]")
                await asyncio.sleep(backoff_sec)
            
            if method == "POST":
                r = await client.post(url, data=data, headers=headers, timeout=30.0)
            else:
                r = await client.get(url, params=data, headers=headers, timeout=30.0)
                
            if r.status_code == 200:
                return r
            else:
                console.print(f"[yellow]Attempt {attempt + 1}: Received status code {r.status_code}[/yellow]")
        except httpx.RequestError as e:
            console.print(f"[yellow]Attempt {attempt + 1} request error: {e}[/yellow]")
    return None


async def scrape_fsp_data(client: httpx.AsyncClient, fsp_no: str, semaphore: asyncio.Semaphore) -> dict | None:
    async with semaphore:
        console.print(f"Scraping FSP Details for [cyan]{fsp_no}[/cyan]...")
        details_payload = {
            "FSP_No": fsp_no,
            "APPNAME": "Web",
            "PRGNAME": "Display Details",
            "ARGUMENTS": "FSP_No",
        }
        r = await make_async_request_with_retry(client, BASE_URL, method="POST", data=details_payload)
        if not r:
            return None
        
        details = parse_fsp_details(r.text)
        if not details:
            return None
        if "fsp_no" not in details:
            details["fsp_no"] = fsp_no
            
        reps_data_list = []
        rep_list_payload = {
            "FSP_No": fsp_no,
            "From_Count": "0",
            "To_Count": "0",
            "Total_Count": "0",
            "Search_String": "",
            "APPNAME": "Web",
            "PRGNAME": "Display_Reps",
            "ARGUMENTS": "FSP_No,From_Count,To_Count,Total_Count,Search_String",
        }
        
        has_more = True
        page_count = 0
        while has_more:
            page_count += 1
            rep_r = await make_async_request_with_retry(client, BASE_URL, method="POST", data=rep_list_payload)
            if not rep_r:
                break
            
            scraped_reps = parse_fsp_reps(rep_r.text)
            reps_data_list.extend(scraped_reps)
            
            pag = parse_reps_pagination(rep_r.text)
            next_from = pag.get("Next_From_Count")
            next_to = pag.get("Next_To_Count")
            total = pag.get("Total_Count")
            
            if next_from and next_to and has_next_page(rep_r.text) and page_count < 2:
                rep_list_payload = {
                    "FSP_No": fsp_no,
                    "Next_From_Count": next_from,
                    "Next_To_Count": next_to,
                    "Total_Count": total,
                    "Search_String": "",
                    "APPNAME": "Web",
                    "PRGNAME": "Display_Reps",
                    "ARGUMENTS": "FSP_No,Next_From_Count,Next_To_Count,Total_Count,Search_String",
                }
                await asyncio.sleep(random.uniform(0.1, 0.3))
            else:
                has_more = False

        kis = details.get("key_individuals", [])
        sole_props = details.get("sole_proprietors", [])
        
        rep_prod_tasks = []
        for rep in reps_data_list:
            if rep.get("rep_id"):
                payload = {
                    "FSP_No": fsp_no,
                    "Rep_ID_No": rep["rep_id"],
                    "APPNAME": "Web",
                    "PRGNAME": "Display_Reps_Products",
                    "ARGUMENTS": "FSP_No,Rep_ID_No",
                }
                rep_prod_tasks.append((rep, make_async_request_with_retry(client, BASE_URL, method="POST", data=payload)))
                
        ki_cob_tasks = []
        for ki in kis:
            if ki.get("ki_id"):
                payload = {
                    "FSP_No": fsp_no,
                    "KI_ID_No": ki["ki_id"],
                    "APPNAME": "Web",
                    "PRGNAME": "Display_KI_COB",
                    "ARGUMENTS": "FSP_No,KI_ID_No",
                }
                ki_cob_tasks.append((ki, make_async_request_with_retry(client, BASE_URL, method="POST", data=payload)))
                
        ki_crypto_tasks = []
        for ki in kis:
            if ki.get("ki_id"):
                payload = {
                    "FSP_No": fsp_no,
                    "KI_ID_No": ki["ki_id"],
                    "APPNAME": "Web",
                    "PRGNAME": "Display_KI_Crypto",
                    "ARGUMENTS": "FSP_No,KI_ID_No",
                }
                ki_crypto_tasks.append((ki, make_async_request_with_retry(client, BASE_URL, method="POST", data=payload)))
                
        sp_prod_tasks = []
        for sp in sole_props:
            payload = {
                "FSP_No": fsp_no,
                "APPNAME": "Web",
                "PRGNAME": "Display_Sole_Prop_Prod",
                "ARGUMENTS": "FSP_No",
            }
            sp_prod_tasks.append((sp, make_async_request_with_retry(client, BASE_URL, method="POST", data=payload)))
            
        all_futures = [task for _, task in rep_prod_tasks] + \
                      [task for _, task in ki_cob_tasks] + \
                      [task for _, task in ki_crypto_tasks] + \
                      [task for _, task in sp_prod_tasks]
                      
        if all_futures:
            results = await asyncio.gather(*all_futures, return_exceptions=True)
            
            idx = 0
            for rep, _ in rep_prod_tasks:
                res = results[idx]
                idx += 1
                rep["products"] = parse_rep_products(res.text) if res and not isinstance(res, Exception) else []
                
            for ki, _ in ki_cob_tasks:
                res = results[idx]
                idx += 1
                ki["cobs"] = parse_ki_cob(res.text) if res and not isinstance(res, Exception) else []
                
            for ki, _ in ki_crypto_tasks:
                res = results[idx]
                idx += 1
                ki["cryptos"] = parse_rep_products(res.text) if res and not isinstance(res, Exception) else []
                
            for sp, _ in sp_prod_tasks:
                res = results[idx]
                idx += 1
                sp["products"] = parse_rep_products(res.text) if res and not isinstance(res, Exception) else []
        else:
            for rep, _ in rep_prod_tasks:
                rep["products"] = []
            for ki, _ in ki_cob_tasks:
                ki["cobs"] = []
            for ki, _ in ki_crypto_tasks:
                ki["cryptos"] = []
            for sp, _ in sp_prod_tasks:
                sp["products"] = []
                
        details["representatives"] = reps_data_list
        return details


def save_fsp_details_to_db(session: Session, details_dict: dict) -> Fsp:
    validated_details = FspDetailsSchema(**details_dict)
    
    fsp = session.query(Fsp).filter_by(fsp_no=validated_details.fsp_no).first()
    if not fsp:
        fsp = Fsp(
            fsp_no=validated_details.fsp_no,
            name=validated_details.name,
            trading_name=validated_details.trading_name,
            fsp_type=validated_details.fsp_type,
            registration_number=validated_details.registration_number,
            date_authorised=validated_details.date_authorised,
            status=validated_details.status,
            physical_address=validated_details.physical_address,
            address_line_1=validated_details.address_line_1,
            address_line_2=validated_details.address_line_2,
            address_line_3=validated_details.address_line_3,
            address_line_4=validated_details.address_line_4,
            postal_code=validated_details.postal_code,
            telephone=validated_details.telephone,
            scraped_at=datetime.now(timezone.utc),
        )
        session.add(fsp)
    else:
        fsp.name = validated_details.name
        fsp.trading_name = validated_details.trading_name
        fsp.fsp_type = validated_details.fsp_type
        fsp.registration_number = validated_details.registration_number
        fsp.date_authorised = validated_details.date_authorised
        fsp.status = validated_details.status
        fsp.physical_address = validated_details.physical_address
        fsp.address_line_1 = validated_details.address_line_1
        fsp.address_line_2 = validated_details.address_line_2
        fsp.address_line_3 = validated_details.address_line_3
        fsp.address_line_4 = validated_details.address_line_4
        fsp.postal_code = validated_details.postal_code
        fsp.telephone = validated_details.telephone
        fsp.scraped_at = datetime.now(timezone.utc)
        
    session.flush()
    
    session.query(FspComplianceOfficer).filter_by(fsp_id=fsp.id).delete()
    session.query(FspRepresentative).filter_by(fsp_id=fsp.id).delete()
    session.query(FspKeyIndividual).filter_by(fsp_id=fsp.id).delete()
    session.query(FspApprovedProduct).filter_by(fsp_id=fsp.id).delete()
    session.query(FspSoleProprietor).filter_by(fsp_id=fsp.id).delete()
    
    for co_data in validated_details.compliance_officers:
        co = FspComplianceOfficer(
            fsp_id=fsp.id,
            name=co_data.name,
            telephone=co_data.telephone,
        )
        session.add(co)
        
    for rep_data in validated_details.representatives:
        rep = FspRepresentative(
            fsp_id=fsp.id,
            rep_id=rep_data.rep_id,
            full_names=rep_data.full_names,
            surname=rep_data.surname,
            ki_of_rep=rep_data.ki_of_rep,
        )
        session.add(rep)
        session.flush()
        
        for rp in rep_data.products:
            c_code, sc_code, comb_code = get_product_codes(rp.category or "", rp.product_name)
            p = FspRepresentativeProduct(
                representative_id=rep.id,
                category=rp.category,
                subcategory=rp.subcategory,
                product_name=rp.product_name,
                advice=rp.advice,
                intermediary_scripted=rp.intermediary_scripted,
                intermediary_other=rp.intermediary_other,
                under_supervision=rp.under_supervision,
                category_code=c_code,
                sub_category_code=sc_code,
                combined_code=comb_code,
            )
            session.add(p)
            
    for ki_data in validated_details.key_individuals:
        ki = FspKeyIndividual(
            fsp_id=fsp.id,
            ki_id=ki_data.ki_id,
            full_names=ki_data.full_names,
            surname=ki_data.surname,
            class_of_business=ki_data.class_of_business,
            crypto_oversee=ki_data.crypto_oversee,
        )
        session.add(ki)
        session.flush()
        
        for kc in ki_data.cobs:
            c_code, sc_code, comb_code = "", "", ""
            if kc.category_i:
                c_code, sc_code, comb_code = get_product_codes("Category I", kc.cob_description)
            elif kc.category_ii:
                c_code, sc_code, comb_code = get_product_codes("Category II", kc.cob_description)
            elif kc.category_iii:
                c_code, sc_code, comb_code = get_product_codes("Category III", kc.cob_description)
            elif kc.category_iv:
                c_code, sc_code, comb_code = get_product_codes("Category IV", kc.cob_description)
            cob = FspKeyIndividualClassOfBusiness(
                key_individual_id=ki.id,
                cob_description=kc.cob_description,
                category_i=kc.category_i,
                category_ii=kc.category_ii,
                category_iia=kc.category_iia,
                category_iii=kc.category_iii,
                category_iv=kc.category_iv,
                category_code=c_code,
                sub_category_code=sc_code,
                combined_code=comb_code,
            )
            session.add(cob)
            
        for kc in ki_data.cryptos:
            c_code, sc_code, comb_code = get_product_codes(kc.category or "", kc.product_name)
            cr = FspKeyIndividualCrypto(
                key_individual_id=ki.id,
                category=kc.category,
                subcategory=kc.subcategory,
                product_name=kc.product_name,
                advice=kc.advice,
                intermediary_scripted=kc.intermediary_scripted,
                intermediary_other=kc.intermediary_other,
                under_supervision=kc.under_supervision,
                category_code=c_code,
                sub_category_code=sc_code,
                combined_code=comb_code,
            )
            session.add(cr)

    seen_products = set()
    for p_data in validated_details.approved_products:
        prod_key = (p_data.category or "", p_data.product_name)
        if prod_key in seen_products:
            continue
        seen_products.add(prod_key)
        
        c_code, sc_code, comb_code = get_product_codes(p_data.category or "", p_data.product_name)
        p = FspApprovedProduct(
            fsp_id=fsp.id,
            category=p_data.category,
            product_name=p_data.product_name,
            advice_automated=p_data.advice_automated,
            advice_non_automated=p_data.advice_non_automated,
            intermediary_scripted=p_data.intermediary_scripted,
            intermediary_other=p_data.intermediary_other,
            category_code=c_code,
            sub_category_code=sc_code,
            combined_code=comb_code,
        )
        session.add(p)

    for sp_data in validated_details.sole_proprietors:
        sp = FspSoleProprietor(
            fsp_id=fsp.id,
            full_names=sp_data.full_names,
            surname=sp_data.surname,
            conditions_apply=sp_data.conditions_apply,
        )
        session.add(sp)
        session.flush()
        
        for rp in sp_data.products:
            c_code, sc_code, comb_code = get_product_codes(rp.category or "", rp.product_name)
            p = FspSoleProprietorProduct(
                sole_proprietor_id=sp.id,
                category=rp.category,
                subcategory=rp.subcategory,
                product_name=rp.product_name,
                advice=rp.advice,
                intermediary_scripted=rp.intermediary_scripted,
                intermediary_other=rp.intermediary_other,
                under_supervision=rp.under_supervision,
                category_code=c_code,
                sub_category_code=sc_code,
                combined_code=comb_code,
            )
            session.add(p)
    session.commit()
    return fsp


async def scrape_fsps_concurrently_async(session: Session, fsp_nos: list[str], max_concurrency: int = 15):
    semaphore = asyncio.Semaphore(max_concurrency)
    limits = httpx.Limits(max_keepalive_connections=max_concurrency, max_connections=max_concurrency * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        tasks = []
        for fno in fsp_nos:
            tasks.append(scrape_fsp_data(client, fno, semaphore))
        for future in asyncio.as_completed(tasks):
            try:
                res_dict = await future
                if res_dict:
                    await asyncio.to_thread(save_fsp_details_to_db, session, res_dict)
                    console.print(f"[bold green]Successfully scraped FSP {res_dict['fsp_no']}:[/bold green]")
                    console.print(f"  Reps: [green]{len(res_dict.get('representatives', []))}[/green]")
                    console.print(f"  KIs: [green]{len(res_dict.get('key_individuals', []))}[/green]")
                    console.print(f"  Sole Proprietors: [green]{len(res_dict.get('sole_proprietors', []))}[/green]")
                    console.print(f"  Products: [green]{len(res_dict.get('approved_products', []))}[/green]")
            except Exception as e:
                console.print(f"[red]Error scraping FSP: {e}[/red]")


def scrape_fsp_details(session: Session, fsp_no: str) -> Fsp | None:
    """Scrapes details, compliance officers, reps, KIs, and approved products for a single FSP (Synchronous Wrapper)."""
    run_async(scrape_fsps_concurrently_async(session, [fsp_no]))
    return session.query(Fsp).filter_by(fsp_no=fsp_no).first()


def search_and_scrape_fsps(session: Session, name: str = None, fsp_no: str = None) -> list[str]:
    """Search for FSPs on FSCA and scrape details for all matching results."""
    if not name and not fsp_no:
        console.print("[red]Please specify either a name or fsp_no to search.[/red]")
        return []

    console.print(f"Searching FSP registry (name={name!r}, fsp_no={fsp_no!r})...")
    payload = {
        "Search_FSP_No": fsp_no or "",
        "Search_FSP_Name": name or "",
        "Search_FSP_Postal_Code": "",
        "Search_Rep_ID": "",
        "APPNAME": "Web",
        "PRGNAME": "Display_Search_Results",
        "ARGUMENTS": "Search_FSP_No,Search_FSP_Name,Search_FSP_Postal_Code,Search_Rep_ID",
        "bSubmit": "Submit",
    }

    async def get_search_results():
        async with httpx.AsyncClient() as client:
            return await make_async_request_with_retry(client, BASE_URL, method="POST", data=payload)

    r = run_async(get_search_results())
    if not r:
        console.print("[red]FSP search request failed.[/red]")
        return []

    fsp_ids = parse_fsp_search_results(r.text)
    if not fsp_ids:
        parsed_direct = parse_fsp_details(r.text)
        if parsed_direct and parsed_direct.get("fsp_no"):
            fsp_id = parsed_direct["fsp_no"]
            console.print(f"Direct match found for FSP No: {fsp_id}")
            scrape_fsp_details(session, fsp_id)
            return [fsp_id]
        console.print("[yellow]No matching FSPs found.[/yellow]")
        return []

    console.print(f"Found [cyan]{len(fsp_ids)}[/cyan] matching FSPs: {fsp_ids}")
    run_async(scrape_fsps_concurrently_async(session, fsp_ids))
    return fsp_ids
