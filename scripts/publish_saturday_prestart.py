#!/usr/bin/env python3
"""Build the immutable Saturday prestart observation and linked report."""
from __future__ import annotations

import gzip
import hashlib
import html
import json
import math
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUND = ROOT / "rounds/2026-11-28-solvalla"
BATCH_ID = "20261128T100612Z"
BATCH = ROOT / "research/comparison/2026-11-28" / BATCH_ID
FRIDAY = ROOT / "research/comparison/2026-11-28/20261127T190642Z"
NOW = datetime.now(timezone.utc).isoformat()

if (BATCH / "manifest.json").exists():
    raise SystemExit(f"Refusing to overwrite immutable prestart batch {BATCH_ID}")


def load(path: Path):
    return json.loads(path.read_text())


def dump(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


data = load(ROUND / "data.json")
form = load(ROUND / "form.json")
historical = load(ROUND / "model.json")
models = load(BATCH / "models.json")
friday_data = load(FRIDAY / "data.json")

snapshot = data["snapshotId"]
source_at = data["sourceAt"]
captured_at = data["retrievedAt"]
race_data = {r["leg"]: r for r in data["races"]}
form_data = {(r["leg"], h["number"]): h for r in form["races"] for h in r["horses"]}
model_data = {(r["leg"], h["number"]): h for r in models["races"] for h in r["horses"]}
friday_starts = {(r["leg"], s["number"]): s for r in friday_data["races"] for s in r["starts"]}


def active(leg):
    return [s for s in race_data[leg]["starts"] if not s["scratched"]]


def horse(leg, number):
    return next(s for s in race_data[leg]["starts"] if s["number"] == number)


def name(leg, number):
    return horse(leg, number)["name"]


market_races = []
reserve_order = []
for leg in range(1, 8):
    ordered = sorted(active(leg), key=lambda s: (-float(s.get("pct") or -1), s["number"]))
    market_races.append({
        "leg": leg,
        "raceId": race_data[leg]["raceId"],
        "top3": [{"number": s["number"], "name": s["name"], "pct": s["pct"]} for s in ordered[:3]],
        "strictOrderedTop3Eligible": len(ordered) >= 3 and ordered[2]["pct"] != ordered[3]["pct"],
    })
    reserve_order.append({"leg": leg, "numbers": [s["number"] for s in ordered], "basis": "ATG streckandel, fallande; startnummer bryter lika värde"})

market = {"capturedAt": captured_at, "sourceAt": source_at, "snapshotId": snapshot, "races": market_races}
dump(BATCH / "market.json", market)


def proxy_rank(leg, number, key):
    vals = []
    for s in active(leg):
        value = form_data[(leg, s["number"])].get("scores", {}).get(key)
        if isinstance(value, (int, float)):
            vals.append((s["number"], float(value)))
    value = dict(vals).get(number)
    if value is None:
        return None
    return {"rank": 1 + sum(v > value for _, v in vals), "covered": len(vals), "cutoff": math.ceil(len(vals) / 3), "value": value}


manual_horses = []
qualified = []
for leg in range(1, 8):
    field = len(active(leg))
    for s in active(leg):
        m = model_data[(leg, s["number"])]
        f = form_data[(leg, s["number"])]
        fr = proxy_rank(leg, s["number"], "form")
        cr = proxy_rank(leg, s["number"], "class")
        item = dict(s)
        item.update({
            "leg": leg,
            "historicalRank": m["historyScoreRank"],
            "expandedRank": m["expandedScoreRank"],
            "formProxy": fr,
            "classProxy": cr,
            "lastFive": f.get("lastFive", []),
            "coverage": f.get("coverage"),
            "equipment": m.get("equipment"),
        })
        manual_horses.append(item)
        proxies = []
        for proxy_name, proxy in (("form", fr), ("class", cr)):
            if proxy and proxy["covered"] >= math.ceil(field / 2) and proxy["rank"] <= proxy["cutoff"]:
                proxies.append({"type": proxy_name, **proxy})
        if float(s.get("pct") or 100) < 10 and 1 <= m["historyScoreRank"] <= 6 and proxies:
            qualified.append({
                "leg": leg, "number": s["number"], "name": s["name"], "pct": s["pct"],
                "historicalRank": m["historyScoreRank"], "expandedRank": m["expandedScoreRank"],
                "qualifyingProxies": proxies,
            })

qualified.sort(key=lambda x: (x["historicalRank"], x["pct"], x["leg"], x["number"]))
selected = []
used_legs = set()
for q in qualified:
    if q["leg"] not in used_legs and len(selected) < 3:
        selected.append(q)
        used_legs.add(q["leg"])

risk_text = {
    (2, 2): "Hola Que Tal och Capo har klart högre marknadsstöd; femstartersraden saknar seger och den utökade modellen rankar lägre.",
    (4, 5): "Voltstart över 2640 meter samt starkt marknadsstöd för Hankypanky Leonie; den utökade modellen rankar lägre.",
    (6, 4): "Barn Bank toppar båda modellerna och sprinttempot från spår 4 måste falla rätt.",
}
picks = []
for q in selected:
    proxy = q["qualifyingProxies"][0]
    reason = f"Historikrank {q['historicalRank']}, utökad rank {q['expandedRank']} och {q['pct']:.2f} procent. {proxy['type']}-proxy {proxy['rank']}/{proxy['covered']} klarar bästa tredjedelen."
    picks.append({**q, "type": "outsider", "sources": [data["sourceUrl"]], "reason": reason, "argument": reason, "risk": risk_text.get((q["leg"], q["number"]), "Favoriter och loppbild ger tydliga motrisker.")})

spikes = [
    {"leg": 1, "number": 5, "name": name(1, 5), "pct": horse(1, 5)["pct"], "historicalRank": 1, "expandedRank": 1,
     "sources": [data["sourceUrl"]], "reason": "Förstaval i båda modellerna i lördagens snapshot.", "challengers": [name(1,11), name(1,8)], "opponents": [{"number": 11, "name": name(1, 11)}, {"number": 8, "name": name(1, 8)}],
     "risk": "Hög streckandel och 47 dagars uppehåll; Iaintnoquitter har fyra segrar och en andraplats på fem starter."},
    {"leg": 6, "number": 7, "name": name(6, 7), "pct": horse(6, 7)["pct"], "historicalRank": 1, "expandedRank": 1,
     "sources": [data["sourceUrl"]], "reason": "Förstaval i båda modellerna i lördagens snapshot.", "challengers": [name(6,4), name(6,5)], "opponents": [{"number": 4, "name": name(6, 4)}, {"number": 5, "name": name(6, 5)}],
     "risk": "Spår 7 över 1640 meter och två galoppnoteringar i femstartersunderlaget; Osvaldo A.Boko och Romulus Diablo är motbud."},
]

A = [[5], [2, 3, 4, 5, 8], [2, 3, 6, 10], [1, 4, 5, 6, 11], [1, 5, 6, 7, 8], [7], [1, 4, 5]]
B = [[5, 11], [2, 3, 4, 5, 8], [2, 3, 6, 10], [1, 4, 5, 6, 11], [1, 5, 6, 7, 8], [5, 7], [1, 4, 5]]
BB = [[5, 11], [2, 3, 4, 5, 8], [2, 3, 10], [1, 4, 5, 6, 11], [1, 5, 6, 7, 8], [5, 7], [4]]


def system(label, selections, extra=0, removed=None):
    rows = math.prod(len(x) for x in selections)
    out = {"label": label, "selections": selections, "reserveOrder": reserve_order, "rows": rows, "costSEK": round(rows * .6, 2), "extraCostSEK": extra}
    if removed:
        out["removedToFit"] = removed
    return out


analysis = {
    "schemaVersion": 1, "version": "2026-11-28-saturday-final", "roundId": data["roundId"], "gameId": data["gameId"],
    "snapshotId": snapshot, "sourceAt": source_at, "reviewedAt": NOW, "status": "SATURDAY_FINAL_PRESTART",
    "picks": picks, "spikeCandidates": spikes, "qualifiedOutsiders": qualified,
    "outsiderRuleSource": "efteranalys/2026-11-21/lessons.json#followUp",
    "theoreticalSystems": {
        "rowPriceSEK": .6, "stakeFraction": 1.0, "budgetExampleSEK": 900,
        "budgetSource": "Senaste uttryckligen bekräftade kupongens insats, Jägersro 2026-11-21; endast räkneexempel.",
        "A": system("Två arbetsspikar", A),
        "BUncut": system("Motbuden tillagda, övriga streck kvar", B, 2700),
        "BWithinBudget": system("Motbuden tillagda inom A:s budget", BB, 0, [{"leg": 3, "numbers": [6]}, {"leg": 7, "numbers": [1, 5]}]),
    },
    "limitations": ["Modellpoäng är inte kalibrerade vinstchanser.", "Den utökade modellen är experimentell och använder marknad och anmäld utrustning.", "Vinnarodds, streck och omsättning kan ändras efter snapshoten."]
}
dump(BATCH / "analysis.json", analysis)
dump(ROUND / "analysis.json", analysis)
dump(BATCH / "manual-review.json", {"snapshotId": snapshot, "reviewedAt": NOW, "activeHorsesReviewed": len(manual_horses), "horses": manual_horses})

external = {
    "schemaVersion": 1, "roundId": data["roundId"], "gameId": data["gameId"], "capturedAt": NOW,
    "sources": [
        {"name": "Travia omgångsanalys", "url": "https://travia.se/v75/solvalla-2026-11-28", "publicationTimeText": "Uppdaterad 10:56 den 28 november", "status": "public_partial_unordered", "spike": {"leg": 5, "number": 5, "name": "Tangelo Lane"}, "outsider": {"leg": 4, "number": 14, "name": "Lotusorchide"}, "overplayed": {"leg": 2, "number": 3, "name": "Hola Que Tal"}, "strictOrderedTop3": False},
        {"name": "Tipper Trav", "url": "https://tippertrav.se/", "status": "public_numeric_index_partial", "warning": "Sidan visade lägre omsättning och äldre streck än ATG-snapshoten; endast publicerade index fryses.", "races": [
            {"leg": 1, "top3": [5,11,6], "indices": [81,33,29]}, {"leg": 2, "top3": [4,3,8], "indices": [71,67,40]}, {"leg": 3, "firstChoice": 3, "top3": None, "reason": "Delad tredjeplats 35."}, {"leg": 4, "top3": [4,11,6], "indices": [71,63,43]}, {"leg": 5, "top3": [5,6,8], "indices": [70,39,34]}, {"leg": 6, "top3": [7,4,2], "indices": [81,30,29]}, {"leg": 7, "firstChoice": None, "top3": None, "reason": "Delad förstaplats 71."}]},
        {"name": "Travtips AI", "url": "https://travtips.ai/sv/tips/v75", "publicationTimeText": "Kontrollerad 27 november", "status": "public_first_choices_only", "firstChoices": [{"leg":1,"number":5},{"leg":2,"number":3},{"leg":3,"number":3},{"leg":4,"number":11},{"leg":5,"number":5},{"leg":6,"number":7},{"leg":7,"number":1}], "strictOrderedTop3": False},
    ] + [{"name": n, "status": "current_prediction_not_captured"} for n in ["Travmaskinen", "V46", "Travia AI", "Travtipsaren", "ATG Elli", "Simsalabim Heat Rank"]]
}
dump(BATCH / "external-sources.json", external)

changes = []
for leg in range(1, 8):
    for s in active(leg):
        before = friday_starts.get((leg, s["number"]))
        if before and abs((s.get("pct") or 0) - (before.get("pct") or 0)) >= 1:
            changes.append({"leg": leg, "number": s["number"], "name": s["name"], "type": "market_pct", "before": before.get("pct"), "after": s.get("pct")})
verification = {"verifiedAt": NOW, "sourceAt": source_at, "retrievedAt": captured_at, "gameId": data["gameId"], "snapshotId": snapshot, "date": data["date"], "track": data["track"], "raceIds": [r["raceId"] for r in data["races"]], "active": len(manual_horses), "scratched": sum(s["scratched"] for r in data["races"] for s in r["starts"]), "deadline": data["startTime"], "turnoverSEK": data["turnoverSEK"], "changesSinceFriday": sorted(changes, key=lambda x: -abs(x["after"]-x["before"])), "newScratchesSinceFriday": []}
dump(BATCH / "verification.json", verification)

versions = {"capturedAt": NOW, "software": historical["software"], "parameters": historical["parameters"], "training": historical["training"], "codeCommitAtRunStart": "f011374b28bfd635fc8c3683d48e37e226f470e1", "modelScripts": ["scripts/rank_current_catboost.py", "scripts/compare_current_models.py"], "validationScope": "V85_ONLY; V75 application prospective"}
dump(BATCH / "versions.json", versions)
for src, dest in ((ROUND/"data.json", BATCH/"published-data.json"), (ROUND/"form.json", BATCH/"form.json"), (ROUND/"model.json", BATCH/"model.json")):
    shutil.copy2(src, dest)
for p in (BATCH/"raw").glob("*.json"):
    with p.open("rb") as fin, gzip.open(str(p)+".gz", "wb") as fout:
        shutil.copyfileobj(fin, fout)
    p.unlink()

dump(ROOT / "research/comparison/2026-11-28/prestart-index.json", {
    "schemaVersion": 1, "roundId": data["roundId"], "gameId": data["gameId"], "bettingDeadline": data["startTime"],
    "primaryBatch": BATCH_ID, "selectedAt": NOW, "snapshotId": snapshot, "observedAt": models["observedAt"], "sourceAt": source_at,
    "status": "SATURDAY_FINAL_PRESTART", "captureWindow": {"startedAt": models["runStartedAt"], "finishedAt": NOW},
    "files": {k: f"{BATCH_ID}/{v}" for k,v in {"manifest":"manifest.json","analysis":"analysis.json","manualReview":"manual-review.json","market":"market.json","models":"models.json","externalSources":"external-sources.json","verification":"verification.json","versions":"versions.json"}.items()},
    "note": "Primär lördagsfrysning före verifierat spelstopp. Tidigare batcher bevaras oförändrade."
})


def model_names(leg, kind):
    nums = next(r["top3"][kind] for r in models["races"] if r["leg"] == leg)
    return ", ".join(f"{n} {name(leg,n)}" for n in nums)


def system_text(sel):
    return " / ".join(",".join(map(str, x)) for x in sel)


def esc(x): return html.escape(str(x))

rows = []
reviews = []
for leg in range(1, 8):
    mt = market_races[leg-1]["top3"]
    market_text = ", ".join("{} {} ({:.2f} %)".format(x["number"], x["name"], x["pct"]) for x in mt)
    rows.append(f"<tr><td>{leg}</td><td>{esc(model_names(leg,'historyScore'))}</td><td>{esc(model_names(leg,'expandedScore'))}</td><td>{esc(market_text)}</td></tr>")
    leaders = []
    for x in mt:
        m = model_data[(leg,x["number"])]
        last = [str(v.get("place")) for v in form_data[(leg,x["number"])].get("lastFive",[])][:5]
        leaders.append(f"{x['number']} {x['name']} (historik {m['historyScoreRank']}, utökad {m['expandedScoreRank']}, senaste {'–'.join(last)})")
    leaders_text = ", ".join("{} {}".format(x["number"], x["name"]) for x in mt)
    reviews.append(f"<article><h3>V75-{leg} — {race_data[leg]['distance']} meter, {race_data[leg]['startMethod']}</h3><p>Marknad: {esc(leaders_text)}. Historikmodellens etta: {esc(model_names(leg,'historyScore').split(', ')[0])}.</p><p>{esc('; '.join(leaders))}.</p><p>{'Voltstart med startmoment och trafik.' if race_data[leg]['startMethod']=='volte' else 'Autostart med positionsrisk; faktisk spetschans är inte verifierad.'}</p></article>")

outsider_html = "".join(f"<article><h3>V75-{p['leg']} #{p['number']} {esc(p['name'])} — {p['pct']:.2f} %</h3><p>{esc(p['argument'])}</p><p><strong>Risk:</strong> {esc(p['risk'])}</p></article>" for p in picks)
spike_html = "".join(f"<article><h3>V75-{s['leg']} #{s['number']} {esc(s['name'])} — {s['pct']:.2f} %</h3><p>Etta i båda modellerna. Motbud: {esc(', '.join(str(o['number']) + ' ' + o['name'] for o in s['opponents']))}.</p><p><strong>Risk:</strong> {esc(s['risk'])}</p></article>" for s in spikes)
reserve_html = "".join(f"<li>V75-{x['leg']}: {', '.join(map(str,x['numbers']))}</li>" for x in reserve_order)
changes_html = "".join(f"<li>V75-{x['leg']} {x['name']}: {x['before']:.2f} → {x['after']:.2f} %</li>" for x in verification["changesSinceFriday"][:12]) or "<li>Inga streckförändringar över en procentenhet.</li>"

report = f'''<!doctype html><html lang="sv"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Solvalla 28 november – slutlig lördagsuppdatering | V75travet.se</title><link rel="stylesheet" href="../../site-shell.css"><link rel="stylesheet" href="../../v75-brand.css"><style>body{{font-family:system-ui;line-height:1.6}}main{{max-width:1100px;margin:auto;padding:24px}}.scroll{{overflow:auto}}table{{width:100%;border-collapse:collapse}}td,th{{border:1px solid #ccd5df;padding:10px;vertical-align:top;text-align:left}}article{{border:1px solid #ccd5df;padding:16px;margin:16px 0}}a{{overflow-wrap:anywhere}}</style></head><body><main><p><a href="../../">V75travet.se</a></p><h1>Solvalla 28 november – slutlig lördagsuppdatering</h1><p>V75 Solvalla 28 november 2026. Spelstopp 15.00 svensk tid. ATG-källtid {source_at}, hämtad {captured_at}. 79 aktiva av 85 anmälda, sex strukna. Omsättning {data['turnoverSEK']:,.0f} kr.</p><p>Slutlig förhandsfrysning före start. Streck, odds och omsättning kan ändras efter snapshoten. Modellpoäng är inte kalibrerade vinstchanser.</p><h2>Förändringar sedan fredag</h2><ul>{changes_html}</ul><p>Omsättningen ökade från {friday_data['turnoverSEK']:,.0f} till {data['turnoverSEK']:,.0f} kr. Inga nya strykningar registrerades.</p><h2>Prioriterade skrällar</h2>{outsider_html}<p>Urval: högst tre totalt, högst en per lopp, under 10 %, historikrank 1–6 och bästa tredjedelen i form eller klass med minst halva fältet täckt.</p><h2>Arbetsspikar</h2>{spike_html}<p>Arbetsspik betyder systemval, inte en kalibrerad vinstchans över 50 procent.</p><h2>Modeller och marknadsbaslinje</h2><div class="scroll"><table><tr><th>Avd</th><th>Historisk CatBoost</th><th>Experimentell utökad CatBoost</th><th>ATG-marknad topp 3</th></tr>{''.join(rows)}</table></div><p>Historikmodellen använder historiska form-, klass- och spårvariabler. Den utökade modellen använder dessutom marknad och anmäld utrustning. Publicerade testmått gäller V85; V75-tillämpningen är prospektiv.</p><h2>Fullständiga teoretiska system</h2><p>Räkneexempel med radpris 0,60 kr, insatsandel 100 % och budget 900 kr. Inga spel är lagda.</p><div class="scroll"><table><tr><th>Alternativ</th><th>Val avdelning 1–7</th><th>Rader</th><th>Kostnad</th></tr><tr><td>A</td><td>{system_text(A)}</td><td>1 500</td><td>900 kr</td></tr><tr><td>B, oskuret</td><td>{system_text(B)}</td><td>6 000</td><td>3 600 kr</td></tr><tr><td>B inom budget</td><td>{system_text(BB)}</td><td>1 500</td><td>900 kr</td></tr></table></div><p>Oskuret B kostar 2 700 kr mer. B inom budget tar bort V75-3 #6 samt V75-7 #1 och #5.</p><h3>Reservordning för samtliga system</h3><ol>{reserve_html}</ol><p>Reservordningen är låst till ATG:s streckandel i snapshoten, fallande; startnummer bryter lika värde.</p><h2>Granskning lopp för lopp</h2>{''.join(reviews)}<h2>Externa prognoser</h2><p>Travia publicerade #5 Tangelo Lane som spik, #14 Lotusorchide som outsider och #3 Hola Que Tal som överspelad; deras A/B/C-grupper behandlas som oordnade. Tipper-indexets delningar i V75-3 och V75-7 omvandlas inte till strikt topp tre. Travtips AI:s offentliga förstaval är frysta utan påhittad topp tre. Övriga listade källor saknade fångad aktuell prognos.</p><p><a href="../../research/comparison/2026-11-28/{BATCH_ID}/manual-review.json">Granskning av 79 aktiva</a> · <a href="../../research/comparison/2026-11-28/{BATCH_ID}/models.json">Frysta modeller</a> · <a href="../../research/comparison/2026-11-28/{BATCH_ID}/external-sources.json">Externa observationer</a> · <a href="../../research/comparison/2026-11-28/prestart-index.json">Primärt prestart-index</a> · <a href="../2026-11-27/">Fredagens bevarade rapport</a></p></main></body></html>'''
(ROOT / "uppdateringar/2026-11-28").mkdir(parents=True, exist_ok=True)
(ROOT / "uppdateringar/2026-11-28/index.html").write_text(report)

rounds = load(ROOT / "rounds.json")
rounds["rounds"][0]["overview"] = "uppdateringar/2026-11-28/"
dump(ROOT / "rounds.json", rounds)

# Manifest is written last and excludes itself.
files = {}
for path in sorted(BATCH.rglob("*")):
    if path.is_file() and path.name != "manifest.json":
        files[str(path.relative_to(BATCH))] = {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "bytes": path.stat().st_size}
dump(BATCH / "manifest.json", {"schemaVersion": 1, "batchId": BATCH_ID, "roundId": data["roundId"], "gameId": data["gameId"], "snapshotId": snapshot, "capturedAt": NOW, "immutable": True, "files": files})
print(json.dumps({"batch": BATCH_ID, "snapshotId": snapshot, "picks": [(p['leg'],p['number']) for p in picks], "qualified": len(qualified)}, ensure_ascii=False))
