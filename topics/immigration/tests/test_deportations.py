"""Official source-row invariants. No mocks or inferred spatial values."""
import json
from pathlib import Path
import unittest

DATA = Path(__file__).resolve().parents[1] / "data" / "state-deportations-2025.json"
KNOWN = {"DE-BW","DE-BY","DE-BE","DE-BB","DE-HB","DE-HH","DE-HE","DE-MV",
         "DE-NI","DE-NW","DE-RP","DE-SL","DE-SN","DE-ST","DE-SH","DE-TH"}


class OfficialStateDataTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(DATA.read_text(encoding="utf-8"))

    def test_official_citation_and_scope(self):
        d = self.data
        self.assertEqual(d["source"]["url"], "https://dserver.bundestag.de/btd/21/044/2104403.pdf")
        self.assertIn("Seite 4", d["source"]["document"])
        self.assertEqual(d["geography_level"], "state_executing_authority")
        self.assertEqual(d["published_at"], "2026-02-26")

    def test_all_states_present_and_unique(self):
        d = self.data
        self.assertEqual(len(d["records"]), 16)
        self.assertEqual({r["iso"] for r in d["records"]}, KNOWN)
        self.assertEqual(len({r["ags"] for r in d["records"]}), 16)
        self.assertTrue(all(isinstance(r["value"], int) and r["value"] >= 0
                            for r in d["records"]))

    def test_state_totals_and_separate_federal_police(self):
        d = self.data
        self.assertEqual(sum(r["value"] for r in d["records"]), 22174)
        self.assertEqual(d["states_subtotal"], 22174)
        self.assertEqual(d["federal_police_separately"], 613)
        self.assertEqual(d["total_all_authorities"], 22787)
        self.assertEqual(d["states_subtotal"] + d["federal_police_separately"],
                         d["total_all_authorities"])


if __name__ == "__main__":
    unittest.main()
