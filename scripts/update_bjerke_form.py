#!/usr/bin/env python3
"""Collect point-in-time past performances for V85 Bjerke 2026-10-31.

ATG's /races/{id}/extended endpoint is not a documented/stable public API.
If historical data is missing, publish coverage status, never fabricated scores.
Uses only previous races; does not use V85 percentages, trends or win odds for scoring.
"""
from __future__ import annotations

import datetime as dt
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / "bjerke-20261031.json"
DEST = ROOT / "bjerke-form-20261031.json"
DAY = dt.date(2026, 10, 31)
ID = "V85_2026-10-31_78_5"
STOP = dt.datetime(2026, 10, 31, 15, 0, tzinfo=dt.timezone(dt.timedelta(hours=1)))
API = "https://www.atg.se/services/racinginfo/v1/api/races/"
HEADERS = {"Accept": "application/json", "User-Agent": "LA-V85-formanalysis/1.0 (GitHub: Biggles22/LA_V85)"}


def normalize(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return re.sub(r"[^a-z0-9]", "", "".join(ch for ch in value if not unicodedata.combining(ch)))


def as_date(value):
    if isinstance(value, str):
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            pass
    return None


def number(value):
    return float(value) if type(value) in (int, float) else None


def fetch_extended(race_number):
    url = f"{API}2026-10-31_78_{race_number}/extended"
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=28) as response:
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get("starts"), list):
        raise ValueError("Missing starts array")
    return data, url


def records_of(start):
    # Published reference: results.records; tolerate missing/alternate wrappers.
    results = start.get("results")
    if isinstance(results, dict) and isinstance(results.get("records"), list):
        return results["records"]
    if isinstance(start.get("records"), list):
        return start["records"]
    return []


def parse_record(record):
    if not isinstance(record, dict):
        return None
    race = record.get("race") if isinstance(record.get("race"), dict) else {}
    start = record.get("start") if isinstance(record.get("start"), dict) else {}
    when = as_date(record.get("date")) or as_date(race.get("date"))
    if when is None or not when < DAY:
        return None
    distance = number(start.get("distance"))
    if distance is None:
        distance = number(race.get("distance"))
    placed = number(record.get("finishOrder"))
    if placed is None or placed <= 0 or placed >= 30:
        placed = number(record.get("place"))
    if placed is not None and (placed < 0 or placed >= 30):
        placed = None
    galloped = record.get("galloped")
    disqualified = record.get("disqualified")
    has_gallop = galloped is True or disqualified is True
    return {
        "date": when.isoformat(),
        "place": int(placed) if placed is not None else None,
        "galloped": has_gallop if galloped is not None or disqualified is not None else None,
        "distance": int(distance) if distance is not None and 800 <= distance <= 6000 else None,
        "raceId": race.get("id") or record.get("link"),
    }


def performance(place, galloped):
    if galloped is True:
        return 0.2
    if place is None:
        return None
    if place == 1:
        return 5.0
    if place == 2:
        return 4.0
    if place == 3:
        return 3.3
    if place <= 5:
        return 2.5
    if place <= 8:
        return 1.5
    return 0.7


def score_form(rows):
    vals = [performance(r["place"], r["galloped"]) for r in rows[:5]]
    accepted = [(v, max(0.35, 1.0 - i * 0.14)) for i, v in enumerate(vals) if v is not None]
    if len(accepted) < 2:
        return None
    return round(sum(v * w for v, w in accepted) / sum(w for _, w in accepted), 2)


def score_risk(rows):
    if len(rows) < 3:
        return None
    recent = rows[:5]
    # Unknown gallop flags do not count as "no gallop".
    flags = [r["galloped"] for r in recent if r["galloped"] is not None]
    if len(flags) < 2:
        return None
    gap = (DAY - dt.date.fromisoformat(recent[0]["date"])).days
    risk = 5.0 - min(3.0, 5.0 * sum(flags) / len(flags))
    if gap > 150:
        risk -= 1.75
    elif gap > 75:
        risk -= 1.0
    elif gap > 40:
        risk -= 0.35
    return round(max(0.0, min(5.0, risk)), 2)


def score_distance(rows, metres):
    if not isinstance(metres, (int, float)):
        return None
    similar = [r for r in rows if r["distance"] is not None and abs(r["distance"] - metres) <= 170]
    vals = [performance(r["place"], r["galloped"]) for r in similar[:5]]
    vals = [x for x in vals if x is not None]
    return round(sum(vals) / len(vals), 2) if len(vals) >= 2 else None


