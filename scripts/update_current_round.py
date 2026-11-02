#!/usr/bin/env python3
"""Import an identified ATG V85 game; never fabricate entries or overwrite an archive.

Run from the repository: python scripts/update_current_round.py
Existing snapshots survive every discovery, schema, network and time validation error.
Editorial proposals are reviewed separately in the current round's analysis.json.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import math
import pathlib
import tempfile
import urllib.request
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parents[1]
BASE = "https://www.atg.se/services/racinginfo/v1/api"
TZ = ZoneInfo("Europe/Stockholm")


def numeric(value):
    return type(value) in (int, float) and math.isfinite(value)


def time_value(value):
    if not isinstance(value, str):
        raise ValueError("Verified source/start timestamp missing")
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    # ATG pool timestamps without an offset are Swedish local wall time.
    return stamp.replace(tzinfo=TZ) if stamp.tzinfo is None else stamp.astimezone(TZ)


def get_json(path):
    req = urllib.request.Request(BASE + path, headers={"Accept": "application/json", "User-Agent": "LA_V85/round-import"})
    with urllib.request.urlopen(req, timeout=25) as response:
        doc = json.load(response)
    if not isinstance(doc, dict):
        raise ValueError("ATG did not return a JSON object")
    return doc


def game_ids(calendar, date):
    games = calendar.get("games", {})
    entries = games.get("V85", []) if isinstance(games, dict) else games
    if isinstance(entries, dict):
        entries = [entries]
    return list(dict.fromkeys(x["id"] for x in entries if isinstance(x, dict)
                             and str(x.get("id", "")).startswith("V85_" + date + "_")))


def normalize(game, round_info, now):
    date, track = round_info["date"], round_info["track"]
    if not str(game.get("id", "")).startswith("V85_" + date + "_"):
        raise ValueError("Wrong game/date")
    races = game.get("races", [])
    if not isinstance(races, list) or len(races) != 8:
        raise ValueError("Expected exactly eight V85 races")
    if any((r.get("track") or {}).get("name") != track for r in races):
        raise ValueError("Wrong track")
    race_ids = [r.get("id") for r in races]
    if any(not isinstance(rid, str) or not rid.startswith(date + "_") for rid in race_ids) or len(set(race_ids)) != 8:
        raise ValueError("Invalid or duplicate race identities")
    starts_at = [time_value(r.get("startTime")) for r in races]
    if any(t.date().isoformat() != date for t in starts_at):
        raise ValueError("Race start date does not match calendar")
    pool = (game.get("pools") or {}).get("V85") or {}
    first_start = min(starts_at)
    deadline = time_value(pool["bettingDeadline"]) if pool.get("bettingDeadline") else first_start
    if deadline > first_start or deadline.date().isoformat() != date:
        raise ValueError("Invalid betting deadline")
    source_at = time_value(pool.get("timestamp"))
    if now >= deadline or source_at >= deadline:
        raise ValueError("Round started; prestart snapshots cannot be updated")
    if source_at > now + dt.timedelta(minutes=5):
        raise ValueError("Source timestamp is in the future")
    def person(value):
        return " ".join(x for x in [value.get("firstName"), value.get("lastName")] if isinstance(x, str)) or value.get("name") or ""
    output = []
    for leg, race in enumerate(races, 1):
        seen, horses = set(), []
        if not isinstance(race.get("starts"), list) or not race["starts"]:
            raise ValueError("Empty start list")
        for start in race["starts"]:
            number, horse = start.get("number"), start.get("horse") or {}
            if type(number) is not int or number < 1 or number in seen or not isinstance(horse.get("name"), str) or not horse["name"].strip():
                raise ValueError("Invalid or duplicate horse")
            seen.add(number)
            market = (start.get("pools") or {}).get("V85") or {}
            pct = market.get("betDistribution")
            if not numeric(pool.get("turnover")) or pool["turnover"] <= 0:
                pct = None
            if pct is not None and (not numeric(pct) or not 0 <= pct <= 10000):
                raise ValueError("Invalid market distribution")
            odd = ((start.get("pools") or {}).get("vinnare") or {}).get("odds")
            trend = market.get("trend")
            trainer = horse.get("trainer") or {}
            # Only explicit pre-race history is retained; missing history remains empty.
            history = []
            for record in (horse.get("results") or {}).get("records", []):
                if not isinstance(record, dict):
                    continue
                raw_date = record.get("date")
                try:
                    past_date = dt.date.fromisoformat(str(raw_date)[:10])
                except ValueError:
                    continue
                if past_date >= dt.date.fromisoformat(date):
                    continue
                place = record.get("place")
                description = "Placering " + str(place) if type(place) is int and place > 0 else "Placering saknas"
                if record.get("galloped") is True:
                    description += " · galopp"
                history.append({"date": past_date.isoformat(), "description": description})
            history = sorted(history, key=lambda x: x["date"], reverse=True)[:5]
            horses.append({"number": number, "name": horse["name"], "driver": person(start.get("driver") or {}),
                           "trainer": person(trainer), "postPosition": start.get("postPosition"),
                           "distance": start.get("distance") or race.get("distance"), "scratched": start.get("scratched") is True,
                           "pct": round(pct/100, 2) if numeric(pct) else None,
                           "odds": round(odd/100, 2) if numeric(odd) and 0 < odd < 9999 else None,
                           "oddsCapped": odd == 9999, "trend": round(trend*100, 2) if numeric(trend) else None,
                           "history": history})
        output.append({"leg": leg, "raceId": race["id"], "raceNumber": race.get("number"),
                       "distance": race.get("distance"), "startMethod": race.get("startMethod"),
                       "startTime": starts_at[leg-1].isoformat(), "starts": horses})
    record = {"schemaVersion": 1, "roundId": round_info["id"], "date": date, "track": track,
              "status": "verified", "gameId": game["id"], "sourceUrl": BASE + "/games/" + game["id"],
              "sourceAt": source_at.isoformat(), "retrievedAt": now.isoformat(), "startTime": deadline.isoformat(),
              "unitStakeSEK": None, "turnoverSEK": round(pool["turnover"]/100, 2) if numeric(pool.get("turnover")) else None,
              "races": output}
    digest = {k: v for k, v in record.items() if k != "retrievedAt"}
    record["snapshotId"] = hashlib.sha256(json.dumps(digest, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return record


def write_snapshot(destination, candidate):
    previous = json.loads(destination.read_text()) if destination.exists() else {}
    if previous.get("roundId") not in (None, candidate["roundId"]):
        raise ValueError("Destination belongs to another round")
    if previous.get("sourceAt") and time_value(previous["sourceAt"]) > time_value(candidate["sourceAt"]):
        raise ValueError("Refusing to replace a newer source snapshot")
    if previous.get("snapshotId") == candidate["snapshotId"]:
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", dir=destination.parent, encoding="utf8", delete=False) as temp:
        json.dump(candidate, temp, ensure_ascii=False, indent=2)
        temp.write("\n")
        temp_path = pathlib.Path(temp.name)
    temp_path.replace(destination)
    return True


def main():
    config = json.loads((ROOT / "rounds.json").read_text())
    round_info = next(r for r in config["rounds"] if r["id"] == config["current"])
    if round_info.get("status") == "completed":
        raise ValueError("Current round is archived")
    destination = (ROOT / round_info["data"]).resolve()
    if not destination.is_relative_to(ROOT / "rounds" / round_info["id"]):
        raise ValueError("Current snapshot destination must be inside its own round directory")
    now = dt.datetime.now(TZ)
    if now.date().isoformat() > round_info["date"]:
        print("Round date has passed; no prestart update.")
        return
    calendar = get_json("/calendar/day/" + round_info["date"])
    ids = game_ids(calendar, round_info["date"])
    if not ids:
        raise ValueError("No V85 game published for requested date")
    candidates = []
    for gid in ids:
        game = get_json("/games/" + gid)
        if game.get("id") != gid:
            raise ValueError("Returned game differs from calendar identity")
        if game.get("races") and all((r.get("track") or {}).get("name") == round_info["track"] for r in game["races"]):
            candidates.append(normalize(game, round_info, now))
    if len(candidates) != 1:
        raise ValueError("Could not identify exactly one matching V85 round")
    changed = write_snapshot(destination, candidates[0])
    print("Updated" if changed else "Unchanged", round_info["id"], candidates[0]["sourceAt"])


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, StopIteration, OSError) as error:
        raise SystemExit("Import stopped; previous snapshot preserved: " + str(error))
