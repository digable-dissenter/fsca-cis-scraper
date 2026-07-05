# FSCA CIS Scraper

Scrapes and stores management companies, schemes, and portfolios from the
[FSCA Collective Investment Schemes](https://www2.fsca.co.za/MagicScripts/mgrqispi.dll?APPNAME=Web&PRGNAME=Search_Mancos) public registry.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
# Run discovery to capture HTML structure
python -m fsca_scraper discover

# Run the full scraper
python -m fsca_scraper scrape

# Run with scheduling (repeat every N hours)
python -m fsca_scraper scrape --schedule 24
```

## Data

Data is stored in `data/fsca_cis.db` (SQLite).

### Tables

- **management_companies** — Manager details (name, type, address, etc.)
- **schemes** — CIS schemes under each management company
- **portfolios** — Investment portfolios under each scheme