def analysis_entry(horse, extended_start):
    recent = []
    if extended_start:
        records = records_of(extended_start)
        recent = [x for row in records if (x := parse_record(row)) is not None]
        # A buggy API response may repeat the same start; do not double-count.
        seen = set()
        dedup = []
        for row in sorted(recent, key=lambda x: x["date"], reverse=True):
            ident = (row["date"], str(row["raceId"]), row["place"])
            if ident not in seen:
                dedup.append(row)
                seen.add(ident)
        recent = dedup
    f = score_form(recent)
    risk = score_risk(recent)
    dist = score_distance(recent, horse.get("distance"))
    known = sum(x is not None for x in (f, risk))
    return {
        "number": horse["number"], "name": horse["name"],
        "scratched": bool(horse.get("scratched")),
        "previousStarts": len(recent),
        "lastFive": recent[:5],
        "scores": {
            "form": f, "pace": None, "class": None, "gear": None, "risk": risk
        },
        "distanceOnlyScore": dist,
        "coverage": {
            "form": f is not None, "risk": risk is not None,
            "pace": False, "class": False, "gear": False
        },
        "status": "partial" if known else ("history_only" if recent else "no_history"),
        "note": (
            "Form från senaste lopp; distansprov separat. Loppbild, klass och utrustning kräver verifiering."
            if known else "Otillräcklig verifierad historik för automatisk bedömning."
        ),
    }


def main():
    now = dt.datetime.now(dt.timezone(dt.timedelta(hours=1)))
    if now >= STOP:
        print("Start passed: historical snapshot is frozen.")
        return 0
    original = json.loads(SOURCE.read_text(encoding="utf-8"))
    if original.get("gameId") != ID or len(original.get("races", [])) != 8:
        raise ValueError("Invalid current game data")
    results = []
    failures = []
    for race in original["races"]:
        leg = race["leg"]
        race_number = race["raceNumber"]
        try:
            payload, url = fetch_extended(race_number)
            starts = payload["starts"]
            # Match BOTH number and horse name. If an API race doesn't align, do not mislabel history.
            found = {}
            for s in starts:
                if not isinstance(s, dict):
                    continue
                h = s.get("horse") if isinstance(s.get("horse"), dict) else {}
                found[s.get("number")] = (normalize(h.get("name")), s)
            if len(starts) < max(5, len(race["starts"]) - 2):
                raise ValueError("Too few starters in extended response")
            parsed = []
            for h in race["starts"]:
                candidate = found.get(h["number"])
                item = candidate[1] if candidate and candidate[0] == normalize(h["name"]) else None
                parsed.append(analysis_entry(h, item))
            results.append({"leg": leg, "raceNumber": race_number, "sourceUrl": url, "horses": parsed})
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as err:
            failures.append({"leg": leg, "error": type(err).__name__ + ": " + str(err)[:160]})
            results.append({
                "leg": leg, "raceNumber": race_number,
                "sourceUrl": f"{API}2026-10-31_78_{race_number}/extended",
                "horses": [analysis_entry(h, None) for h in race["starts"]],
            })
        time.sleep(0.25)
    flat = [h for r in results for h in r["horses"] if not h["scratched"]]
    with_history = sum(h["previousStarts"] >= 1 for h in flat)
    rated = sum(h["scores"]["form"] is not None for h in flat)
    rated_risk = sum(h["scores"]["risk"] is not None for h in flat)
    if not flat or len(results) != 8:
        raise ValueError("Bad analysis output")
    if len(failures) == 8:
        # Do not overwrite an existing valid form report with a network outage.
        print("All eight extended requests failed; previous report retained.")
        print(json.dumps(failures, ensure_ascii=False))
        return 1
    result = {
        "schemaVersion": 1, "gameId": ID, "track": "Bjerke",
        "raceDate": DAY.isoformat(), "atgSourceAt": original.get("sourceAt"),
        "method": "Backward-only last-five form score; NOT a calibrated win probability.",
        "limitations": "Pace, class and equipment are not inferred from odds, popularity or start number. No full 100-point automatic ranking.",
        "coverage": {
            "activeHorses": len(flat), "horsesWithHistory": with_history,
            "formRated": rated, "riskRated": rated_risk,
            "failedRaces": len(failures),
        },
        "failures": failures, "races": results,
    }
    old = json.loads(DEST.read_text(encoding="utf-8")) if DEST.exists() else {}
    comparable = {k: v for k, v in result.items() if k != "retrievedAt"}
    if {k: v for k, v in old.items() if k != "retrievedAt"} == comparable:
        print("No new form information; keeping existing snapshot.")
        return 0
    result["retrievedAt"] = now.isoformat()
    DEST.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Form: {rated}/{len(flat)}, histories: {with_history}, risk: {rated_risk}, failures: {len(failures)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
