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


    def test_prize_and_time_are_prestart_evidence(self):
        sample = {"date": "2026-10-19", "place": "1", "race": {
            "firstPrize": 20000000, "startMethod": "auto", "id": "2026-10-19_78_3"},
            "track": {"countryCode": "NO"},
            "start": {"distance": 2100, "postPosition": 3},
            "kmTime": {"minutes": 1, "seconds": 15, "tenths": 5}}
        p = m.parse_record(sample)
        self.assertEqual(p["country"], "NO")
        self.assertEqual(p["kmSeconds"], 75.5)
        self.assertEqual(p["pastFirstPrize"], 20000000)
        self.assertEqual(p["startMethod"], "auto")

    def test_volt_race_has_no_auto_gate_proxy(self):
        self.assertIsNone(m.score_draw(3, "volte"))
        self.assertGreater(m.score_draw(2, "auto"), m.score_draw(10, "auto"))

    def test_class_proxy_uses_only_historical_purse_within_country(self):
        races=[{"leg":1,"startMethod":"auto","horses":[]}]
        market=[{"starts":[]}]
        for i in range(10):
            rows=[]
            for j in range(3):
                rows.append({"date":f"2026-10-{20-j:02d}","place":1 if i%2 else 4,
                             "galloped":False,"distance":2100,
                             "country":"NO","pastFirstPrize":(i+1)*1000000,
                             "kmSeconds":70+i*0.2,"startMethod":"auto"})
            h={"number":i+1,"name":f"Horse {i}","scratched":False,"lastFive":rows,
               "scores":{"form":3,"pace":None,"class":None,"gear":None,"risk":None},
               "coverage":{"form":True,"pace":False,"class":False,"gear":False},
               "evidence":{"classStarts":0,"paceStarts":0,"classCountries":[],
                           "modelCoverageWeight":0,"partialRankScore":None}}
            races[0]["horses"].append(h)
            market[0]["starts"].append({"number":i+1,"postPosition":i+1,"distance":2100,
                                        "pct":90-i*9,"odds":1+i})
        m.add_contextual_scores(races,market)
        self.assertTrue(all(h["scores"]["class"] is not None for h in races[0]["horses"]))
        self.assertTrue(all(h["scores"]["pace"] is not None for h in races[0]["horses"]))
        self.assertGreater(races[0]["horses"][-1]["scores"]["class"],
                           races[0]["horses"][0]["scores"]["class"])
        self.assertEqual(races[0]["horses"][0]["evidence"]["modelCoverageWeight"],75)

    def test_missing_purse_and_time_not_fabricated(self):
        h={"number":1,"name":"No comparable data","scratched":False,"lastFive":[],
           "scores":{"form":None,"pace":None,"class":None,"gear":None,"risk":None},
           "coverage":{"form":False,"pace":False,"class":False,"gear":False},
           "evidence":{"classStarts":0,"paceStarts":0,"classCountries":[],
                       "modelCoverageWeight":0,"partialRankScore":None}}
        race=[{"leg":1,"startMethod":"volte","horses":[h]}]
        market=[{"starts":[{"number":1,"postPosition":1,"distance":2140}]}]
        m.add_contextual_scores(race,market)
        self.assertIsNone(h["scores"]["class"])
        self.assertIsNone(h["scores"]["pace"])
        self.assertIsNone(h["evidence"]["partialRankScore"])



if __name__ == "__main__":
    unittest.main()
