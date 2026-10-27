"""Tests: no time leakage, race winner filters, historical market benchmark."""
import unittest
from scripts import historical_pilot as h
from scripts import train_historical_pilot as t

class HistoricalPilotTests(unittest.TestCase):
    def test_market_and_future_results_not_feature_inputs(self):
        self.assertEqual(set(t.FEATURES),{"post","distance","field","auto","starts5",
            "form_place_mean","win5","top3_5","days_off","gallop5",
            "km_median","past_purse_log"})
        self.assertNotIn("marketFinalPct",t.FEATURES)

    def test_calendar_v85_discovery(self):
        self.assertEqual(h.get_v85_id({"games":{"V85":{"id":"V85_2026-10-03_7_5"}}}),
                         "V85_2026-10-03_7_5")
        with self.assertRaises(ValueError):
            h.get_v85_id({"games":{}})

    def test_dont_leak_any_future_or_same_day_results(self):
        start={"horse":{"results":{"records":[
            {"date":"2026-06-01","place":"1","race":{"id":"2026-06-01_5_1"}},
            {"date":"2026-06-15","place":"1","race":{"id":"2026-06-15_5_1"}},
            {"date":"2026-06-20","place":"2","race":{"id":"2026-06-20_5_1"}}
        ]}}}
        history=h.past_records(start,__import__("datetime").date(2026,6,15))
        self.assertEqual(len(history),1)
        self.assertEqual(history[0]["date"],"2026-06-01")

    def test_result_requires_one_winner(self):
        race={"id":"2026-06-01_5_1","status":"results","date":"2026-06-01",
             "distance":2140,"startMethod":"auto","track":{"name":"Test"},
             "starts":[{"number":i,"horse":{"name":f"Example{i}"},"result":{"place":1 if i==1 else i}}
                       for i in range(1,9)]}
        parsed=h.parse_historical_race(race,{"id":"V85_TEST","races":[]},"2026-06-01")
        self.assertEqual(len(parsed),8)
        self.assertEqual(sum(r["winner"] for r in parsed),1)
        self.assertIsNone(parsed[0]["prestartFeatures"]["form_place_mean"])
        race["starts"][1]["result"]["place"]=1
        self.assertIsNone(h.parse_historical_race(race,{"id":"V85_TEST","races":[]},"2026-06-01"))

    def test_normalized_probs(self):
        x=t.normalized_per_race([2,1,1])
        self.assertAlmostEqual(sum(x),1)
        self.assertAlmostEqual(x[0],0.5)

    def test_baseline_needs_complete_pool(self):
        r={"r":[{"winner":1,"marketFinalPct":None},{"winner":0,"marketFinalPct":80}]
           +[{"winner":0,"marketFinalPct":4} for _ in range(5)]}
        self.assertEqual(t.evaluate(r,"marketFinalPct",market=True)["races"],0)

if __name__=="__main__":
    unittest.main()
