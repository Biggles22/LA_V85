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
import statistics
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
    if type(value) in (int, float):
        return float(value)
    if isinstance(value, str) and re.fullmatch(r"\d+(?:\.\d+)?", value.strip()):
        return float(value.strip())
    return None


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
    horse = start.get("horse") if isinstance(start.get("horse"), dict) else {}
    for source in (horse.get("results"), start.get("results")):
        if isinstance(source, dict) and isinstance(source.get("records"), list):
            return source["records"]
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
    prize = number(race.get("firstPrize"))
    country = (record.get("track") or {}).get("countryCode") if isinstance(record.get("track"), dict) else None
    method = race.get("startMethod")
    post = number(start.get("postPosition"))
    raw_time = record.get("kmTime") if isinstance(record.get("kmTime"), dict) else {}
    mins, secs, tenths = (number(raw_time.get(k)) for k in ("minutes", "seconds", "tenths"))
    kilometre_seconds = None
    if mins is not None and secs is not None:
        candidate_time = 60 * mins + secs + (tenths or 0) / 10
        if 60 <= candidate_time <= 160:
            kilometre_seconds = round(candidate_time, 2)
    return {
        "date": when.isoformat(),
        "place": int(placed) if placed is not None else None,
        "country": country if country in ("SE", "NO", "DK", "FI") else None,
        "pastFirstPrize": prize if prize is not None and prize > 0 else None,
        "postPosition": int(post) if post is not None and 1 <= post <= 20 else None,
        "startMethod": method if method in ("auto", "volte") else None,
        "kmSeconds": kilometre_seconds,
        "galloped": has_gallop if galloped is not None or disqualified is not None else None,
        "distance": int(distance) if distance is not None and 800 <= distance <= 6000 else None,
        "raceId": race.get("id") or None,
    }


def performance(place, galloped):
    # A horse can gallop, recover and still WIN. Never turn a confirmed
    # first place into a bottom performance solely because gallop=True.
    if place is None:
        return 0.2 if galloped is True else None
    if place == 1:
        base = 5.0
    elif place == 2:
        base = 4.0
    elif place == 3:
        base = 3.3
    elif place <= 5:
        base = 2.5
    elif place <= 8:
        base = 1.5
    else:
        base = 0.7
    return max(0.2, base - 0.4) if galloped is True else base


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
        "evidence": {"classStarts": 0, "paceStarts": 0, "classCountries": [],
                     "modelCoverageWeight": 0, "partialRankScore": None},
        "coverage": {
            "form": f is not None, "risk": risk is not None,
            "pace": False, "class": False, "gear": False
        },
        "status": "partial" if known else ("history_only" if recent else "no_history"),
        "note": (
            "Form från tidigare starter; spår/tempo och klass beräknas först när jämförbar historik räcker."
            if known else "Otillräcklig verifierad historik för automatisk bedömning."
        ),
    }



def percentile(value, samples):
    """0-1 empirical midrank; robust to tied samples."""
    if not samples:
        return None
    below = sum(x < value for x in samples)
    equal = sum(x == value for x in samples)
    return (below + equal / 2) / len(samples)


def score_draw(post, method):
    """Only a rough current gate-position indicator: never an inferred lead chance."""
    if method != "auto" or not isinstance(post, int) or post < 1:
        return None
    gates = {1: 4.3, 2: 4.7, 3: 4.7, 4: 4.5, 5: 4.1, 6: 3.4, 7: 2.8, 8: 2.2}
    return gates.get(post, max(0.8, 2.0 - 0.13 * (post - 9)))


