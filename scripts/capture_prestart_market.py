#!/usr/bin/env python3
"""Capture immutable, timestamped *before-the-off* V85 market snapshots.

Research archive only; no live tips, no change to current Bjerke JSON.
ATG Racinginfo is an unofficial/unstable site endpoint; reject bad data.
"""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import pathlib
import sys
import urllib.request
from zoneinfo import ZoneInfo

BASE=pathlib.Path(__file__).resolve().parents[1]
ID="V85_2026-10-31_78_5"
DAY="2026-10-31"
LOCAL=ZoneInfo("Europe/Stockholm")
CUTOFF=dt.datetime(2026,10,31,15,0,tzinfo=LOCAL)
URL="https://www.atg.se/services/racinginfo/v1/api/games/"+ID
DEST=BASE/"research"/"prestart"/DAY


def checked_snapshot(game, now):
    """Pure validation; time-sensitive and strict about race/market data."""
    if now.tzinfo is None:
        raise ValueError("Observations must be timezone-aware")
    local_now=now.astimezone(LOCAL)
    if local_now>=CUTOFF:
        raise ValueError("Race has started: refuse prestart snapshot")
    if game.get("id")!=ID or not isinstance(game.get("races"),list) or len(game["races"])!=8:
        raise ValueError("Unexpected game or wrong V85 field")
    pool=(game.get("pools") or {}).get("V85") or {}
    source_time=pool.get("timestamp")
    if not isinstance(source_time,str):
        raise ValueError("ATG V85 source timestamp missing")
    try:
        parsed=dt.datetime.fromisoformat(source_time.replace(" ","T"))
        parsed=parsed.replace(tzinfo=LOCAL) if parsed.tzinfo is None else parsed.astimezone(LOCAL)
    except ValueError as ex:
        raise ValueError("Invalid ATG source timestamp") from ex
    if parsed>local_now+dt.timedelta(minutes=5) or parsed.date()!=local_now.date() and (local_now-parsed)>dt.timedelta(days=8):
        raise ValueError("Future or unexpectedly old ATG source time")
    if parsed>=CUTOFF:
        raise ValueError("Source timestamp not before start")
    entries=[]
    for leg,r in enumerate(game["races"],1):
        if not isinstance(r,dict) or r.get("status")=="results":
            raise ValueError("Already finished race")
        starts=r.get("starts")
        if not isinstance(starts,list) or len(starts)<6:
            raise ValueError(f"Invalid starters in leg {leg}")
        packed=[]
        for h in starts:
            if not isinstance(h,dict):
                raise ValueError("Invalid starter record")
            horse=h.get("horse") or {}
            n=h.get("number")
            distribution=((h.get("pools") or {}).get("V85") or {}).get("betDistribution")
            pct=distribution/100 if type(distribution) in (int,float) else None
            if type(n) is not int or not isinstance(horse.get("name"),str):
                raise ValueError("Bad number or horse in market")
            if pct is None or not 0<=pct<=100:
                raise ValueError(f"Missing/invalid market percent: leg {leg}, horse {n}")
            packed.append({"number":n,"horse":horse["name"],"pct":round(pct,2),
                           "scratched":bool(h.get("scratched") or (h.get("result") or {}).get("scratched"))})
        active=[x for x in packed if not x["scratched"]]
        if len({x["number"] for x in packed})!=len(packed) or not 95<=sum(x["pct"] for x in active)<=105:
            raise ValueError(f"Market percent totals invalid in leg {leg}")
        entries.append({"leg":leg,"raceId":r.get("id"),"raceNumber":r.get("number"),
                        "starts":packed})
    return {
        "schemaVersion":1,"gameId":ID,"raceDate":DAY,"source":URL,
        "sourceAt":parsed.isoformat(),"observedAt":local_now.isoformat(),
        "lagSeconds":round((local_now-parsed).total_seconds()),
        "snapshotKind":"OBSERVED_PRESTART_NOT_FINAL_POOL",
        "note":"ATG V85 betDistribution from live API before scheduled start; not a predicted win probability.",
        "races":entries,
    }


def candidate_path(doc):
    # observedAt is deliberately excluded from digest: repeated observations
    # of identical market data are ONE snapshot, not extra commits.
    relevant={"gameId":doc["gameId"],"sourceAt":doc["sourceAt"],"races":doc["races"]}
    digest=hashlib.sha256(json.dumps(relevant,sort_keys=True,ensure_ascii=False,separators=(",",":")).encode()).hexdigest()[:12]
    source=dt.datetime.fromisoformat(doc["sourceAt"]).strftime("%Y%m%dT%H%M%S")
    return DEST/(f"{source}_{digest}.json")


def main():
    now=dt.datetime.now(dt.timezone.utc)
    if now.astimezone(LOCAL)>=CUTOFF:
        print("Outside prestart window, no archive created.")
        return 0
    req=urllib.request.Request(URL,headers={"Accept":"application/json",
                                            "User-Agent":"LA_V85-research-prestart/1.0"})
    with urllib.request.urlopen(req,timeout=30) as response:
        game=json.load(response)
    doc=checked_snapshot(game,now)
    target=candidate_path(doc)
    if target.exists():
        print("Unchanged source and market: no duplicate snapshot",target)
        return 0
    DEST.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(doc,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Archived observed-before-start market",target,
          "source lag seconds:",doc["lagSeconds"])
    return 0


if __name__=="__main__":
    try:
        sys.exit(main())
    except (ValueError,TypeError,OSError,KeyError) as exc:
        print("PRESTART ARCHIVE ERROR:",exc,file=sys.stderr)
        sys.exit(1)
