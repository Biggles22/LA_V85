#!/usr/bin/env python3
"""As-of historical-rival pilot: past opponents of historical V85 runners.

Two strict cutoffs per feature:
  current V85 race date > the runner's previous race date > opponent's form dates.
All winners and market data are OUTSIDE this feature computation.
Bounded unofficial ATG requests; coverage report comes before ML evaluation.
"""
from __future__ import annotations

import concurrent.futures
import datetime as dt
import hashlib
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from collections import defaultdict

try:
    from scripts.opponent_probe import ident, prior_opponent_form
except ModuleNotFoundError:
    from opponent_probe import ident, prior_opponent_form

ROOT=pathlib.Path(__file__).resolve().parents[1]
HISTORY=ROOT/"research/historical_pilot_2026.json"
OUT=ROOT/"research/historical_opponent_asof_2026.json"
BASE="https://www.atg.se/services/racinginfo/v1/api/races/"
RE_RACE=re.compile(r"^(\d{4}-\d{2}-\d{2})_\d+_\d+$")
MAX_TARGETS=42
MAX_PRIOR_CARDS=380
WORKERS=3


def match_race_id(race_id,upper_bound):
    found=RE_RACE.fullmatch(str(race_id or ""))
    return bool(found and dt.date.fromisoformat(found.group(1))<dt.date.fromisoformat(upper_bound))


