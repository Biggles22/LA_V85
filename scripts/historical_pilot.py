#!/usr/bin/env python3
"""Leakage-safe pilot of *past* V85 starts. Research only, no betting advice.

Unversioned ATG site API: endpoints may change; source use must comply with ATG terms.
Do not use today's mutable horse.statistics, career money or final odds as model features.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import math
import pathlib
import re
import statistics
import time
import urllib.error
import urllib.request

BASE = "https://www.atg.se/services/racinginfo/v1/api"
ROOT = pathlib.Path(__file__).resolve().parents[1]
DEST = ROOT / "research/historical_pilot_2026.json"
USER_AGENT = "LA_V85/research-1.0 (Biggles22/LA_V85; low-frequency research)"
# Saturdays spread over several months; no upcoming or live meetings.
DATES = ("2026-03-14","2026-03-21","2026-03-28","2026-04-11",
         "2026-09-19","2026-09-26","2026-10-03","2026-10-10",
         "2026-10-17","2026-10-24")
# Track IDs either confirmed from LA_V85 archive or candidate match with race calendar.
TRACK_CANDIDATES={"2026-03-14":78,"2026-03-21":6,"2026-03-28":5,
                  "2026-04-11":7,"2026-09-19":15,"2026-09-26":6,
                  "2026-10-03":11,"2026-10-10":5,"2026-10-17":16,
                  "2026-10-24":7}
KNOWN_GAME_IDS={
    "2026-10-03":"V85_2026-10-03_11_5",
    "2026-10-10":"V85_2026-10-10_5_6",
    "2026-10-17":"V85_2026-10-17_16_5",
    "2026-10-24":"V85_2026-10-24_7_5",
}


def get_json(path):
    req = urllib.request.Request(BASE+path, headers={
        "User-Agent":USER_AGENT,"Accept":"application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        value = json.load(response)
    if not isinstance(value, dict):
        raise ValueError("ATG endpoint did not return an object")
    return value


def number(value):
    if type(value) in (int,float) and math.isfinite(value):
        return float(value)
    if isinstance(value,str) and re.fullmatch(r"\d+(?:\.\d+)?",value.strip()):
        return float(value.strip())
    return None


def date_only(value):
    if isinstance(value,str):
        try:
            return dt.date.fromisoformat(value[:10])
        except ValueError:
            pass
    return None


def get_v85_id(calendar):
    games = calendar.get("games") or {}
    if isinstance(games,dict):
        item=games.get("V85")
        if isinstance(item,dict) and isinstance(item.get("id"),str):
            return item["id"]
        if isinstance(item,list):
            for x in item:
                if isinstance(x,dict) and isinstance(x.get("id"),str):
                    return x["id"]
    elif isinstance(games,list):
        for item in games:
            if isinstance(item,dict) and str(item.get("id","")).startswith("V85_"):
                return item["id"]
    # Never invent a game from track IDs; report discovery failure.
    raise ValueError("No V85 game id in ATG calendar")


def discover_game(date):
    """Try calendar, then bounded, *validated* V85 game-ID candidates.

    Known October IDs come from this repository's archived snapshots.
    Earlier candidates are probed, never assumed to be valid.
    """
    attempts=[]
    candidates=[]
    try:
        calendar=get_json("/calendar/day/"+date)
        candidates.append(get_v85_id(calendar))
    except (urllib.error.URLError,ValueError,KeyError) as ex:
        attempts.append("calendar "+type(ex).__name__+" "+str(ex)[:100])
    if date in KNOWN_GAME_IDS:
        candidates.append(KNOWN_GAME_IDS[date])
    track=TRACK_CANDIDATES.get(date)
    if track is not None:
        candidates.extend(f"V85_{date}_{track}_{num}" for num in (5,6,7))
    for gid in dict.fromkeys(candidates):
        try:
            game=get_json("/games/"+gid)
            if game.get("id")==gid and len(game.get("races") or [])==8 and gid.startswith("V85_"+date+"_"):
                return gid,game
            attempts.append(gid+" mismatched game ID/races")
        except (urllib.error.URLError,ValueError,KeyError) as ex:
            attempts.append(gid+" "+type(ex).__name__+" "+str(ex)[:80])
    raise ValueError("No verified game for "+date+": "+"; ".join(attempts[-5:]))


def past_records(start, race_day):
    horse = start.get("horse") or {}
    data = horse.get("results") or start.get("results") or {}
    entries = data.get("records",[]) if isinstance(data,dict) else []
    kept=[]
    for r in entries:
        if not isinstance(r,dict):
            continue
        when=date_only(r.get("date"))
        if not when or not when < race_day:
            continue
        race=r.get("race") or {}
        st=r.get("start") or {}
        position=number(r.get("place"))
        if position is not None and not (1<=position<=30):
            position=None
        dist=number(st.get("distance"))
        if dist is None:
            dist=number(race.get("distance"))
        when_id=(when.isoformat(),race.get("id"))
        purse=number(race.get("firstPrize"))
        timer=r.get("kmTime") or {}
        minutes=number(timer.get("minutes"))
        seconds=number(timer.get("seconds"))
        tenths=number(timer.get("tenths"))
        km=(60*minutes+seconds+(tenths or 0)/10) if minutes is not None and seconds is not None else None
        track=r.get("track") or {}
        kept.append({
            "date":when.isoformat(),"id":str(race.get("id") or ""),
            "place":int(position) if position is not None else None,
            "gallop":r.get("galloped") is True or r.get("disqualified") is True,
            "hasGallopFlag":type(r.get("galloped")) is bool or type(r.get("disqualified")) is bool,
            "distance":dist, "method":race.get("startMethod"),
            "purse":purse, "country":track.get("countryCode"),
            "km":km if km is not None and 60<=km<=160 else None,
            "dedup":when_id,
        })
    kept.sort(key=lambda v:v["date"],reverse=True)
    seen=set(); result=[]
    for item in kept:
        if item["dedup"] in seen:continue
        seen.add(item["dedup"]);item.pop("dedup")
        result.append(item)
    return result


def features_from_history(start,race,race_day,field_size):
    rows=past_records(start,race_day)
    recent=rows[:5]
    valid=[r for r in recent if r["place"] is not None]
    gap=(race_day-date_only(rows[0]["date"])).days if rows else None
    kms=[r["km"] for r in recent if r["km"] is not None
         and r["distance"] is not None
         and abs(r["distance"]-race.get("distance",0))<=170]
    country=(race.get("track") or {}).get("countryCode")
    # Prize comparisons limited to the same country; past purses in cents.
    purses=[r["purse"] for r in recent if r["country"]==country and r["purse"] is not None]
    gallop_flags=[r["gallop"] for r in recent if r["hasGallopFlag"]]
    return {
        "post":number(start.get("postPosition")),
        "distance":number(start.get("distance")) or number(race.get("distance")),
        "field":field_size,"auto":1 if race.get("startMethod")=="auto" else 0,
        "starts5":len(recent),
        "form_place_mean":round(statistics.mean(r["place"] for r in valid),3) if len(valid)>=2 else None,
        "win5":sum(r["place"]==1 for r in valid) if len(valid)>=2 else None,
        "top3_5":sum(r["place"]<=3 for r in valid) if len(valid)>=2 else None,
        "days_off":gap,
        "gallop5":sum(gallop_flags)/len(gallop_flags) if len(gallop_flags)>=2 else None,
        "km_median":round(statistics.median(kms),2) if len(kms)>=2 else None,
        "past_purse_log":round(math.log1p(statistics.median(purses)),3) if len(purses)>=2 else None,
    }


def market_distribution(game, race_id):
    for r in game.get("races",[]):
        if not isinstance(r,dict) or r.get("id")!=race_id:
            continue
        entries={}
        for s in r.get("starts",[]):
            pct=number(((s.get("pools") or {}).get("V85") or {}).get("betDistribution"))
            if pct is not None:
                entries[s.get("number")]=pct/100
        return entries
    return {}


def parse_historical_race(race,game,date):
    day=dt.date.fromisoformat(date)
    rid=race.get("id")
    if race.get("status")!="results" or not rid or not isinstance(race.get("starts"),list):
        return None
    entries=[]; failed=0
    for start in race["starts"]:
        if not isinstance(start,dict):
            continue
        horse=start.get("horse") or {}
        result=start.get("result") or {}
        if not isinstance(result,dict):
            result={}
        if start.get("scratched") is True or result.get("scratched") is True or horse.get("scratched") is True:
            continue
        if not isinstance(horse.get("name"),str) or not isinstance(start.get("number"),int):
            failed+=1;continue
        place=number(result.get("place"))
        if place is None or not (0<=place<=30):
            failed+=1;continue
        entries.append((start,horse,place))
    if failed or not 6<=len(entries)<=20:
        return None
    winners=[x for x in entries if x[2]==1]
    if len(winners)!=1:
        return None   # skip dead heats and uncertain winner labels
    field_size=len(entries)
    market=market_distribution(game,rid)
    rows=[]
    for start,horse,place in entries:
        rows.append({
            "date":date,"raceId":rid,"track":(race.get("track") or {}).get("name"),
            "gameId":game.get("id"),"number":start["number"],"horse":horse["name"],
            "winner":int(place==1),"prestartFeatures":features_from_history(start,race,day,field_size),
            "marketFinalPct":market.get(start["number"]),
        })
    return rows


def collect(dates):
    output=[]; roundlog=[]; included=set()
    for date in dates:
        try:
            game_id,game=discover_game(date)
            races=game.get("races") or []
            if len(races)!=8:
                raise ValueError("V85 game does not contain 8 races")
            count=0; eligible=0
            for r in races:
                rid=r.get("id")
                if not isinstance(rid,str):
                    continue
                try:
                    extended=get_json("/races/"+rid+"/extended")
                    if extended.get("id")!=rid:
                        raise ValueError("Race ID mismatch")
                    parsed=parse_historical_race(extended,game,date)
                    eligible+=1
                    if parsed and rid not in included:
                        output.extend(parsed);included.add(rid);count+=1
                except (urllib.error.URLError,ValueError,TimeoutError,KeyError) as ex:
                    print("RACE_SKIP",date,rid,type(ex).__name__,str(ex)[:100],flush=True)
                time.sleep(0.18)
            roundlog.append({"date":date,"gameId":game_id,"completeRaces":count,
                             "attemptedRaces":eligible,"status":"ok" if count else "no_results"})
            print("ROUND",date,game_id,"accepted",count,"of",eligible,flush=True)
        except (urllib.error.URLError,ValueError,TimeoutError,KeyError) as ex:
            roundlog.append({"date":date,"status":"failed","reason":type(ex).__name__+": "+str(ex)[:130]})
            print("ROUND_FAILED",date,type(ex).__name__,str(ex)[:130],flush=True)
        time.sleep(0.25)
    return output,roundlog


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--limit",type=int,default=len(DATES))
    args=parser.parse_args()
    if not 1<=args.limit<=len(DATES):
        parser.error("invalid --limit")
    rows,log=collect(DATES[:args.limit])
    dates={x["date"] for x in rows}
    races={x["raceId"] for x in rows}
    print("SUMMARY",len(rows),"starters",len(races),"completed races",len(dates),"dates",flush=True)
    if len(dates)<2 or len(races)<8:
        raise SystemExit("Insufficient validated history; refusing to publish a misleading dataset")
    report={"schemaVersion":1,"gameTypes":["V85"],
            "asOfDate":"2026-10-27",
            "method":"Historical V85 horse past-start features, each filtered strictly before that race's date.",
            "leakageControls":"No post-race statistics, final odds or pooled percentages used as input features.",
            "marketWarning":"marketFinalPct is retrospective close-of-pool data; NOT an archived verified prestart market snapshot.",
            "source":"ATG site racinginfo API (unofficial, subject to terms/availability)",
            "dates":list(DATES[:args.limit]),"rounds":log,
            "starterCount":len(rows),"raceCount":len(races),"rows":rows}
    DEST.parent.mkdir(parents=True,exist_ok=True)
    previous=json.loads(DEST.read_text()) if DEST.exists() else None
    if previous==report:
        print("No changes to historical data");return
    DEST.write_text(json.dumps(report,ensure_ascii=False,separators=(",",":"))+"\n")
    print("Saved",DEST,flush=True)


if __name__=="__main__":
    main()
