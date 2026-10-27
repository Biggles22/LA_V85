"""Tests of opponent strength estimates at the *past race's date*."""
import unittest
from scripts import opponent_probe as o

class OpponentProbeTests(unittest.TestCase):
    def test_future_performance_is_ignored(self):
        h={"horse":{"name":"Opponent","results":{"records":[
            {"date":"2026-09-08","place":"1"},
            {"date":"2026-09-01","place":"3"},
            {"date":"2026-10-30","place":"1"},
        ]}}}
        base=o.prior_opponent_form(h,__import__("datetime").date(2026,9,15))
        self.assertAlmostEqual(base,.6*.5+.4*1.0)
        self.assertIsNone(o.prior_opponent_form(h,__import__("datetime").date(2026,8,15)))

    def test_missing_opponent_form_stays_missing(self):
        r={"id":"2026-09-10_7_8","starts":[
            {"horse":{"name":"Focus","results":{"records":[]}}},
            *[{"horse":{"name":f"Rival{i}","results":{"records":[]}}}
              for i in range(1,8)],
        ]}
        got=o.opponent_context(r,{r["id"]:[{"leg":2,"number":3,"name":"Focus"}]})
        self.assertFalse(got[0]["coverageSufficient"])
        self.assertIsNone(got[0]["opponentRecentFormMean"])

    def test_asof_count_excludes_same_day(self):
        r={"horse":{"name":"Example","results":{"records":[
            {"date":"2026-09-10","place":"1"},
            {"date":"2026-09-09","place":"1"},
            {"date":"2026-09-02","place":"2"},
        ]}}}
        score=o.prior_opponent_form(r,__import__("datetime").date(2026,9,10))
        self.assertAlmostEqual(score,.6*.5+.4*1)

    def test_requires_race_identifiers(self):
        doc={"races":[{"leg":1,"horses":[{"number":3,"name":"X","lastFive":[
          {"raceId":"bad-id"},{"raceId":"2026-09-12_5_3"}]}]}]}
        race=o.requested_races(doc)
        self.assertEqual(list(race),["2026-09-12_5_3"])

if __name__=="__main__":
    unittest.main()