def get_extended(rid):
    req=urllib.request.Request(BASE+rid+"/extended",headers={
        "User-Agent":"LA-V85-research/dated-opponent-1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=28) as response:
        item=json.load(response)
    if not isinstance(item,dict) or item.get("id")!=rid:
        raise ValueError("Wrong response race identifier")
    if not isinstance(item.get("starts"),list):
        raise ValueError("Missing starters")
    return item


def pick_historical_races(rows,limit=MAX_TARGETS):
    bydate=defaultdict(set)
    for x in rows:
        bydate[x["date"]].add(x["raceId"])
    dates=sorted(bydate)
    # Two race cards per date, spread over earlier and later parts of history;
    # fixed selection, not based on winners, odds, or observed predictions.
    selected=[]
    for date in dates:
        for rid in sorted(bydate[date])[:2]:
            selected.append((date,rid))
    if len(selected)>limit:
        # Evenly sample without looking at any race outcome.
        indices=sorted(set(round(i*(len(selected)-1)/(limit-1)) for i in range(limit)))
        selected=[selected[i] for i in indices]
    return selected


def make_focus(extended, historical_rows, target_date):
    starts={}
    for s in extended.get("starts",[]):
        if isinstance(s,dict) and type(s.get("number")) is int:
            starts[s["number"]]=s
    available=[]
    for row in historical_rows:
        n=row["number"]
        start=starts.get(n)
        if not start:continue
        horse=start.get("horse")
        if not isinstance(horse,dict) or ident(horse.get("name"))!=ident(row["horse"]):
            continue
        result=horse.get("results")
        previous=result.get("records",[]) if isinstance(result,dict) else []
        dated=[]
        for record in previous:
            if not isinstance(record,dict):continue
            past=record.get("race")
            rid=past.get("id") if isinstance(past,dict) else None
            if not match_race_id(rid,target_date):continue
            dated.append(rid)
        # unique, newest first, for a stable prestart-only selection
        dated=sorted(set(dated),reverse=True)[:3]
        available.append({"date":target_date,"raceId":row["raceId"],
                          "number":n,"name":row["horse"],
                          "candidatePriorRaceIds":dated})
    return available


def bounded_plan(targets,max_cards=MAX_PRIOR_CARDS,cached_ids=()):
    """Keep published research, extending the sample to newer test dates.

    The initial bounded pilot had concentrated on earlier dates. Never
    silently drop validated source cards; prioritize later dates next.
    """
    existing=set(cached_ids)
    selected={}
    for target in targets:
        for rid in target["candidatePriorRaceIds"]:
            if rid in existing:
                selected.setdefault(rid,set()).add((target["raceId"],target["number"]))
    if len(selected)>max_cards:
        raise ValueError("More verified cards than request budget")
    for depth in range(3):
        for target in reversed(targets):
            history=target["candidatePriorRaceIds"]
            if depth>=len(history):continue
            rid=history[depth]
            if rid not in selected and len(selected)>=max_cards:
                continue
            selected.setdefault(rid,set()).add((target["raceId"],target["number"]))
    return selected

def historical_card(data,rid):
    """Only historical rivals' form before the previous race, no result label."""
    cutoff=dt.date.fromisoformat(rid[:10])
    if not 6<=len(data["starts"])<=22:
        raise ValueError("Invalid previous race field")
    peers=[]
    for s in data["starts"]:
        if not isinstance(s,dict):continue
        horse=s.get("horse")
        if not isinstance(horse,dict) or not isinstance(horse.get("name"),str):
            continue
        res=s.get("result") if isinstance(s.get("result"),dict) else {}
        if s.get("scratched") is True or res.get("scratched") is True:
            continue
        peers.append({"name":horse["name"],"asofForm":prior_opponent_form(s,cutoff)})
    if len(peers)<6:raise ValueError("Too few historical rivals")
    return {"raceId":rid,"cutoff":cutoff.isoformat(),"peers":peers}


def asof_strength(target, prior_cards):
    """Return score and provenance only if the focus matches exactly once."""
    values=[];details=[]
    for prior_id in target["candidatePriorRaceIds"]:
        card=prior_cards.get(prior_id)
        if card is None:continue
        names=[p for p in card["peers"] if ident(p["name"])==ident(target["name"])]
        if len(names)!=1:continue
        rivals=[p["asofForm"] for p in card["peers"] if ident(p["name"])!=ident(target["name"])]
        valid=[v for v in rivals if type(v) in (float,int)]
        needed=max(4,(len(rivals)+1)//2)
        if len(valid)<needed:continue
        mean=round(sum(valid)/len(valid),4)
        values.append(mean)
        details.append({"previousRaceId":prior_id,"previousDate":card["cutoff"],
                        "ratedRivals":len(valid),"rivals":len(rivals),"mean":mean})
    return {"date":target["date"],"raceId":target["raceId"],
            "number":target["number"],"horse":target["name"],
            "opponentForm":round(sum(values)/len(values),4) if values else None,
            "measuredPreviousRaces":len(values),"evidence":details}


def main():
    doc=json.loads(HISTORY.read_text(encoding="utf8"))
    historical=defaultdict(list)
    for row in doc["rows"]:
        historical[row["raceId"]].append(row)
    selected=pick_historical_races(doc["rows"])
    if not selected:raise ValueError("Empty historical selection")
    # Cache immutable compact cards in previously published report.
    previous=json.loads(OUT.read_text(encoding="utf8")) if OUT.exists() else {}
    all_cards=previous.get("previousRaceCards",{})
    target_cache=previous.get("targets",{})
    targets=[];target_failures={}
    to_fetch=[rid for _,rid in selected if rid not in target_cache]
    fetched={}
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        tasks={pool.submit(get_extended,rid):rid for rid in to_fetch}
        for task in concurrent.futures.as_completed(tasks):
            rid=tasks[task]
            try:fetched[rid]=task.result()
            except (urllib.error.URLError,TimeoutError,ValueError,KeyError,json.JSONDecodeError) as ex:
                target_failures[rid]=type(ex).__name__+": "+str(ex)[:90]
    for date,rid in selected:
        if rid in target_cache:
            targets.extend(target_cache[rid])
        elif rid in fetched:
            found=make_focus(fetched[rid],historical[rid],date)
            target_cache[rid]=found
            targets.extend(found)
    plan=bounded_plan(targets,cached_ids=all_cards)
    prior_failures={}
    needed=[rid for rid in plan if rid not in all_cards]
    with concurrent.futures.ThreadPoolExecutor(max_workers=WORKERS) as pool:
        tasks={pool.submit(get_extended,rid):rid for rid in needed}
        for task in concurrent.futures.as_completed(tasks):
            rid=tasks[task]
            try: all_cards[rid]=historical_card(task.result(),rid)
            except (urllib.error.URLError,TimeoutError,ValueError,KeyError,json.JSONDecodeError) as ex:
                prior_failures[rid]=type(ex).__name__+": "+str(ex)[:90]
    used_cards={rid:all_cards[rid] for rid in plan if rid in all_cards}
    prepared=[]
    for t in targets:
        # Restrict the card pool to selected bounded IDs; unselected previous
        # races must not appear merely because of a stale cache.
        report=asof_strength(t,used_cards)
        prepared.append(report)
    rated=sum(x["opponentForm"] is not None for x in prepared)
    races_with_any={x["raceId"] for x in prepared if x["opponentForm"] is not None}
    if len(prepared)<75 or len(races_with_any)<10:
        raise ValueError("Insufficient matched historical sample; refusing model output")
    report={
      "schemaVersion":1,"sourceRaceCount":doc["raceCount"],
      "method":"Previous-opponents' past results with two historical cutoffs; no present-race result or pool input.",
      "warning":"Small deterministic research sample, no calibrated probabilities; historical ATG API coverage may change.",
      "selectedCurrentRaces":len(selected),
      "readableCurrentRaces":len(target_cache),
      "matchedCurrentHorseStarts":len(prepared),
      "ratedCurrentHorseStarts":rated,
      "currentRacesWithRatedStarters":len(races_with_any),
      "plannedPreviousRaceCards":len(plan),
      "readablePreviousRaceCards":len(used_cards),
      "targetFailures":[{"raceId":k,"error":v} for k,v in sorted(target_failures.items())],
      "previousFailures":[{"raceId":k,"error":v} for k,v in sorted(prior_failures.items())],
      "targets":{rid:target_cache[rid] for _,rid in selected if rid in target_cache},
      "previousRaceCards":used_cards,
      "rows":prepared,
    }
    if report==previous:
        print("ASOF-OPPONENT unchanged");return
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(json.dumps(report,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf8")
    print("ASOF-OPPONENT",len(selected),"target races",len(prepared),"matched starters",
          rated,"rated; prior cards",len(used_cards),"/",len(plan),flush=True)


if __name__=="__main__":
    try:main()
    except (ValueError,KeyError,TypeError,OSError) as error:
        print("ASOF-OPPONENT unavailable:",error,file=sys.stderr)
        sys.exit(1)
