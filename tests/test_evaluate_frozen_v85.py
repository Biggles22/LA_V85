"""Only post-race confirmed winners may score prospectively frozen forecasts."""
import datetime as dt
import unittest
from zoneinfo import ZoneInfo
from scripts import evaluate_frozen_v85 as m
from scripts import freeze_v85_forecasts as f

TZ=ZoneInfo("Europe/Stockholm")


def fixtures():
    racecards=[];extended={};reports=[]
    for leg in range(1,9):
        rid=f"2026-10-31_78_{leg+4}"
        racecards.append({"id":rid,"status":"results"})
        starts=[{"number":n,"horse":{"name":f"Runner {leg}-{n}"},
                 "result":{"place":str(n)}} for n in range(1,9)]
        extended[rid]={"id":rid,"status":"results","starts":starts}
        reports.append({
            "leg":leg,"raceId":rid,
            "runners":[{"number":n,"horse":f"Runner {leg}-{n}"} for n in range(1,9)],
            "baseTop3":[1,2,3],"opponentTop3":[2,1,3],"marketTop3":[3,2,1],
        })
    game={"id":f.ID,"races":racecards}
    frozen={"kind":"FROZEN_PROSPECTIVE_RESEARCH_NOT_BETTING_ADVICE",
            "gameId":f.ID,"slot":"friday",
            "frozenAt":"2026-10-30T18:04:00+01:00",
            "marketSourceAt":"2026-10-30T18:01:00+01:00",
            "races":reports}
    return game,extended,frozen


class Tests(unittest.TestCase):
    def test_verifiable_eight_winners_and_paired_scores(self):
        game,cards,frozen=fixtures()
        winners=m.verified_results(game,cards)
        self.assertEqual(len(winners),8)
        outcome=m.score_frozen(frozen,winners)
        self.assertEqual(outcome["metrics"]["base"]["top1"],8)
        self.assertEqual(outcome["metrics"]["opponents"]["top1"],0)
        self.assertEqual(outcome["metrics"]["opponents"]["top3"],8)
        self.assertEqual(outcome["metrics"]["atg"]["top3"],8)

    def test_duplicate_winner_is_rejected(self):
        game,cards,_=fixtures()
        cards["2026-10-31_78_5"]["starts"][1]["result"]["place"]="1"
        with self.assertRaisesRegex(ValueError,"uniquely"):
            m.verified_results(game,cards)

    def test_incomplete_results_are_rejected(self):
        game,cards,_=fixtures()
        cards["2026-10-31_78_5"]["starts"][0]["result"]={}
        with self.assertRaisesRegex(ValueError,"uniquely"):
            m.verified_results(game,cards)

    def test_frozen_after_off_rejected(self):
        game,cards,frozen=fixtures()
        frozen["frozenAt"]="2026-10-31T15:01:00+01:00"
        with self.assertRaisesRegex(ValueError,"AFTER"):
            m.score_frozen(frozen,m.verified_results(game,cards))

    def test_current_race_id_and_name_must_match(self):
        game,cards,frozen=fixtures()
        frozen["races"][0]["runners"][0]["horse"]="DIFFERENT"
        with self.assertRaisesRegex(ValueError,"identical"):
            m.score_frozen(frozen,m.verified_results(game,cards))

    def test_sunday_timing_is_guarded(self):
        self.assertEqual(m.to_place("1"),1)
        self.assertIsNone(m.to_place("u"))
        with self.assertRaisesRegex(ValueError,"November 1"):
            m.evaluate(dt.datetime(2026,10,31,21,0,tzinfo=TZ))


if __name__=="__main__":
    unittest.main()
