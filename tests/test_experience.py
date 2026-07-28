import unittest
from fsca_scraper.experience import (
    normalize_product_name,
    get_experience_requirement,
    validate_experience,
    ADVICE,
    INTERMEDIARY,
)

class TestExperience(unittest.TestCase):
    def test_normalize_product_name(self):
        self.assertEqual(
            normalize_product_name("Participatory interests in one or more collective investment schemes"),
            "participatory interest in collective investment scheme"
        )
        self.assertEqual(
            normalize_product_name("Long-Term Insurance subcategory A"),
            "long term insurance subcategory a"
        )
        self.assertEqual(
            normalize_product_name("Pension Funds Benefits"),
            "pension fund benefit"
        )
        self.assertEqual(
            normalize_product_name("Debentures and securitised debt"),
            "debenture and securitised debt"
        )
        self.assertEqual(
            normalize_product_name("Short-term Insurance Personal Lines"),
            "short term insurance personal line"
        )

    def test_get_experience_requirement_cat_i(self):
        # Long-Term Insurance subcategory A (Advice: 6 months, Intermediary: 2 months)
        self.assertEqual(get_experience_requirement("CATEGORY I", "Long-Term Insurance subcategory A", ADVICE), 6)
        self.assertEqual(get_experience_requirement("CATEGORY I FSP", "Long-Term Insurance subcategory A", INTERMEDIARY), 2)
        
        # Shares (Advice: 24 months, Intermediary: 12 months)
        self.assertEqual(get_experience_requirement("Category I", "Shares", ADVICE), 24)
        self.assertEqual(get_experience_requirement("Category I", "Shares", INTERMEDIARY), 12)

    def test_get_experience_requirement_cat_ii(self):
        # Shares (3 years = 36 months)
        self.assertEqual(get_experience_requirement("CATEGORY II - Discretionary FSP", "Shares", ADVICE), 36)
        self.assertEqual(get_experience_requirement("Category II", "Long-term Insurance subcategory B1", ADVICE), 24)

    def test_get_experience_requirement_cat_iii(self):
        # Category III general experience requirement is 36 months
        self.assertEqual(get_experience_requirement("CATEGORY III - Administrative FSP", "Shares", INTERMEDIARY), 36)
        self.assertEqual(get_experience_requirement("Category III", "Long-term Insurance subcategory C", ADVICE), 36)

    def test_validate_experience(self):
        # Meets requirement
        valid, req = validate_experience("CATEGORY I", "Shares", ADVICE, 24)
        self.assertTrue(valid)
        self.assertEqual(req, 24)

        # Fails requirement
        valid, req = validate_experience("CATEGORY I", "Shares", ADVICE, 12)
        self.assertFalse(valid)
        self.assertEqual(req, 24)

        # Non-existent product/category
        valid, req = validate_experience("CATEGORY I", "Invalid Product Name Here", ADVICE, 12)
        self.assertTrue(valid)
        self.assertEqual(req, 0)

    def test_get_product_codes(self):
        from fsca_scraper.experience import get_product_codes
        
        # Test Category I Bonds
        cat_c, subcat_c, comb_c = get_product_codes("CATEGORY I", "Bonds")
        self.assertEqual(cat_c, "1")
        self.assertEqual(subcat_c, "12")
        self.assertEqual(comb_c, "1.12")

        # Test Category II Bonds
        cat_c, subcat_c, comb_c = get_product_codes("CATEGORY II - Discretionary FSP", "Bonds")
        self.assertEqual(cat_c, "2")
        self.assertEqual(subcat_c, "9")
        self.assertEqual(comb_c, "2.9")


if __name__ == "__main__":
    unittest.main()
