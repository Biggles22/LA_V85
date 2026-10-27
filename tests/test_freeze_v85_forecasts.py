"""Prospective-only freeze validation; no actual ATG calls in tests."""
import datetime as dt
import unittest
from unittest import mock
from zoneinfo import ZoneInfo
from scripts import freeze_v85_forecasts as f

TZ=ZoneInfo("Europe/Stockholm")

def market_and_ext():
    races=[]; extended={}
    for leg in range(1,9):
        rid=f"2026-10-31_78_{leg+4}"
        entries=[]
        for i in range(1,11):
            entries.append({"number":i,
                            "horse":{"name":f"Runner {leg}-{i}"},
                            "postPosition":i,"distance":2100,
                            "pools":{"V85":{"betDistribution":1000}}})
        races.append({"id":rid,"number":leg+4,"status":"bettable",
                      "starts":entries})
        extended[rid]={"id":rid,"startMethod":"auto","distance":2100,
                       "track":{"countryCode":"NO"},"starts":entries}
    return {"id":f.ID,
            "pools":{"V85":{"timestamp":"2026-10-30 17:55:00"}},
            "races":races},extended


class FreezeTests(unittest.TestCase):
    def test_slot_times_are_time_zone_aware_and_guarded(self):
        self.assertTrue(f.in_slot(dt.datetime(2026,10,30,18,0,tzinfo=TZ),"friday"))
        self.assertFalse(f.in_slot(dt.datetime(2026,10,30,17,59,tzinfo=TZ),"friday"))
        self.assertFalse(f.in_slot(dt.datetime(2026,10,31,14,14,tzinfo=TZ),"saturday"))
        self.assertTrue(f.in_slot(dt.datetime(2026,10,31,14,15,tzinfo=TZ),"saturday"))
        self.assertFalse(f.in_slot(dt.datetime(2026,10,31,15,0,tzinfo=TZ),"saturday"))
        self.assertFalse(f.in_slot(dt.datetime(2026,10,31,16,0,tzinfo=TZ),"preview"))
        with self.assertRaisesRegex(ValueError,"timezone"):
            f.in_slot(dt.datetime(2026,10,30,18,10),"friday")

    def test_identical_eight_active_races_required(self):
        game,extended=market_and_ext()
        now=dt.datetime(2026,10,30,18,2,tzinfo=TZ)
        snapshot=f.checked_snapshot(game,now)
        rows=f.current_rows(game,extended,snapshot)
        self.assertEqual(len(rows),80)
        self.assertTrue(all(row["prestartFeatures"]["field"]==10 for row in rows))
        extended["2026-10-31_78_5"]["starts"][0]["horse"]["name"]="WRONG"
        with self.assertRaisesRegex(ValueError,"mismatch"):
            f.current_rows(game,extended,snapshot)

    def test_scratch_and_missing_card_are_not_silent(self):
        game,extended=market_and_ext()
        now=dt.datetime(2026,10,30,18,2,tzinfo=TZ)
        snap=f.checked_snapshot(game,now)
        extended.pop("2026-10-31_78_5")
        with self.assertRaisesRegex(ValueError,"Missing identical"):
            f.current_rows(game,extended,snap)

    def test_normalization_is_labelled_uncalibrated(self):
        rows=[{"leg":i,"number":j} for i in range(1,9) for j in range(1,9)]
        result=f.race_distribution(rows,[0.1]*len(rows))
        self.assertEqual(len(result),64)
        self.assertAlmostEqual(sum(result[(1,k)] for k in range(1,9)),100,places=2)

    def test_build_rejects_out_of_slot_before_network(self):
        with mock.patch.object(f,"get_json",side_effect=AssertionError("Never access network")):
            with self.assertRaisesRegex(ValueError,"prestart"):
                f.build("saturday",dt.datetime(2026,10,31,15,1,tzinfo=TZ))

    def test_six_hour_market_age_guard(self):
        game,extended=market_and_ext()
        now=dt.datetime(2026,10,30,23,58,tzinfo=TZ)
        with self.assertRaisesRegex(ValueError,"six hours"):
            f.build("friday",now,game=game,extended=extended,
                    historical={"rows":[]} ,opponent_historical={},coverage={})


if __name__=="__main__":
    unittest.main()
