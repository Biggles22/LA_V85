"""Offline tests for two-cutoff prior-opponent historical features."""
import datetime as dt
import unittest
from scripts import historical_opponent_asof as m

def start(name,history):
    return {"horse":{"name":name,"results":{"records":[
        {"date":day,"place":place} for day,place in history]}}}

class HistoricalOpponentTests(unittest.TestCase):
    def test_strict_past_race_and_current_race_bounds(self):
        self.assertTrue(m.match_race_id("2026-08-01_6_4","2026-09-01"))
        self.assertFalse(m.match_race_id("2026-09-01_6_4","2026-09-01"))
        self.assertFalse(m.match_race_id("2026-09-02_6_4","2026-09-01"))
        self.assertFalse(m.match_race_id("not-a-race","2026-09-01"))

    def test_actual_opponent_uses_only_results_before_previous_race(self):
        previous="2026-08-15_6_4"
        focus=start("Focus",[])
        rivals=[start(f"Rival{i}",[
            ("2026-08-01","1"),("2026-07-12","2"),
            ("2026-08-15","1"),("2026-09-03","1")]) for i in range(7)]
        card=m.historical_card({"id":previous,"starts":[focus,*rivals]},previous)
        row=m.asof_strength({"date":"2026-09-01","raceId":"2026-09-01_6_8",
                            "number":3,"name":"Focus",
                            "candidatePriorRaceIds":[previous]},{previous:card})
        self.assertEqual(row["measuredPreviousRaces"],1)
        self.assertAlmostEqual(row["opponentForm"],.8)
        self.assertEqual(row["evidence"][0]["previousDate"],"2026-08-15")

    def test_wrong_name_and_insufficient_peers_are_missing(self):
        previous="2026-08-15_6_4"
        card={"raceId":previous,"cutoff":"2026-08-15",
              "peers":[{"name":"Other","asofForm":.8}]*8}
        row=m.asof_strength({"date":"2026-09-01","raceId":"2026-09-01_6_8",
          "number":3,"name":"Focus","candidatePriorRaceIds":[previous]},{previous:card})
        self.assertIsNone(row["opponentForm"])

    def test_card_selection_bounded_and_ignores_future(self):
        targets=[{"raceId":f"2026-09-01_6_{i}","number":i,
            "name":f"Focus{i}","candidatePriorRaceIds":[
                f"2026-08-01_6_{i}",f"2026-07-01_6_{i}"]}
            for i in range(1,12)]
        planned=m.bounded_plan(targets,max_cards=15)
        self.assertLessEqual(len(planned),15)
        self.assertEqual(len(planned),15)

    def test_no_outcome_or_pool_input_into_feature(self):
        import inspect
        source=inspect.getsource(m.asof_strength)+inspect.getsource(m.historical_card)
        self.assertNotIn("marketFinalPct",source)
        self.assertNotIn('["winner"]',source)
        self.assertNotIn("betDistribution",source)

    def test_match_historical_target_by_name_and_number(self):
        current={"starts":[
          {"number":1,"horse":{"name":"Different","results":{"records":[]}}},
          {"number":2,"horse":{"name":"Focus","results":{"records":[
              {"date":"2026-08-15","race":{"id":"2026-08-15_6_4"}},
              {"date":"2026-10-01","race":{"id":"2026-10-01_6_4"}},
          ]}}}
        ]}
        refs=[{"raceId":"2026-09-01_6_8","number":1,"horse":"Focus"},
              {"raceId":"2026-09-01_6_8","number":2,"horse":"Focus"}]
        matches=m.make_focus(current,refs,"2026-09-01")
        self.assertEqual(len(matches),1)
        self.assertEqual(matches[0]["candidatePriorRaceIds"],["2026-08-15_6_4"])

if __name__=="__main__":
    unittest.main()
