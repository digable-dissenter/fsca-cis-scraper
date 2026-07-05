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
