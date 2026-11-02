#!/usr/bin/env python3
"""Train CatBoost on complete historical fields and rank the verified current round."""
import concurrent.futures
import datetime as dt
import hashlib
import json
import pathlib
import sys
import urllib.request
import numpy as np
import catboost
from catboost import CatBoostClassifier
from scripts.data_quality import load_training_data
from scripts.historical_pilot import features_from_history
from scripts.train_historical_pilot import FEATURES, evaluate
from scripts.walkforward_evaluation import enriched_matrix, clean_paired, RELATIVE_FEATURES, MIN_TRAIN_DATES, MIN_TRAIN_STARTERS

ROOT = pathlib.Path(__file__).resolve().parents[1]
def estimator():
    return CatBoostClassifier(iterations=220, depth=5, learning_rate=.045,
        loss_function='Logloss', l2_leaf_reg=6, random_seed=214,
        verbose=False, allow_writing_files=False, thread_count=2)

def matrix(rows):
    # Keep the fixed baseline feature policy during history expansion.
    # Explicit historical gallop flags remain sparse; disable in inference too.
    clean = [{**r, 'prestartFeatures': {**r['prestartFeatures'], 'gallop5': None}} for r in rows]
    return enriched_matrix(clean)

def backtest(rows):
    dates = sorted({r['date'] for r in rows})
    groups, folds = {}, []
    for date in dates[MIN_TRAIN_DATES:]:
        train = [r for r in rows if r['date'] < date]
        test = [r for r in rows if r['date'] == date]
        if len(train) < MIN_TRAIN_STARTERS: continue
        model = estimator()
        model.fit(matrix(train), np.array([r['winner'] for r in train]))
        pred = model.predict_proba(matrix(test))[:, 1]
        fold = {}
        for row, score in zip(test, pred):
            fold.setdefault(row['raceId'], []).append({**row, 'score': float(score)})
        groups.update(fold)
        folds.append({'date': date, 'trainUntil': max(r['date'] for r in train),
                      'trainStarts': len(train), 'metrics': evaluate(fold, 'score')})
    metrics = evaluate(groups, 'score')
    if len(folds) < 2 or metrics['races'] < 12:
        raise ValueError('Insufficient independent chronological test races')
    paired = clean_paired(groups)
    return {'folds': folds, 'metrics': metrics,
            'pairedModel': evaluate(paired, 'score'),
            'retrospectiveFinalPool': evaluate(paired, 'marketFinalPct', market=True),
            'marketCaveat': 'Final pool, not an independently archived prestart observation.',
            'racePredictions': [{'raceId': rid, 'date': items[0]['date'],
                                 'top3': [r['number'] for r in sorted(items, key=lambda r: (-r['score'], r['number']))[:3]],
                                 'winner': next(r['number'] for r in items if r['winner'])}
                                for rid, items in sorted(groups.items())]}

def current_rows(data):
    day = dt.date.fromisoformat(data['date'])
    def collect(race):
        url = 'https://www.atg.se/services/racinginfo/v1/api/races/' + race['raceId'] + '/extended'
        req = urllib.request.Request(url, headers={'User-Agent': 'LA_V85/research-1.0', 'Accept': 'application/json'})
        with urllib.request.urlopen(req, timeout=35) as response: raw = json.load(response)
        if raw.get('id') != race['raceId']: raise ValueError('Race identity mismatch')
        expected = {h['number']: h for h in race['starts'] if not h['scratched']}
        active = [h for h in raw['starts'] if not h.get('scratched')]
        if set(expected) != {h['number'] for h in active}: raise ValueError('Field changed: refresh startlist first')
        result = []
        for h in active:
            saved = expected[h['number']]
            if h['horse']['name'] != saved['name']: raise ValueError('Horse identity mismatch')
            if h.get('postPosition') != saved['postPosition'] or (h.get('distance') or raw['distance']) != saved['distance']:
                raise ValueError('Post or distance changed')
            f = features_from_history(h, raw, day, len(active))
            result.append({'raceId': race['raceId'], 'leg': race['leg'], 'number': h['number'],
                           'name': saved['name'], 'prestartFeatures': f})
        return result, {'raceId': race['raceId'], 'sourceUrl': url,
                        'sha256': hashlib.sha256(json.dumps(raw, sort_keys=True).encode()).hexdigest()}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        collected = list(pool.map(collect, data['races']))
    return [r for rows, source in collected for r in rows], [s for rows, s in collected]

def main():
    config = json.loads((ROOT/'rounds.json').read_text(encoding='utf-8'))
    info = next(r for r in config['rounds'] if r['id'] == config['current'])
    data = json.loads((ROOT/info['data']).read_text(encoding='utf-8'))
    now = dt.datetime.now(dt.timezone.utc)
    if data['status'] != 'verified' or now >= dt.datetime.fromisoformat(data['startTime']):
        raise ValueError('Verified prestart round required')
    doc = load_training_data()
    cutoff = min(data['date'], now.date().isoformat())
    rows = [r for r in doc['rows'] if r['date'] < cutoff]
    if len(rows) < 200 or len({r['date'] for r in rows}) < 6: raise ValueError('Insufficient history')
    validation = backtest(rows)
    current, sources = current_rows(data)
    model = estimator()
    model.fit(matrix(rows), np.array([r['winner'] for r in rows]))
    pred = model.predict_proba(matrix(current))[:, 1]
    ranked = []
    for race in data['races']:
        items = [{**r, 'modelScore': round(float(p), 8)} for r, p in zip(current, pred) if r['leg'] == race['leg']]
        items.sort(key=lambda r: (-r['modelScore'], r['number']))
        for rank, item in enumerate(items, 1): item['rank'] = rank
        ranked.append({'leg': race['leg'], 'raceId': race['raceId'], 'horses': items,
                       'top3': [{'number': h['number'], 'name': h['name'], 'rank': h['rank']} for h in items[:3]]})
    report = {'schemaVersion': 1, 'kind': 'CATBOOST_PRESTART_RANKING', 'roundId': data['roundId'],
        'gameId': data['gameId'], 'snapshotId': data['snapshotId'], 'generatedAt': now.isoformat(),
        'model': 'CatBoostClassifier', 'parameters': estimator().get_params(),
        'software': {'catboost': catboost.__version__, 'numpy': np.__version__, 'python': sys.version.split()[0]},
        'training': {'starts': len(rows), 'races': len({r['raceId'] for r in rows}),
                     'dates': len({r['date'] for r in rows}), 'from': min(r['date'] for r in rows),
                     'until': max(r['date'] for r in rows), 'source': doc['dataQuality']['sourceFile'],
                     'sha256': doc['dataQuality']['sourceSha256'], 'excludedRaces': doc['dataQuality']['excludedRaces']},
        'features': [*FEATURES, *RELATIVE_FEATURES], 'validation': validation, 'sources': sources,
        'limitations': 'Experimentell ranking från utvalda kompletta historiska lopp. Modellpoäng är inte kalibrerad vinstchans. Odds, streck, aktuellt resultat, hästnamn, kusk, tränare och karriärstatistik ingår inte som modellvariabler. Galoppvariabeln är avstängd för jämförbarhet med grundförsöket. Testet är retrospektivt och visar inte lönsamhet.',
        'races': ranked}
    output = ROOT/'rounds'/data['roundId']/'model.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'training': report['training'], 'validation': validation['metrics'],
                      'top3': [{'leg': r['leg'], 'horses': r['top3']} for r in ranked]}, ensure_ascii=False), flush=True)
if __name__ == '__main__': main()
