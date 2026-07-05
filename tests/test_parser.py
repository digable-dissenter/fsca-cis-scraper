import unittest
from pathlib import Path
from fsca_scraper.parser import parse_manco_list, parse_manco_details, parse_manco_schemes, parse_portfolios

class TestParser(unittest.TestCase):
    def setUp(self):
        self.discovery_dir = Path(__file__).parent.parent / "data" / "discovery"
        
    def test_parse_manco_list(self):
        file_path = self.discovery_dir / "01_search_results.html"
        if not file_path.exists():
            self.skipTest("01_search_results.html not found")
        content = file_path.read_text(encoding="utf-8")
        manco_ids = parse_manco_list(content)
        self.assertGreater(len(manco_ids), 0)
        self.assertIn("10", manco_ids)
        self.assertIn("2", manco_ids)

    def test_parse_manco_details(self):
        file_path = self.discovery_dir / "detail_10.html"
        if not file_path.exists():
            self.skipTest("detail_10.html not found")
        content = file_path.read_text(encoding="utf-8")
        details = parse_manco_details(content)
        self.assertEqual(details.get("manager_no"), "10")
        self.assertEqual(details.get("name"), "Foord Unit Trusts (RF) Pty Ltd")
        self.assertEqual(details.get("company_type"), "Securities")
        self.assertEqual(details.get("company_no"), "2001/029793/07")
        self.assertEqual(details.get("local_foreign"), "Local")
        self.assertIn("PINELANDS", details.get("physical_address", ""))
        self.assertEqual(details.get("telephone"), "+27 21 5326916")

    def test_parse_manco_schemes(self):
        file_path = self.discovery_dir / "detail_10.html"
        if not file_path.exists():
            self.skipTest("detail_10.html not found")
        content = file_path.read_text(encoding="utf-8")
        schemes = parse_manco_schemes(content)
        self.assertEqual(len(schemes), 1)
        self.assertEqual(schemes[0].get("scheme_no"), "10")
        self.assertEqual(schemes[0].get("name"), "Foord Unit Trust Scheme")
        self.assertEqual(schemes[0].get("type_of_scheme"), "Securities")
        self.assertEqual(schemes[0].get("status"), "Approved")

    def test_parse_portfolios(self):
        file_path = self.discovery_dir / "portfolios_10_10.html"
        if not file_path.exists():
            self.skipTest("portfolios_10_10.html not found")
        content = file_path.read_text(encoding="utf-8")
        portfolios = parse_portfolios(content)
        self.assertGreater(len(portfolios), 0)
        self.assertEqual(portfolios[0].get("portfolio_no"), "169")
        self.assertEqual(portfolios[0].get("scheme_no"), "10")
        self.assertEqual(portfolios[0].get("name"), "Foord Balanced Fund")

if __name__ == "__main__":
    unittest.main()