def add_contextual_scores(results, market_races):
    """Intra-field, prestart evidence only. Do not use betting/odds or future races.

    Class proxy: prior first-prize tiers normalized within past-race country.
    Pace proxy: past comparable-km times (not sectional speed) and draw, auto only.
    We leave these scores missing when evidence does not justify a comparison.
    """
    for race, market in zip(results, market_races):
        current = {h["number"]: h for h in market["starts"]}
        horses = [h for h in race["horses"] if not h["scratched"]]
        # Compare horse history only with runners in the same upcoming leg.
        prize_by_country = {}
        for h in horses:
            for past in h["lastFive"]:
                country, prize = past.get("country"), past.get("pastFirstPrize")
                if country is not None and isinstance(prize, (int, float)):
                    prize_by_country.setdefault(country, []).append(prize)
        valid_countries = {
            country: values for country, values in prize_by_country.items()
            if len(values) >= 9 and len(set(values)) >= 3
        }
        for h in horses:
            relevant = []
            for past in h["lastFive"]:
                country = past.get("country")
                prize = past.get("pastFirstPrize")
                if country not in valid_countries or not isinstance(prize, (int, float)):
                    continue
                p = performance(past.get("place"), past.get("galloped"))
                if p is not None:
                    relevant.append((percentile(prize, valid_countries[country]), p))
            if len(relevant) >= 2:
                tier = statistics.mean(x[0] for x in relevant[:5])
                achieved = statistics.mean(x[1] for x in relevant[:5]) / 5
                # Thresholds are heuristic; not trained or probability calibrated.
                h["scores"]["class"] = round(min(5, max(0, 5 * (0.65 * tier + 0.35 * achieved))), 2)
                h["evidence"]["classStarts"] = len(relevant)
                h["evidence"]["classCountries"] = sorted({p["country"] for p in h["lastFive"]
                    if p.get("country") in valid_countries and isinstance(p.get("pastFirstPrize"), (int, float))})
                h["coverage"]["class"] = True

        method = race.get("startMethod")
        if method == "auto":
            times = {}
            # Normalized timing is only comparable within approximately matching distances.
            for h in horses:
                current_dist = current[h["number"]].get("distance")
                values = [x["kmSeconds"] for x in h["lastFive"]
                    if x.get("kmSeconds") is not None and x.get("startMethod") == "auto"
                    and x.get("galloped") is not True and x.get("distance") is not None
                    and isinstance(current_dist, (int, float))
                    and abs(x["distance"] - current_dist) <= 170]
                if len(values) >= 2:
                    times[h["number"]] = round(statistics.median(values), 2)
            if len(times) >= 5 and len(set(times.values())) >= 3:
                sample = list(times.values())
                for h in horses:
                    if h["number"] not in times:
                        continue
                    post = current[h["number"]].get("postPosition")
                    draw = score_draw(post, method)
                    if draw is None:
                        continue
                    fast_pct = 1 - percentile(times[h["number"]], sample)
                    h["scores"]["pace"] = round(0.65 * fast_pct * 5 + 0.35 * draw, 2)
                    h["evidence"]["paceStarts"] = sum(
                        x.get("kmSeconds") is not None and x.get("startMethod") == "auto"
                        and x.get("galloped") is not True and x.get("distance") is not None
                        and abs(x["distance"] - current[h["number"]]["distance"]) <= 170
                        for x in h["lastFive"])
                    h["coverage"]["pace"] = True
        for h in horses:
            known = [(h["scores"][k], w) for k, w in (("form", 30), ("pace", 25), ("class", 20),
                     ("gear", 15), ("risk", 10)) if h["scores"][k] is not None]
            total = sum(w for _, w in known)
            h["evidence"]["modelCoverageWeight"] = total
            # At least two independent evidence dimensions; never a complete 100-point ranking.
            if len(known) >= 2 and total >= 45:
                h["evidence"]["partialRankScore"] = round(sum(v / 5 * w for v, w in known) / total * 100, 1)
            if h["scores"]["pace"] is not None or h["scores"]["class"] is not None:
                h["status"] = "partial"
                h["note"] = "Historisk prestations-, tempo/spår- och klassproxy där data finns; ingen säker spetsprognos."

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
            results.append({"leg": leg, "raceNumber": race_number, "startMethod": payload.get("startMethod"),
                            "sourceUrl": url, "horses": parsed})
        except (urllib.error.URLError, TimeoutError, ValueError, KeyError, json.JSONDecodeError) as err:
            failures.append({"leg": leg, "error": type(err).__name__ + ": " + str(err)[:160]})
            results.append({
                "leg": leg, "raceNumber": race_number, "startMethod": None,
                "sourceUrl": f"{API}2026-10-31_78_{race_number}/extended",
                "horses": [analysis_entry(h, None) for h in race["starts"]],
            })
        time.sleep(0.25)
    add_contextual_scores(results, original["races"])
    flat = [h for r in results for h in r["horses"] if not h["scratched"]]
    with_history = sum(h["previousStarts"] >= 1 for h in flat)
    rated = sum(h["scores"]["form"] is not None for h in flat)
    rated_risk = sum(h["scores"]["risk"] is not None for h in flat)
    rated_pace = sum(h["scores"]["pace"] is not None for h in flat)
    rated_class = sum(h["scores"]["class"] is not None for h in flat)
    partial = sum(h["evidence"]["partialRankScore"] is not None for h in flat)
    if not flat or len(results) != 8:
        raise ValueError("Bad analysis output")
    if len(failures) == 8:
        # Do not overwrite an existing valid form report with a network outage.
        print("All eight extended requests failed; previous report retained.")
        print(json.dumps(failures, ensure_ascii=False))
        return 1
    result = {
        "schemaVersion": 2, "gameId": ID, "track": "Bjerke",
        "raceDate": DAY.isoformat(), "atgSourceAt": original.get("sourceAt"),
        "method": "Backward-only performance, pace/draw proxy, and past purse-tier class proxy; NOT a calibrated win probability.",
        "limitations": "Pace approximates pace suitability using recorded km times and the current draw (NOT verified lead probability). Class compares previous first prizes ONLY within the same country and field, with past finishing performance. Not a calibrated prediction. Gear and many risks remain unknown. Scores never use odds or V85 betting percentages.",
        "coverage": {
            "activeHorses": len(flat), "horsesWithHistory": with_history,
            "formRated": rated, "riskRated": rated_risk,
            "paceRated": rated_pace, "classRated": rated_class,
            "partialRanked": partial,
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
    print(f"Form: {rated}/{len(flat)}, class: {rated_class}, pace: {rated_pace}, "
          f"partial: {partial}, histories: {with_history}, risk: {rated_risk}, failures: {len(failures)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
