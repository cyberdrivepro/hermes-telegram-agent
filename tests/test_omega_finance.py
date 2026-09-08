from decimal import Decimal
from pathlib import Path
import tempfile
import unittest
from omega_finance import amortization, dcf, invoice


class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def test_interest_and_prepayment(self):
        baseline = amortization({"principal": 100000, "annual_rate_percent": 12, "months": 12}, self.root)
        self.assertEqual(baseline["data"]["monthly_payment"], "8884.88")
        prepaid = amortization({"principal": 100000, "annual_rate_percent": 12, "months": 12, "monthly_prepayment": 1000}, self.root)
        self.assertLess(Decimal(prepaid["data"]["total_interest"]), Decimal(baseline["data"]["total_interest"]))
        self.assertLess(prepaid["data"]["months"], 12)

    def test_dcf_perpetuity_and_bad_growth(self):
        result = dcf({"cash_flows": [100], "discount_rate_percent": 10}, self.root)
        self.assertEqual(result["data"]["enterprise_value"], "1000.00")
        with self.assertRaises(ValueError):
            dcf({"cash_flows": [100], "discount_rate_percent": 10, "terminal_growth_percent": 10}, self.root)

    def test_invoice_totals_and_csv_injection(self):
        payload = {"items": [{"description": "=DANGEROUS()", "quantity": 2, "unit_price": "100", "tax_rate_percent": 18}]}
        totals = invoice(payload, self.root)["data"]["totals"]
        self.assertEqual(totals, {"taxable": "200.00", "cgst": "18.00", "sgst": "18.00", "igst": "0.00", "total": "236.00"})
        self.assertIn("'=DANGEROUS()", (self.root / "invoice.csv").read_text())
        payload["interstate"] = True
        totals = invoice(payload, self.root)["data"]["totals"]
        self.assertEqual(totals["igst"], "36.00")
        self.assertEqual(totals["cgst"], "0.00")

