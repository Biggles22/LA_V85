"""Regression tests for point-in-time Bjerke form collector."""
import unittest

from scripts import update_bjerke_form as m


class FormCollectionTests(unittest.TestCase):
    def test_uses_nested_horse_history(self):
        record = {"date": "2026-10-20", "place": "2", "race": {"id": "2026-10-20_1_1"},
                  "start": {"distance": 2100}}
        start = {"number": 3, "horse": {"name": "Example",
                 "results": {"records": [record]}}}
        self.assertEqual(m.records_of(start), [record])
        self.assertEqual(m.parse_record(record)["place"], 2)

    def test_only_past_starts(self):
        self.assertIsNone(m.parse_record({"date": "2026-10-31", "place": "1"}))
        self.assertIsNone(m.parse_record({"date": "2026-11-01", "place": "1"}))
        self.assertIsNotNone(m.parse_record({"date": "2026-10-30", "place": "1"}))

    def test_gallop_and_win_is_not_zero(self):
        self.assertGreater(m.performance(1, True), 4)
        self.assertEqual(m.performance(None, True), 0.2)
        self.assertEqual(m.performance(1, False), 5)

    def test_missing_history_produces_no_score(self):
        item = m.analysis_entry({"number": 1, "name": "No history", "distance": 1609}, None)
        self.assertIsNone(item["scores"]["form"])
        self.assertIsNone(item["scores"]["risk"])
        self.assertEqual(item["lastFive"], [])

    def test_form_needs_two_verifiable_starts(self):
        one = [{"date": "2026-10-10", "place": 1, "galloped": None}]
        self.assertIsNone(m.score_form(one))
        self.assertGreater(m.score_form(one + [{"date": "2026-09-10", "place": 2, "galloped": None}]), 3)


if __name__ == "__main__":
    unittest.main()
