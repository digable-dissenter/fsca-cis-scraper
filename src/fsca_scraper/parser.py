import re
from bs4 import BeautifulSoup


def parse_manco_list(html: str) -> list[str]:
    """Extract unique Manco Numbers from the search results page."""
    manco_ids = set()
    matches = re.findall(r"updateArguments\((\d+)\)", html)
    for m in matches:
        manco_ids.add(m)
    return sorted(list(manco_ids))


def parse_manco_details(html: str) -> dict:
    """Parse management company detail fields from the details page."""
    soup = BeautifulSoup(html, "lxml")
    details = {}

    tables = soup.find_all("table")
    if not tables:
        return details

    # Parse first table (general details)
    for row in tables[0].find_all("tr"):
        th = row.find("th")
        td = row.find("td")
        if th and td:
            key = th.text.strip().lower()
            val = td.text.strip()
            if "manager no" in key:
                details["manager_no"] = val
            elif "manager name" in key:
                details["name"] = val
            elif "company type" in key:
                details["company_type"] = val
            elif "company no" in key:
                details["company_no"] = val
            elif "local / foreign" in key:
                details["local_foreign"] = val

    # Find the contact info table
    contact_table = None
    for table in tables[1:]:
        ths = [th.text.strip().lower() for th in table.find_all("th")]
        if "physical address" in ths or "telephone no" in ths:
            contact_table = table
            break

    if contact_table:
        for row in contact_table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if th and td:
                key = th.text.strip().lower()
                if "physical address" in key:
                    # preserve newlines for cleaner addresses
                    details["physical_address"] = "\n".join(
                        [line.strip() for line in td.strings if line.strip()]
                    )
                elif "telephone no" in key:
                    details["telephone"] = td.text.strip()
                elif "fax" in key:
                    details["fax"] = td.text.strip()
                elif "email" in key:
                    details["email"] = td.text.strip()
                elif "website" in key:
                    details["website"] = td.text.strip()

    return details


def parse_manco_schemes(html: str) -> list[dict]:
    """Parse all schemes listed under a management company."""
    soup = BeautifulSoup(html, "lxml")
    schemes = []

    for table in soup.find_all("table"):
        ths = [th.text.strip().lower() for th in table.find_all("th")]
        if "scheme no" in ths and "scheme name" in ths:
            for row in table.find_all("tr")[1:]:
                tds = row.find_all("td")
                if len(tds) >= 2:
                    scheme = {}
                    for idx, th_name in enumerate(ths):
                        if idx < len(tds):
                            val = tds[idx].text.strip()
                            if "scheme no" in th_name:
                                scheme["scheme_no"] = val
                            elif "scheme name" in th_name:
                                scheme["name"] = val
                            elif "type of scheme" in th_name:
                                scheme["type_of_scheme"] = val
                            elif "representative name" in th_name:
                                scheme["representative_name"] = val
                            elif "status" in th_name:
                                scheme["status"] = val
                    if scheme.get("scheme_no"):
                        schemes.append(scheme)
            break

    return schemes


def parse_portfolios(html: str) -> list[dict]:
    """Parse all portfolios listed under a scheme's portfolio page."""
    soup = BeautifulSoup(html, "lxml")
    portfolios = []

    for table in soup.find_all("table"):
        ths = [th.text.strip().lower() for th in table.find_all("th")]
        if "portfolio no" in ths and "portfolio name" in ths:
            for row in table.find_all("tr")[1:]:
                tds = row.find_all("td")
                if len(tds) >= 2:
                    portfolio = {}
                    for idx, th_name in enumerate(ths):
                        if idx < len(tds):
                            val = tds[idx].text.strip()
                            if "portfolio no" in th_name:
                                portfolio["portfolio_no"] = val
                            elif "portfolio name" in th_name:
                                portfolio["name"] = val
                            elif "scheme no" in th_name:
                                portfolio["scheme_no"] = val
                    if portfolio.get("portfolio_no"):
                        portfolios.append(portfolio)
            break

    return portfolios


def parse_fsp_search_results(html: str) -> list[str]:
    """Extract unique FSP Numbers from the search results page."""
    fsp_ids = set()
    matches = re.findall(r"updateArguments\(\s*(\d+)\s*\)", html)
    for m in matches:
        fsp_ids.add(m)
    return sorted(list(fsp_ids), key=lambda x: int(x) if x.isdigit() else x)


