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


    def test_scratched_horse_retains_market_share_without_fake_redistribution(self):
        source=game()
        leg8=source["races"][7]
        # Nore'n: 10.6% on a scratched horse, remainder 89.4% still on live runners.
        raw=[1060,1270,1270,1270,1270,1270,1270,1320]
        self.assertEqual(sum(raw),10000)
        for runner,pct in zip(leg8["starts"],raw):
            runner["pools"]["V85"]["betDistribution"]=pct
        leg8["starts"][0]["scratched"]=True
        doc=m.checked_snapshot(source,NOW)
        value=doc["races"][7]
        self.assertEqual(value["allMarketPct"],100)
        self.assertEqual(value["activeMarketPct"],89.4)
        self.assertEqual(value["scratchedMarketPct"],10.6)
        self.assertTrue(value["awaitingScratchRedistribution"])
        self.assertEqual(value["starts"][0]["pct"],10.6)
        self.assertTrue(value["starts"][0]["scratched"])

    def test_invalid_total_with_a_scratch_is_still_rejected(self):
        source=game()
        source["races"][7]["starts"][0]["scratched"]=True
        source["races"][7]["starts"][0]["pools"]["V85"]["betDistribution"]=300
        with self.assertRaisesRegex(ValueError,"totals invalid"):
            m.checked_snapshot(source,NOW)

    def test_healthy_market_has_no_pending_scratch_shares(self):
        doc=m.checked_snapshot(game(),NOW)
        self.assertTrue(all(not r["awaitingScratchRedistribution"] for r in doc["races"]))
        self.assertTrue(all(r["activeMarketPct"]==100 for r in doc["races"]))

    def test_invalid_atg_response_is_warning_not_job_failure(self):
        from unittest import mock
        from io import StringIO
        import json
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return json.dumps({"id":m.ID,"races":[]}).encode()
        with mock.patch.object(m.urllib.request,"urlopen",return_value=Response()):
            with mock.patch("sys.stdout",new_callable=StringIO) as captured:
                self.assertEqual(m.main(now=NOW),0)
                self.assertIn("::warning::ATG snapshot skipped",captured.getvalue())

    def test_source_is_not_altered(self):
        source=game(); original=copy.deepcopy(source)
        m.checked_snapshot(source,NOW)
        self.assertEqual(source,original)

if __name__=="__main__":
    unittest.main()
