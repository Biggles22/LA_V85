#!/usr/bin/env python3
"""Bounded pilot: Bjerke runners' *former opponents'* prior form at race date.

Each previous race is fetched once. NEVER compute an opponent's quality using
runs on/after that previous race, and never read odds/betDistribution. This is
only a research coverage/provenance probe, not a trained win-probability model.
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

ROOT=pathlib.Path(__file__).resolve().parents[1]
INPUT=ROOT/"bjerke-form-20261031.json"
OUTPUT=ROOT/"research/opponent_probe_2026.json"
BASE="https://www.atg.se/services/racinginfo/v1/api/races/"
MAX_RACES=16


def ident(name):
    raw=unicodedata.normalize("NFKD",str(name or "")).casefold()
    return re.sub("[^a-z0-9]","",''.join(x for x in raw if not unicodedata.combining(x)))


def prior_opponent_form(start,cutoff):
    """A crude past win/top-3 score, based solely on records < prior race date."""
    horse=start.get("horse") if isinstance(start.get("horse"),dict) else {}
    data=horse.get("results") if isinstance(horse.get("results"),dict) else {}
    records=data.get("records",[])
    if not isinstance(records,list):return None
    prior=[]
    for entry in records:
        if not isinstance(entry,dict):continue
        date=entry.get("date")
        if not isinstance(date,str):continue
        try:
            when=dt.date.fromisoformat(date[:10])
        except ValueError:
            continue
        if when>=cutoff:continue
        place=entry.get("place")
        if isinstance(place,str) and place.isdigit():
            place=int(place)
        if type(place) is not int or not 1<=place<=30:continue
        prior.append((when,place))
    prior=sorted(prior,key=lambda x:x[0],reverse=True)[:5]
    if len(prior)<2:return None
    won=sum(place==1 for _,place in prior)/len(prior)
    top3=sum(place<=3 for _,place in prior)/len(prior)
    # 0..1 proxy, only prior performances, not opponent race's final outcome.
    return round(0.6*won+0.4*top3,4)


def opponent_context(race,targets):
    if not isinstance(race,dict) or race.get("id") not in targets:
        raise ValueError("Mismatched historical race")
    try: cutoff=dt.date.fromisoformat(race["id"][:10])
    except ValueError as e: raise ValueError("Unparseable race date") from e
    starts=race.get("starts")
    if not isinstance(starts,list) or len(starts)<6:
        raise ValueError("Missing historical field")
    ratings=[]
    for s in starts:
        if not isinstance(s,dict):continue
        h=s.get("horse") or {}
        if not isinstance(h,dict):continue
        score=prior_opponent_form(s,cutoff)
        if s.get("scratched") is not True and (s.get("result") or {}).get("scratched") is not True:
            ratings.append((ident(h.get("name")),score))
    output=[]
    for focus in targets[race["id"]]:
        matches=[n for n,score in ratings if n==ident(focus["name"])]
        peers=[score for n,score in ratings if n!=ident(focus["name"])]
        known=[v for v in peers if v is not None]
        enough=len(known)>=max(4,len(peers)//2)
        output.append({
            "leg":focus["leg"],"number":focus["number"],"name":focus["name"],
            "previousRaceId":race["id"],"cutoff":cutoff.isoformat(),
            "focusFound":bool(matches),
            "otherStarters":len(peers) if matches else None,
            "ratedOpponents":len(known) if matches else 0,
            "opponentRecentFormMean":round(sum(known)/len(known),4)
                if matches and enough and known else None,
            "coverageSufficient":bool(matches and enough),
        })
    return output


def requested_races(doc,max_races=MAX_RACES):
    """Prioritize at most two *distinct* past races per current V85 leg."""
    races={}
    for leg in doc["races"]:
        count=0
        for h in leg["horses"]:
            for past in h.get("lastFive",[])[:3]:
                rid=past.get("raceId")
                if not isinstance(rid,str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}_\d+_\d+",rid):
                    continue
                if rid not in races and count>=2:
                    continue
                if rid not in races and len(races)>=max_races:
                    break
                races.setdefault(rid,[]).append({"leg":leg["leg"],"number":h["number"],"name":h["name"]})
                if len(races[rid])==1:count+=1
                break
            if count>=2:break
    return races


def get_race(race_id):
    req=urllib.request.Request(BASE+race_id+"/extended",headers={
        "User-Agent":"LA-V85-opposition-pilot/1.0","Accept":"application/json"})
    with urllib.request.urlopen(req,timeout=25) as response:
        return json.load(response)


def main():
    source=json.loads(INPUT.read_text(encoding="utf8"))
    if source.get("gameId")!="V85_2026-10-31_78_5":
        raise ValueError("Wrong source event")
    planned=requested_races(source)
    if not planned:
        raise ValueError("No known prior race identifiers")
    entries=[];failures=[]
    for race_id in planned:
        try:
            data=get_race(race_id)
            entries+=opponent_context(data,planned)
        except (urllib.error.URLError,TimeoutError,ValueError,KeyError,TypeError) as e:
            failures.append({"raceId":race_id,"type":type(e).__name__,
                             "detail":str(e)[:100]})
        time.sleep(0.2)
    if len(entries)<6:
        raise ValueError("Insufficient past-race cards: refuse research output")
    valid=sum(x["coverageSufficient"] for x in entries)
    result={
        "schemaVersion":1,"sampledPreviousRaces":len(planned),
        "readableRaces":len(planned)-len(failures),
        "observedFocusStarts":len(entries),"sufficientCoverage":valid,
        "method":"Form of actual other runners as it stood before each sampled previous race, without post-race records. A bounded proof of concept only.",
        "noMarketOrResultLeakage":True,
        "limits":"Only a small deterministic sample of previous races; no verified lead positions, track condition or opponent-class correction. Not a predictor.",
        "source":"ATG racinginfo extended, unofficial",
        "failures":failures,
        "rows":entries,
    }
    old=json.loads(OUTPUT.read_text()) if OUTPUT.exists() else None
    if result==old:
        print("OPPONENT_PROBE unchanged");return
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    OUTPUT.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print("OPPONENT_PROBE",result["readableRaces"],"of",len(planned),
          "focus samples",len(entries),"sufficient",valid,flush=True)


if __name__=="__main__":
    try:main()
    except (ValueError,OSError,KeyError,TypeError) as e:
        print("OPPONENT PROBE NOT READY:",e,file=sys.stderr);sys.exit(1)
