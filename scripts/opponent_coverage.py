#!/usr/bin/env python3
"""Expand actual-opponent evidence across ALL current Bjerke runners.

Research only; never alters live ranking, odds or horse probability forecasts.
Uses opponent's races STRICTLY before the historical race's date (not before
today). Fetches a bounded selection with two workers, caches successful cards.
No fabricated score when dated comparison data are insufficient.
"""
from __future__ import annotations
import concurrent.futures
import datetime as dt
import json
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict

try:
    from scripts.opponent_probe import ident, prior_opponent_form
except ModuleNotFoundError:
    from opponent_probe import ident, prior_opponent_form

ROOT=pathlib.Path(__file__).resolve().parents[1]
SOURCE=ROOT/"bjerke-form-20261031.json"
DEST=ROOT/"research/opponent_coverage_2026.json"
BASE="https://www.atg.se/services/racinginfo/v1/api/races/"
MAX_DISTINCT_RACES=100
WORKERS=2
DAY=dt.date(2026,10,31)
ID="V85_2026-10-31_78_5"


def build_plan(doc, limit=MAX_DISTINCT_RACES):
    """Fair first sweep: one previous start per horse before adding seconds."""
    plans={}
    horses=[]
    for race in doc["races"]:
        leg=race["leg"]
        for horse in race["horses"]:
            if horse.get("scratched"):
                continue
            horses.append({"leg":leg,"number":horse["number"],"name":horse["name"],
                           "lastFive":horse.get("lastFive") or []})
    if not horses or limit<1:
        raise ValueError("No active runners")
    # Include duplicates of selected earlier races for any horse that raced there.
    for offset in range(3):
        for horse in horses:
            past=horse["lastFive"]
            if offset>=len(past):
                continue
            prior=past[offset]
            rid=prior.get("raceId")
            if not isinstance(rid,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d+_\d+",rid):
                continue
            if dt.date.fromisoformat(rid[:10])>=DAY:
                continue
            if rid not in plans and len(plans)>=limit:
                continue
            key=(horse["leg"],horse["number"],ident(horse["name"]))
            refs=plans.setdefault(rid,[])
            if key not in {(x["leg"],x["number"],ident(x["name"])) for x in refs}:
                refs.append({"leg":horse["leg"],"number":horse["number"],"name":horse["name"]})
    return plans,horses


def parse_card(payload,race_id):
    if not isinstance(payload,dict) or payload.get("id")!=race_id:
        raise ValueError("Historical race id mismatch")
    try:
        cutoff=dt.date.fromisoformat(race_id[:10])
    except ValueError as e:
        raise ValueError("Invalid dated race identifier") from e
    starts=payload.get("starts")
    if not isinstance(starts,list) or not 6<=len(starts)<=22:
        raise ValueError("Invalid historical starters")
    peers=[]
    for s in starts:
        if not isinstance(s,dict):
            continue
        h=s.get("horse") if isinstance(s.get("horse"),dict) else {}
        n=h.get("name")
        if not isinstance(n,str):
            continue
        res=s.get("result") if isinstance(s.get("result"),dict) else {}
        if s.get("scratched") is True or res.get("scratched") is True:
            continue
        peers.append({"name":n,"form":prior_opponent_form(s,cutoff)})
    if len(peers)<6:
        raise ValueError("Too few non-scratched historical competitors")
    return {"raceId":race_id,"cutoff":cutoff.isoformat(),"peers":peers}


def assess_card(card,focus):
    matches=[x for x in card["peers"] if ident(x["name"])==ident(focus["name"])]
    if len(matches)!=1:
        return {"leg":focus["leg"],"number":focus["number"],"name":focus["name"],
                "raceId":card["raceId"],"cutoff":card["cutoff"],"match":False,
                "rivals":None,"rated":0,"mean":None,"coverage":None}
    others=[x["form"] for x in card["peers"] if ident(x["name"])!=ident(focus["name"])]
    valid=[p for p in others if type(p) in (float,int)]
    enough=len(valid)>=max(4,(len(others)+1)//2)
    return {"leg":focus["leg"],"number":focus["number"],"name":focus["name"],
            "raceId":card["raceId"],"cutoff":card["cutoff"],"match":True,
            "rivals":len(others),"rated":len(valid),
            "mean":round(sum(valid)/len(valid),4) if enough and valid else None,
            "coverage":round(len(valid)/len(others),3) if others else None}


def fetch_card(race_id):
    request=urllib.request.Request(BASE+race_id+"/extended",headers={
        "User-Agent":"LA_V85-research/opponents-2.0","Accept":"application/json"})
    with urllib.request.urlopen(request,timeout=28) as response:
        payload=json.load(response)
    return parse_card(payload,race_id)


def summarize(plan,horses,cards,errors):
    rows=[]
    for rid,refs in plan.items():
        card=cards.get(rid)
        if not card:
            continue
        for ref in refs:
            rows.append(assess_card(card,ref))
    by_horse=defaultdict(list)
    for row in rows:
        by_horse[(row["leg"],row["number"])].append(row)
    collected=[]
    for horse in horses:
        own=by_horse.get((horse["leg"],horse["number"]),[])
        valid=[x for x in own if x["match"] and x["mean"] is not None]
        # Mean across earlier separate opponents' races is not a calibrated
        # rating; retain evidence count, don't impute missing numbers.
        score=round(sum(x["mean"] for x in valid)/len(valid),4) if valid else None
        collected.append({"leg":horse["leg"],"number":horse["number"],
                          "name":horse["name"],"coveredPreviousRaces":len(own),
                          "validPreviousRaces":len(valid),
                          "opponentFormMean":score,
                          "priorRaceIds":[x["raceId"] for x in valid]})
    return {
        "schemaVersion":2,"gameId":ID,"currentRaceDate":DAY.isoformat(),
        "method":"Prior results of actual opponents BEFORE each sampled historical race; never outcomes or data from/after the sampled race.",
        "limitations":"Not validated as predictive. Incomplete records and historical API revisions can reduce reliable coverage. Uses 0-1 proxy of past wins/top-3, not opponent ratings calibrated to race class.",
        "plannedDistinctRaces":len(plan),"readableDistinctRaces":len(cards),
        "activeHorses":len(horses),"horsesWithAnyReference":sum(bool(by_horse.get((h["leg"],h["number"]))) for h in horses),
        "horsesWithValidForm":sum(x["opponentFormMean"] is not None for x in collected),
        "failures":[{"raceId":rid,"type":msg} for rid,msg in sorted(errors.items())],
        "historicalCards":{rid:cards[rid] for rid in plan if rid in cards},
        "references":rows,"horses":collected,
    }


def main():
    original=json.loads(SOURCE.read_text(encoding="utf8"))
    if original.get("gameId")!=ID or len(original.get("races",[]))!=8:
        raise ValueError("Wrong Bjerke start list")
    plan,horses=build_plan(original)
    previous=json.loads(DEST.read_text(encoding="utf8")) if DEST.exists() else {}
    cached=previous.get("historicalCards") or {}
    cards={rid:card for rid,card in cached.items() if rid in plan and
           isinstance(card,dict) and card.get("raceId")==rid and isinstance(card.get("peers"),list)}
    to_fetch=[rid for rid in plan if rid not in cards]
    errors={}
    # Concurrent requests capped at two to limit load on unofficial endpoint.
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        futs={pool.submit(fetch_card,rid):rid for rid in to_fetch}
        for fut in concurrent.futures.as_completed(futs):
            rid=futs[fut]
            try: cards[rid]=fut.result()
            except (urllib.error.URLError,TimeoutError,ValueError,TypeError,KeyError,json.JSONDecodeError) as ex:
                errors[rid]=type(ex).__name__+": "+str(ex)[:90]
    result=summarize(plan,horses,cards,errors)
    if result["readableDistinctRaces"]<16:
        raise ValueError("Too little verified historical evidence; do not publish")
    if result==previous:
        print("OPPONENT COVERAGE unchanged");return
    DEST.parent.mkdir(parents=True,exist_ok=True)
    DEST.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf8")
    print("OPPONENT COVERAGE",result["readableDistinctRaces"],"/",result["plannedDistinctRaces"],
          "historical races;",result["horsesWithValidForm"],"/",result["activeHorses"],"horses rated")


if __name__=="__main__":
    try: main()
    except (OSError,ValueError,KeyError,TypeError,json.JSONDecodeError) as ex:
        print("Coverage not ready:",str(ex),file=sys.stderr)
        sys.exit(1)
