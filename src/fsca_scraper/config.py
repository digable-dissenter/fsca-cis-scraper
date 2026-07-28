from pathlib import Path

BASE_URL = "https://www2.fsca.co.za/MagicScripts/mgrqispi.dll"
SEARCH_PARAMS = {
    "APPNAME": "Web",
    "PRGNAME": "Search_Mancos",
}
SEARCH_URL = f"{BASE_URL}?APPNAME=Web&PRGNAME=Search_Mancos"

CATEGORY_MAPPINGS = {
    'CATEGORY I': 1,
    'CATEGORY II - Discretionary FSP': 2,
    'CATEGORY III - Administrative FSP': 3,
    'CATEGORY IV Assistance business FSP': 4,
    'CATEGORY 2A': 20
}

REQUEST_DELAY_MIN_SECONDS = 3
REQUEST_DELAY_MAX_SECONDS = 5

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATABASE_PATH = DATA_DIR / "fsca_cis.db"
DISCOVERY_DIR = DATA_DIR / "discovery"

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

PAGE_LOAD_TIMEOUT_MS = 30_000
NAVIGATION_TIMEOUT_MS = 60_000
