"""Offline validation of immutable ATG prestart snapshots."""
import copy
import datetime as dt
import unittest
from zoneinfo import ZoneInfo
from scripts import capture_prestart_market as m

NOW=dt.datetime(2026,10,27,9,0,tzinfo=ZoneInfo("Europe/Stockholm"))

def game():
    return {"id":m.ID,
            "pools":{"V85":{"timestamp":"2026-10-27 08:58:00"}},
            "races":[{"id":f"2026-10-31_78_{i+4}","number":i+4,
                      "status":"bettable",
                      "starts":[{"number":n,"horse":{"name":f"H{n}"},
                                 "pools":{"V85":{"betDistribution":1250}}}
                                for n in range(1,9)]} for i in range(1,9)]}

class Tests(unittest.TestCase):
    def test_happy_path_and_stable_digest(self):
        doc=m.checked_snapshot(game(),NOW)
        self.assertEqual(len(doc["races"]),8)
        self.assertAlmostEqual(sum(x["pct"] for x in doc["races"][0]["starts"]),100)
        path=m.candidate_path(doc)
        later={**doc,"observedAt":"2026-10-27T09:03:00+01:00"}
        self.assertEqual(path,m.candidate_path(later))

    def test_no_snapshots_after_off(self):
        with self.assertRaisesRegex(ValueError,"started"):
            m.checked_snapshot(game(),dt.datetime(2026,10,31,15,0,tzinfo=NOW.tzinfo))

    def test_incomplete_pool_rejected(self):
        bad=game()
        bad["races"][0]["starts"][0]["pools"]["V85"]["betDistribution"]=0
        with self.assertRaisesRegex(ValueError,"totals"):
            m.checked_snapshot(bad,NOW)

    def test_source_timestamp_future_rejected(self):
        bad=game()
        bad["pools"]["V85"]["timestamp"]="2026-10-28 12:00:00"
        with self.assertRaisesRegex(ValueError,"source time"):
            m.checked_snapshot(bad,NOW)

    def test_source_is_not_altered(self):
        source=game(); original=copy.deepcopy(source)
        m.checked_snapshot(source,NOW)
        self.assertEqual(source,original)

if __name__=="__main__":
    unittest.main()
