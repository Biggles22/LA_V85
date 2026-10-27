#!/usr/bin/env python3
"""Score immutable Bjerke research forecasts only AFTER independently verified results.

Does not retrain models or change their prestart predictions.
Requires eight complete race cards with exactly one declared winner each.
"""
from __future__ import annotations
import datetime as dt
import json
import pathlib
import sys
from zoneinfo import ZoneInfo

try:
    from scripts.freeze_v85_forecasts import DEST,ID,BASE,DATE,get_json,TZ
except ModuleNotFoundError:
    from freeze_v85_forecasts import DEST,ID,BASE,DATE,get_json,TZ

AFTER=dt.datetime(2026,11,1,0,0,tzinfo=TZ)
OUT=DEST/"evaluation.json"
SLOTS=("preview","friday","saturday")


def to_place(v):
    if type(v) is int and 1<=v<=30:return v
    if isinstance(v,str) and v.isdigit() and 1<=int(v)<=30:return int(v)
    return None


def verified_results(game,extra):
    if game.get("id")!=ID or len(game.get("races",[]))!=8:
        raise ValueError("Wrong 8-race game")
    winners={}
    for leg,r in enumerate(game["races"],1):
        rid=r.get("id")
        extended=extra.get(rid)
        if not isinstance(extended,dict) or extended.get("id")!=rid or extended.get("status")!="results":
            raise ValueError("Incomplete official results for leg "+str(leg))
        runners=extended.get("starts")
        if not isinstance(runners,list) or len(runners)<6:
            raise ValueError("Incomplete result card")
        completed=[]
        for s in runners:
            if not isinstance(s,dict):continue
            h=s.get("horse") if isinstance(s.get("horse"),dict) else {}
            res=s.get("result") if isinstance(s.get("result"),dict) else {}
            if s.get("scratched") is True or res.get("scratched") is True:
                continue
            p=to_place(res.get("place"))
            if p is not None and type(s.get("number")) is int and isinstance(h.get("name"),str):
                completed.append((s["number"],h["name"],p))
        if len(completed)<max(6,int(len(runners)*.75)):
            raise ValueError("Too many missing placings in leg "+str(leg))
        winner=[x for x in completed if x[2]==1]
        if len(winner)!=1:
            raise ValueError("Winner not uniquely verified for leg "+str(leg))
        winners[leg]={"raceId":rid,"number":winner[0][0],"horse":winner[0][1],
                      "recordedPlacings":len(completed)}
    return winners


def score_frozen(frozen,results):
    if frozen.get("gameId")!=ID or frozen.get("kind")!="FROZEN_PROSPECTIVE_RESEARCH_NOT_BETTING_ADVICE":
        raise ValueError("Unrecognized immutable forecast")
    if len(frozen.get("races",[]))!=8:
        raise ValueError("Forecast missing one or more legs")
    when=dt.datetime.fromisoformat(frozen["frozenAt"])
    if when>=dt.datetime(2026,10,31,15,0,tzinfo=TZ) or when.date()>DATE:
        raise ValueError("Forecast timestamp AFTER race start")
    model_keys={"base":"baseTop3","opponents":"opponentTop3","atg":"marketTop3"}
    totals={k:{"top1":0,"top3":0} for k in model_keys}
    byleg=[]
    for r in frozen["races"]:
        leg=r["leg"]
        result=results.get(leg)
        if result is None or r.get("raceId")!=result["raceId"]:
            raise ValueError("Race ID changed between forecast and results")
        actual=result["number"]
        horses=[x for x in r["runners"] if x["number"]==actual]
        if len(horses)!=1 or horses[0]["horse"]!=result["horse"]:
            raise ValueError("Winner not in identical forecast field")
        detail={"leg":leg,"winnerNumber":actual,"winner":result["horse"]}
        for key,field in model_keys.items():
            predicted=r[field]
            if len(predicted)!=3 or len(set(predicted))!=3:
                raise ValueError("Invalid top-three forecast")
            first=actual==predicted[0]
            three=actual in predicted
            totals[key]["top1"]+=int(first)
            totals[key]["top3"]+=int(three)
            detail[key]={"top1":first,"top3":three,"predicted":predicted}
        byleg.append(detail)
    if len({x["leg"] for x in byleg})!=8:
        raise ValueError("Duplicate/missing leg")
    return {"slot":frozen["slot"],"frozenAt":frozen["frozenAt"],
            "marketSourceAt":frozen["marketSourceAt"],"races":8,
            "metrics":totals,"byLeg":byleg}


def evaluate(now=None):
    now=now or dt.datetime.now(dt.timezone.utc)
    if now.astimezone(TZ)<AFTER:
        raise ValueError("Post-race results may not be checked before November 1")
    slots={}
    for name in SLOTS:
        file=DEST/(name+".json")
        if file.exists():
            slots[name]=json.loads(file.read_text(encoding="utf8"))
    if not slots:
        raise ValueError("No original frozen predictions to evaluate")
    game=get_json(BASE+"/games/"+ID)
    extra={r["id"]:get_json(BASE+"/races/"+r["id"]+"/extended")
           for r in game.get("races",[])}
    winners=verified_results(game,extra)
    comparisons={name:score_frozen(doc,winners) for name,doc in slots.items()}
    return {
        "schemaVersion":1,"type":"HISTORICAL_RESULTS_FOR_IMMUTABLE_PRESTART_FORECASTS",
        "gameId":ID,"date":DATE.isoformat(),
        "scoredAfter":now.astimezone(TZ).isoformat(),
        "resultsSource":"ATG racinginfo extended result cards (unofficial API)",
        "winners":[{"leg":leg,**info} for leg,info in sorted(winners.items())],
        "slotComparisons":comparisons,
        "missingSlots":[x for x in SLOTS if x not in comparisons],
        "warning":"Small prospective sample. Normalized model scores are NOT validated winning probabilities. ATG comparator is a frozen snapshot, not a retrospective final pool. No profit claim.",
    }


def main():
    now=dt.datetime.now(dt.timezone.utc)
    if now.astimezone(TZ)<AFTER:
        print("Too early for postrace comparison.")
        return 0
    if OUT.exists():
        print("Immutable outcome report already saved; no overwrite.")
        return 0
    result=evaluate(now)
    DEST.mkdir(parents=True,exist_ok=True)
    with OUT.open("x",encoding="utf8") as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2)
        stream.write("\n")
    for slot,v in result["slotComparisons"].items():
        print("RESULTS",slot,v["metrics"],flush=True)
    return 0


if __name__=="__main__":
    try:sys.exit(main())
    except (OSError,ValueError,TypeError,KeyError) as ex:
        print("RESULT EVALUATION BLOCKED:",str(ex),file=sys.stderr)
        sys.exit(1)
