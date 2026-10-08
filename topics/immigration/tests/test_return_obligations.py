"""AZR 2025 state-level source integrity checks."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
AZR = ROOT / "data" / "state-return-obligations-2025.json"
DEPORT = ROOT / "data" / "state-deportations-2025.json"
METRICS = ("total", "with_duldung", "without_duldung")


class StateReturnObligationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = json.loads(AZR.read_text(encoding="utf-8"))
        cls.deport = json.loads(DEPORT.read_text(encoding="utf-8"))

    def test_source_and_legal_concept(self):
        d = self.data
        self.assertEqual(d["reference_date"], "2025-12-31")
        self.assertEqual(d["published_at"], "2026-02-11")
        self.assertIn("21/4103", d["source"]["document"])
        self.assertIn("Seite 21", d["source"]["document"])
        self.assertEqual(d["geography_level"], "state_registered_location")
        self.assertIn("Duldung", d["statistics_definition_zh"])

    def test_16_state_complete_geography(self):
        d = self.data
        records = d["records"]
        self.assertEqual(len(records), 16)
        self.assertEqual({r["iso"] for r in records},
                         {r["iso"] for r in self.deport["records"]})
        self.assertEqual(len({r["ags"] for r in records}), 16)
        self.assertEqual(d["completeness"]["reported_states"], 16)
        self.assertFalse(d["completeness"]["lower_geographies_available_in_this_source"])

    def test_all_record_sums_and_national_totals(self):
        d = self.data
        for row in d["records"]:
            self.assertEqual(row["total"], row["with_duldung"] + row["without_duldung"])
            for key in METRICS:
                self.assertGreaterEqual(row[key], 0)
                self.assertIsInstance(row[key], int)
        for key, total in (("total", 232067),
                           ("with_duldung", 190974),
                           ("without_duldung", 41093)):
            self.assertEqual(sum(row[key] for row in d["records"]), total)
            self.assertEqual(d["totals"][key], total)

    def test_no_county_level_records_or_synthetic_rates(self):
        self.assertTrue(all(len(r["ags"]) == 2 for r in self.data["records"]))
        self.assertNotIn("deportation_rate", self.data)
        self.assertEqual(self.data["missing_value_policy"].split(",")[0].strip(),
                         "Missing observations must be null")


if __name__ == "__main__":
    unittest.main()