def parse_fsp_details(html: str) -> dict:
    """Parse FSP details, compliance officers, reps, KIs, and approved products from HTML."""
    soup = BeautifulSoup(html, "lxml")
    details = {}

    # 1. Main Details table (first table or table containing "FSP No")
    tables = soup.find_all("table")
    main_table = None
    for t in tables:
        rows = t.find_all("tr")
        if rows:
            first_row_cells = rows[0].find_all(["td", "th"])
            if first_row_cells:
                first_cell_text = first_row_cells[0].text.strip().lower()
                if "fsp no" in first_cell_text:
                    main_table = t
                    break

    if main_table:
        for row in main_table.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                key = cells[0].text.strip().lower()
                val = cells[1].text.strip()
                if "fsp no" in key:
                    details["fsp_no"] = val
                elif "fsp name" in key:
                    details["name"] = val
                elif "fsp type" in key:
                    details["fsp_type"] = val
                elif "registration number" in key:
                    details["registration_number"] = val
                elif "date authorised" in key:
                    details["date_authorised"] = val

    # 2. Contact Info (can be inside div or table with "physical address")
    contact_div = soup.find(id="Contact_Info")
    if contact_div:
        for row in contact_div.find_all("tr"):
            cells = row.find_all("td")
            if len(cells) >= 2:
                key = cells[0].text.strip().lower()
                td_val = cells[1]
                if "physical address" in key:
                    details["physical_address"] = "\n".join(
                        [line.strip() for line in td_val.strings if line.strip()]
                    )
                elif "telephone no" in key:
                    details["telephone"] = td_val.text.strip()
    else:
        # Fallback: search all tables
        for t in tables:
            rows = t.find_all("tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 2:
                    key = cells[0].text.strip().lower()
                    if "physical address" in key:
                        details["physical_address"] = "\n".join(
                            [line.strip() for line in cells[1].strings if line.strip()]
                        )
                    elif "telephone no" in key:
                        details["telephone"] = cells[1].text.strip()

    # 3. Compliance Officers
    compliance_officers = []
    co_div = soup.find(id="ComplianceOfficers")
    co_table = None
    if co_div:
        co_table = co_div.find("table")
    if not co_table:
        for t in tables:
            rows = t.find_all("tr")
            if rows:
                headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
                if "compliance officer" in headers:
                    co_table = t
                    break

    if co_table:
        rows = co_table.find_all("tr")
        if len(rows) > 1:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            for row in rows[1:]:
                cells = row.find_all("td")
                if len(cells) >= len(headers):
                    name = cells[0].text.strip()
                    tel = cells[1].text.strip() if len(cells) > 1 else ""
                    if name:
                        compliance_officers.append({"name": name, "telephone": tel})
    details["compliance_officers"] = compliance_officers

    # 4. Representatives
    representatives = []
    rep_div = soup.find(id="Representatives")
    rep_table = None
    if rep_div:
        rep_table = rep_div.find("table")
    if not rep_table:
        for t in tables:
            rows = t.find_all("tr")
            if rows:
                headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
                if "full names" in headers and "ki of rep" in headers:
                    rep_table = t
                    break

    if rep_table:
        rows = rep_table.find_all("tr")
        if len(rows) > 1:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            for row in rows[1:]:
                cells = row.find_all("td")
                if cells:
                    rep = {}
                    for idx, h in enumerate(headers):
                        if idx < len(cells):
                            val = cells[idx].text.strip()
                            if "full names" in h:
                                rep["full_names"] = val
                            elif "surname" in h:
                                rep["surname"] = val
                            elif "ki of rep" in h:
                                rep["ki_of_rep"] = val
                    
                    # Extract rep_id from input onclick showProducts
                    onclick_elem = row.find("input", {"onclick": True})
                    if onclick_elem:
                        onclick_val = onclick_elem["onclick"]
                        m = re.search(r"showProducts\('\s*([^']+)\s*'\)", onclick_val)
                        if m:
                            rep["rep_id"] = m.group(1)
                            
                    if rep.get("full_names") or rep.get("surname"):
                        representatives.append(rep)
    details["representatives"] = representatives

    # 5. Key Individuals
    key_individuals = []
    ki_div = soup.find(id="Key_Individuals")
    ki_table = None
    if ki_div:
        ki_table = ki_div.find("table")
    if not ki_table:
        for t in tables:
            rows = t.find_all("tr")
            if rows:
                headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
                if "full names" in headers and "class of business" in headers and "type" in headers:
                    ki_table = t
                    break

    if ki_table:
        rows = ki_table.find_all("tr")
        if len(rows) > 1:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            for row in rows[1:]:
                cells = row.find_all("td")
                if cells:
                    ki = {}
                    for idx, h in enumerate(headers):
                        if idx < len(cells):
                            val = cells[idx].text.strip()
                            if "full names" in h:
                                ki["full_names"] = val
                            elif "surname" in h:
                                ki["surname"] = val
                            elif "class of business" in h:
                                ki["class_of_business"] = val
                            elif "crypto oversee" in h:
                                ki["crypto_oversee"] = val
                    
                    # Extract ki_id from input onclick showExperience/showCrypto
                    onclick_elem = row.find("input", {"onclick": True})
                    if onclick_elem:
                        onclick_val = onclick_elem["onclick"]
                        m = re.search(r"(?:showExperience|showCrypto)\('\s*([^']+)\s*'\)", onclick_val)
                        if m:
                            ki["ki_id"] = m.group(1)
                            
                    if ki.get("full_names") or ki.get("surname"):
                        key_individuals.append(ki)
    details["key_individuals"] = key_individuals

    # 6. Products Approved
    approved_products = []
    prod_div = soup.find(id="Products_Approved")
    prod_table = None
    if prod_div:
        prod_table = prod_div.find("table")
    if not prod_table:
        for t in tables:
            rows = t.find_all("tr")
            if rows:
                headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
                if "category description" in headers and "advice automated" in headers:
                    prod_table = t
                    break

    if prod_table:
        rows = prod_table.find_all("tr")
        if len(rows) > 1:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            current_category = ""
            for row in rows[1:]:
                cells = row.find_all("td")
                if cells:
                    desc = cells[0].text.strip()
                    if desc.upper().startswith("CATEGORY") or (len(cells) > 1 and all(c.text.strip() == "" for c in cells[1:])):
                        current_category = desc
                    else:
                        prod = {
                            "category": current_category,
                            "product_name": desc,
                            "advice_automated": cells[1].text.strip().upper() == "X" if len(cells) > 1 else False,
                            "advice_non_automated": cells[2].text.strip().upper() == "X" if len(cells) > 2 else False,
                            "intermediary_scripted": cells[3].text.strip().upper() == "X" if len(cells) > 3 else False,
                            "intermediary_other": cells[4].text.strip().upper() == "X" if len(cells) > 4 else False,
                        }
                        approved_products.append(prod)
    details["approved_products"] = approved_products

    # 5b. Sole Proprietors
    details["sole_proprietors"] = parse_fsp_sole_proprietors(html)

    return details


def parse_rep_products(html: str) -> list[dict]:
    """Parse representative approved products from HTML."""
    soup = BeautifulSoup(html, "lxml")
    products = []
    
    tables = soup.find_all("table")
    prod_table = None
    for t in tables:
        rows = t.find_all("tr")
        if rows:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            if "category description" in headers and any("intermediary" in h for h in headers):
                prod_table = t
                break
                
    if prod_table:
        rows = prod_table.find_all("tr")
        if len(rows) > 1:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            for row in rows[1:]:
                cells = row.find_all("td")
                if cells:
                    prod = {
                        "category": cells[0].text.strip() if len(cells) > 0 else "",
                        "subcategory": cells[1].text.strip() if len(cells) > 1 else "",
                        "product_name": cells[2].text.strip() if len(cells) > 2 else "",
                        "advice": cells[3].text.strip().upper() == "X" if len(cells) > 3 else False,
                        "intermediary_scripted": cells[4].text.strip().upper() == "X" if len(cells) > 4 else False,
                        "intermediary_other": cells[5].text.strip().upper() == "X" if len(cells) > 5 else False,
                        "under_supervision": cells[6].text.strip().upper() == "X" if len(cells) > 6 else False,
                    }
                    if prod["product_name"]:
                        products.append(prod)
    return products


def parse_ki_cob(html: str) -> list[dict]:
    """Parse Key Individual Class of Business from HTML."""
    soup = BeautifulSoup(html, "lxml")
    cobs = []
    
    tables = soup.find_all("table")
    cob_table = None
    for t in tables:
        rows = t.find_all("tr")
        if rows:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            if "class of business" in headers and any("category" in h for h in headers):
                cob_table = t
                break
                
    if cob_table:
        rows = cob_table.find_all("tr")
        if len(rows) > 1:
            for row in rows[1:]:
                desc_input = row.find("input", {"name": "COB_Description"})
                if desc_input:
                    desc_val = desc_input.get("value", "").strip()
                    if desc_val:
                        cob = {
                            "cob_description": desc_val,
                            "category_i": False,
                            "category_ii": False,
                            "category_iia": False,
                            "category_iii": False,
                            "category_iv": False,
                        }
                        checkboxes = row.find_all("input", {"type": "checkbox"})
                        for cb in checkboxes:
                            cb_name = cb.get("name", "").upper()
                            is_checked = cb.has_attr("checked")
                            if "COB_CATI_" in cb_name:
                                cob["category_i"] = is_checked
                            elif "COB_CATII_" in cb_name:
                                cob["category_ii"] = is_checked
                            elif "COB_CATIIA_" in cb_name:
                                cob["category_iia"] = is_checked
                            elif "COB_CATIII_" in cb_name:
                                cob["category_iii"] = is_checked
                            elif "COB_CATIV_" in cb_name:
                                cob["category_iv"] = is_checked
                        cobs.append(cob)
    return cobs


def parse_fsp_reps(html: str) -> list[dict]:
    """Parse representatives from the representatives list page HTML."""
    soup = BeautifulSoup(html, "lxml")
    representatives = []
    tables = soup.find_all("table")
    rep_table = None
    for t in tables:
        rows = t.find_all("tr")
        if rows:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            if "full names" in headers and "ki of rep" in headers:
                rep_table = t
                break
                
    if rep_table:
        rows = rep_table.find_all("tr")
        if len(rows) > 1:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            for row in rows[1:]:
                cells = row.find_all("td")
                if cells:
                    rep = {}
                    for idx, h in enumerate(headers):
                        if idx < len(cells):
                            val = cells[idx].text.strip()
                            if "full names" in h:
                                rep["full_names"] = val
                            elif "surname" in h:
                                rep["surname"] = val
                            elif "ki of rep" in h:
                                rep["ki_of_rep"] = val
                    
                    onclick_elem = row.find("input", {"onclick": True})
                    if onclick_elem:
                        onclick_val = onclick_elem["onclick"]
                        m = re.search(r"showProducts\('\s*([^']+)\s*'\)", onclick_val)
                        if m:
                            rep["rep_id"] = m.group(1)
                            
                    if rep.get("full_names") or rep.get("surname"):
                        representatives.append(rep)
    return representatives


def parse_fsp_sole_proprietors(html: str) -> list[dict]:
    """Parse sole proprietors from details HTML."""
    soup = BeautifulSoup(html, "lxml")
    sole_props = []
    
    tables = soup.find_all("table")
    sp_table = None
    for t in tables:
        rows = t.find_all("tr")
        if rows:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            if "sole proprietor" in headers or ("full names" in headers and "conditions apply" in headers):
                sp_table = t
                break
                
    if sp_table:
        rows = sp_table.find_all("tr")
        if len(rows) > 1:
            headers = [c.text.strip().lower() for c in rows[0].find_all(["td", "th"])]
            for row in rows[1:]:
                cells = row.find_all("td")
                if cells:
                    sp = {}
                    for idx, h in enumerate(headers):
                        if idx < len(cells):
                            val = cells[idx].text.strip()
                            if "full names" in h:
                                sp["full_names"] = val
                            elif "surname" in h:
                                sp["surname"] = val
                            elif "conditions apply" in h:
                                sp["conditions_apply"] = val
                    if sp.get("full_names") or sp.get("surname"):
                        sole_props.append(sp)
    return sole_props


def parse_reps_pagination(html: str) -> dict:
    """Parse representative list pagination state from HTML."""
    soup = BeautifulSoup(html, "lxml")
    pag = {}
    for name in ["Next_From_Count", "Next_To_Count", "Total_Count", "Previous_From_Count", "Previous_To_Count"]:
        inp = soup.find("input", {"name": name})
        if inp:
            val = inp.get("value", "").strip()
            if val:
                pag[name] = val
    return pag


def has_next_page(html: str) -> bool:
    """Check if the Next button is enabled in representative list page."""
    soup = BeautifulSoup(html, "lxml")
    btn = soup.find("input", {"name": "bNext"})
    if btn:
        return not btn.has_attr("disabled")
    return False
