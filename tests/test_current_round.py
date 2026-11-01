import copy
import datetime as dt
import json
import pathlib
import tempfile
import unittest
from scripts import update_current_round as importer

ROUND = {"id": "2026-11-07-bergsaker", "date": "2026-11-07", "track": "Bergsåker"}
NOW = dt.datetime.fromisoformat("2026-11-02T12:00:00+01:00")


def game():
    """Synthetic API-shaped input, never published as racing data."""
    return {"id": "V85_2026-11-07_9_5", "pools": {"V85": {"timestamp": "2026-11-02 11:59:00", "turnover": 123400}},
            "races": [{"id": f"2026-11-07_9_{leg+4}", "number": leg+4, "track": {"name": "Bergsåker"},
                       "startTime": f"2026-11-07T{14+leg}:00:00+01:00", "distance": 2140, "startMethod": "auto",
                       "starts": [{"number": 1, "horse": {"name": f"Testhäst {leg}", "results": {"records": [
                           {"date": "2026-10-25", "place": 2}, {"date": "2026-11-07", "place": 1}]}},
                                   "pools": {"V85": {"betDistribution": 1234, "trend": 0.012}, "vinnare": {"odds": 9999}}}]}
                      for leg in range(1, 9)]}


class CurrentRoundTests(unittest.TestCase):
    def test_calendar_discovery_does_not_invent_ids(self):
        self.assertEqual(importer.game_ids({"games": {}}, ROUND["date"]), [])
        self.assertEqual(importer.game_ids({"games": {"V85": [{"id": "V85_2026-11-07_9_5"}, {"id": "V85_2026-10-31_78_5"}]}}, ROUND["date"]), ["V85_2026-11-07_9_5"])

    def test_normalizes_verified_source_and_filters_future_history(self):
        result = importer.normalize(game(), ROUND, NOW)
        horse = result["races"][0]["starts"][0]
        self.assertEqual(horse["pct"], 12.34)
        self.assertEqual(horse["trend"], 1.2)
        self.assertIsNone(horse["odds"])
        self.assertTrue(horse["oddsCapped"])
        self.assertEqual(len(horse["history"]), 1)
        self.assertEqual(result["sourceAt"], "2026-11-02T11:59:00+01:00")
        self.assertEqual(result["startTime"], "2026-11-07T15:00:00+01:00")

    def test_missing_stakes_remain_missing(self):
        raw = game()
        raw["races"][0]["starts"][0]["pools"] = {}
        result = importer.normalize(raw, ROUND, NOW)
        self.assertIsNone(result["races"][0]["starts"][0]["pct"])
        self.assertIsNone(result["unitStakeSEK"])

    def test_wrong_round_and_track_are_rejected(self):
        for mutate in (lambda g: g.update(id="V85_2026-10-31_78_5"),
                       lambda g: g["races"][3]["track"].update(name="Bjerke")):
            with self.subTest(mutate=mutate):
                raw = game()
                mutate(raw)
                with self.assertRaises(ValueError):
                    importer.normalize(raw, ROUND, NOW)

    def test_duplicate_or_missing_races_are_rejected(self):
        raw = game()
        raw["races"][1]["id"] = raw["races"][0]["id"]
        with self.assertRaises(ValueError):
            importer.normalize(raw, ROUND, NOW)
        raw = game()
        raw["races"].pop()
        with self.assertRaises(ValueError):
            importer.normalize(raw, ROUND, NOW)

    def test_duplicate_horses_are_rejected(self):
        raw = game()
        raw["races"][0]["starts"] *= 2
        with self.assertRaises(ValueError):
            importer.normalize(raw, ROUND, NOW)

    def test_invalid_market_data_is_rejected(self):
        raw = game()
        raw["races"][0]["starts"][0]["pools"]["V85"]["betDistribution"] = 10001
        with self.assertRaises(ValueError):
            importer.normalize(raw, ROUND, NOW)

    def test_no_prestart_capture_after_start(self):
        with self.assertRaises(ValueError):
            importer.normalize(game(), ROUND, dt.datetime.fromisoformat("2026-11-07T15:00:00+01:00"))

    def test_missing_start_time_never_defaults_to_a_guess(self):
        raw = game()
        raw["races"][0].pop("startTime")
        with self.assertRaises(ValueError):
            importer.normalize(raw, ROUND, NOW)

    def test_source_timestamp_in_future_rejected(self):
        raw = game()
        raw["pools"]["V85"]["timestamp"] = "2026-11-03T15:00:00+01:00"
        with self.assertRaises(ValueError):
            importer.normalize(raw, ROUND, NOW)

    def test_repeat_capture_is_stable_and_older_capture_cannot_overwrite(self):
        candidate = importer.normalize(game(), ROUND, NOW)
        repeated = importer.normalize(game(), ROUND, NOW + dt.timedelta(minutes=2))
        self.assertEqual(candidate["snapshotId"], repeated["snapshotId"])
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / "data.json"
            self.assertTrue(importer.write_snapshot(target, candidate))
            original = target.read_bytes()
            self.assertFalse(importer.write_snapshot(target, repeated))
            self.assertEqual(target.read_bytes(), original)
            older = copy.deepcopy(candidate)
            older["sourceAt"] = "2026-11-01T10:00:00+01:00"
            older["snapshotId"] = "older"
            with self.assertRaises(ValueError):
                importer.write_snapshot(target, older)
            self.assertEqual(target.read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
