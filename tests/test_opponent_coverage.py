"""Tests for fair coverage and strictly dated rival evidence."""
import datetime as dt
import unittest
from scripts import opponent_coverage as m

def source():
    races=[]
    for leg in range(1,9):
        starts=[]
        for n in range(1,11):
            starts.append({"number":n,"name":f"Horse {leg}-{n}",
                           "lastFive":[{"raceId":f"2026-10-{20+n%5:02d}_{leg}_{n}"}],
                           "scratched":False})
        races.append({"leg":leg,"horses":starts})
    return {"races":races}

class CoverageTests(unittest.TestCase):
    def test_first_pass_covers_different_runners(self):
        plan,horses=m.build_plan(source(),limit=100)
        self.assertEqual(len(horses),80)
        self.assertEqual(len(plan),80)
        counts={(h["leg"],h["number"]) for refs in plan.values() for h in refs}
        self.assertEqual(len(counts),80)

    def test_limit_and_date_cutoff(self):
        doc=source()
        doc["races"][0]["horses"][0]["lastFive"]=[
            {"raceId":"2026-10-31_1_2"},
            {"raceId":"2026-10-29_1_2"}]
        plan,_=m.build_plan(doc,limit=10)
        self.assertLessEqual(len(plan),10)
        self.assertNotIn("2026-10-31_1_2",plan)

    def test_prior_opponents_not_historical_finishing_result(self):
        rid="2026-09-10_7_2"
        def horse(name,history):
            return {"horse":{"name":name,"results":{"records":history}},
                    "result":{"place":1}}
        starts=[horse("Focus",[])]
        for i in range(1,9):
            starts.append(horse(f"Other {i}",[
                {"date":"2026-09-01","place":str(1+i%3)},
                {"date":"2026-08-20","place":"2"},
                {"date":"2026-09-10","place":"1"}, # MUST NOT COUNT
                {"date":"2026-10-12","place":"1"}, # MUST NOT COUNT
            ]))
        card=m.parse_card({"id":rid,"starts":starts},rid)
        ref=m.assess_card(card,{"leg":1,"number":3,"name":"Focus"})
        self.assertTrue(ref["match"])
        self.assertEqual(ref["rated"],8)
        self.assertGreater(ref["mean"],0.2)

    def test_unknown_peers_are_not_zero(self):
        rid="2026-09-10_7_2"
        card={"raceId":rid,"cutoff":"2026-09-10",
              "peers":[{"name":"Focus","form":None}]+[
                  {"name":f"Rival {i}","form":None} for i in range(8)]}
        ref=m.assess_card(card,{"leg":1,"number":3,"name":"Focus"})
        self.assertFalse(ref["mean"] is not None)
        self.assertEqual(ref["rated"],0)
        out=m.summarize({rid:[{"leg":1,"number":3,"name":"Focus"}]},
                        [{"leg":1,"number":3,"name":"Focus"}],{rid:card},{})
        self.assertEqual(out["horsesWithValidForm"],0)
        self.assertIsNone(out["horses"][0]["opponentFormMean"])

    def test_does_not_compare_wrong_horse(self):
        card={"raceId":"2026-09-10_7_2","cutoff":"2026-09-10",
              "peers":[{"name":"Another","form":.4}]*8}
        result=m.assess_card(card,{"leg":1,"number":3,"name":"Focus"})
        self.assertFalse(result["match"])
        self.assertIsNone(result["mean"])

if __name__=="__main__":
    unittest.main()
