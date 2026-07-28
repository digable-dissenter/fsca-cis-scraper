import unittest
from fsca_scraper.parser import (
    parse_fsp_search_results,
    parse_fsp_details,
    parse_rep_products,
    parse_ki_cob,
)


class TestFspScraper(unittest.TestCase):
    def setUp(self):
        self.sample_search_results_html = """
<HTML>
<BODY>
<form NAME="Search" action="/MagicScripts/mgrqispi.dll" method="post">
<table border=2>
<tr>
<td class=noborderText>  704</Td>
<td class=noborderText>ALLAN GRAY GROUP LIMITED</Td>
<td class=noborderText>Lapsed</Td>
<td class=noborderText><input type="submit" onclick="updateArguments(  704)" name="bDetails" value="Details"></Td>
</tr>
<tr>
<td class=noborderText>19896</Td>
<td class=noborderText>ALLAN GRAY INVESTMENT SERVICES (PTY) LTD</Td>
<td class=noborderText>Authorized</Td>
<td class=noborderText><input type="submit" onclick="updateArguments(19896)" name="bDetails" value="Details"></Td>
</tr>
</table>
</form>
</BODY>
</HTML>
"""

        self.sample_details_html = """
<HTML>
<BODY>
<form NAME="Detail" action="/MagicScripts/mgrqispi.dll" method="post">
<table border=2>
<tr>
<td class="DescrText">FSP No</td>
<td class=noborderText>19896</Td>
</tr>
<tr>
<td class="DescrText">FSP Name</td>
<td class=noborderText>ALLAN GRAY INVESTMENT SERVICES (PTY) LTD</Td>
</tr>
<tr>
<td class="DescrText">FSP Type</td>
<td class=noborderText>Company - Private</Td>
</tr>
<tr>
<td class="DescrText">Registration Number</td>
<td class=noborderText>2004/015145/07</Td>
</tr>
<tr>
<td class="DescrText">Date Authorised</td>
<td class=noborderText>12/05/2005</Td>
</tr>
</table>

<div id="Contact_Info">
<table border=1>
<tr>
<td class="DescrText">Physical Address</td>
<td class="noborderText">1 SILO SQUARE<br>CAPE TOWN<br>8001</td>
</tr>
<tr>
<td class="DescrText">Telephone No</td>
<td class="noborderText">+27021 4152301</td>
</tr>
</table>
</div>

<div id="ComplianceOfficers">
<table border=1>
<tr>
<td class="DescrText">Compliance Officer</td>
<td class="DescrText">Compliance Officer Tel No</td>
</tr>
<tr>
<td class="noborderText">URSUL U LOUBSER</td>
<td class="noborderText">021 524 4400</td>
</tr>
</table>
</div>

<div id="Key_Individuals">
<table border=1>
<tr>
<td class="DescrText">Type</td>
<td class="DescrText">Full Names</td>
<td class="DescrText">Surname</td>
<td class="DescrText">Class of Business</td>
</tr>
<tr>
<td class="InputText">Key Individual</td>
<td class="InputText">FAIZIL</td>
<td class="InputText">JAKOET</td>
<td class="InputText">Class of Business</td>
</tr>
</table>
</div>

<div id="Products_Approved">
<table border=1>
<tr>
<td class="DescrText">Category Description</td>
<td class="DescrText">Advice Automated</td>
<td class="DescrText">Advice Non-automated</td>
<td class="DescrText">Intermediary Scripted</td>
<td class="DescrText">Intermediary Other</td>
</tr>
<tr>
<td class="InputText">CATEGORY III - Administrative FSP</td>
<td class="InputText"></td>
<td class="InputText"></td>
<td class="InputText"></td>
<td class="InputText"></td>
</tr>
<tr>
<td class="InputText">Participatory interest in a hedge fund</td>
<td class="InputText"></td>
<td class="InputText"></td>
<td class="InputText"></td>
<td class="InputText">X</td>
</tr>
<tr>
<td class="InputText">Long-term Insurance subcategory C</td>
<td class="InputText"></td>
<td class="InputText"></td>
<td class="InputText"></td>
<td class="InputText">X</td>
</tr>
</table>
</div>
</form>
</BODY>
</HTML>
"""

    def test_parse_fsp_search_results(self):
        fsp_ids = parse_fsp_search_results(self.sample_search_results_html)
        self.assertEqual(len(fsp_ids), 2)
        self.assertEqual(fsp_ids[0], "704")
        self.assertEqual(fsp_ids[1], "19896")

    def test_parse_fsp_details(self):
        details = parse_fsp_details(self.sample_details_html)
        
        # Verify general details
        self.assertEqual(details.get("fsp_no"), "19896")
        self.assertEqual(details.get("name"), "ALLAN GRAY INVESTMENT SERVICES (PTY) LTD")
        self.assertEqual(details.get("fsp_type"), "Company - Private")
        self.assertEqual(details.get("registration_number"), "2004/015145/07")
        self.assertEqual(details.get("date_authorised"), "12/05/2005")

        # Verify contact info
        self.assertIn("1 SILO SQUARE", details.get("physical_address", ""))
        self.assertIn("CAPE TOWN", details.get("physical_address", ""))
        self.assertEqual(details.get("telephone"), "+27021 4152301")

        # Verify compliance officers
        cos = details.get("compliance_officers", [])
        self.assertEqual(len(cos), 1)
        self.assertEqual(cos[0].get("name"), "URSUL U LOUBSER")
        self.assertEqual(cos[0].get("telephone"), "021 524 4400")

        # Verify Key Individuals
        kis = details.get("key_individuals", [])
        self.assertEqual(len(kis), 1)
        self.assertEqual(kis[0].get("full_names"), "FAIZIL")
        self.assertEqual(kis[0].get("surname"), "JAKOET")

        # Verify Approved Products
        prods = details.get("approved_products", [])
        self.assertEqual(len(prods), 2)
        
        self.assertEqual(prods[0].get("category"), "CATEGORY III - Administrative FSP")
        self.assertEqual(prods[0].get("product_name"), "Participatory interest in a hedge fund")
        self.assertFalse(prods[0].get("advice_automated"))
        self.assertTrue(prods[0].get("intermediary_other"))
        
        self.assertEqual(prods[1].get("category"), "CATEGORY III - Administrative FSP")
        self.assertEqual(prods[1].get("product_name"), "Long-term Insurance subcategory C")
        self.assertFalse(prods[1].get("advice_non_automated"))
        self.assertTrue(prods[1].get("intermediary_other"))

    def test_parse_rep_products(self):
        rep_html = """
<HTML>
<BODY>
<table border=1 cellspacing=0 cellpadding=3>
<tr>
<td class="DescrText">Category</td>
<td class="DescrText">Sub Category</td>
<td class="DescrText">Category Description</td>
<td class="DescrText">Advice</td>
<td class="DescrText">Intermediary - Scripted</td>
<td class="DescrText">Intermediary - Other</td>
<td class="DescrText">Services Under Supervision</td>
</tr>
<tr>
<td class="InputText"> 1</td>
<td class="InputText"> 4</td>
<td class="InputText">Long-Term Insurance subcategory C</td>
<td class="InputText"></td>
<td class="InputText"></td>
<td class="InputText">X</td>
<td class="InputText"></td>
</tr>
</table>
</BODY>
</HTML>
"""
        prods = parse_rep_products(rep_html)
        self.assertEqual(len(prods), 1)
        self.assertEqual(prods[0].get("category"), "1")
        self.assertEqual(prods[0].get("subcategory"), "4")
        self.assertEqual(prods[0].get("product_name"), "Long-Term Insurance subcategory C")
        self.assertFalse(prods[0].get("advice"))
        self.assertTrue(prods[0].get("intermediary_other"))
        self.assertFalse(prods[0].get("under_supervision"))

    def test_parse_ki_cob(self):
        ki_html = """
<HTML>
<BODY>
<table border="1">
	<tr>
		<td class="title-grey-narrow">Class of business</td>
		<td class="title-grey-narrow">Select</td>
		<td class="title-grey-narrow">Category I</td>
		<td class="title-grey-narrow">Category II</td>
		<td class="title-grey-narrow">Category IIA</td>
		<td class="title-grey-narrow">Category III</td>
		<td class="title-grey-narrow">Category IV</td>
	</tr>
	<tr>
		<td><input type=text readonly class=InputText size="50" name="COB_Description" value="Long-Term Insurance"></td>
		<td><input type="checkbox"  value="1" checked name="COB_3"></td>	
		<td><input type="checkbox"  value="1" checked name="COB_CATI_3"></td>					
		<td><input type="checkbox"  value="1" checked name="COB_CATII_3"></td>					
		<td><input type="checkbox"  value="1"  name="COB_CATIIA_3"></td>					
		<td><input type="checkbox"  value="1"  name="COB_CATIII_3"></td>					
		<td><input type="checkbox"  value="1"  name="COB_CATIV_3"></td>					
	</tr>
</table>
</BODY>
</HTML>
"""
        cobs = parse_ki_cob(ki_html)
        self.assertEqual(len(cobs), 1)
        self.assertEqual(cobs[0].get("cob_description"), "Long-Term Insurance")
        self.assertTrue(cobs[0].get("category_i"))
        self.assertTrue(cobs[0].get("category_ii"))
        self.assertFalse(cobs[0].get("category_iia"))
        self.assertFalse(cobs[0].get("category_iii"))
        self.assertFalse(cobs[0].get("category_iv"))


if __name__ == "__main__":
    unittest.main()
