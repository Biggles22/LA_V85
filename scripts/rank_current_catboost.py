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
from scripts.historical_validation import game_type, v85_folds, later_v85_split

ROOT = pathlib.Path(__file__).resolve().parents[1]
XGB_PARAMETERS = dict(n_estimators=120, max_depth=3, learning_rate=.055,
    subsample=.85, colsample_bytree=.85, reg_lambda=5, objective='binary:logistic',
    eval_metric='logloss', tree_method='hist', random_state=214, n_jobs=2)
def estimator():
    return CatBoostClassifier(iterations=220, depth=5, learning_rate=.045,
        loss_function='Logloss', l2_leaf_reg=6, random_seed=214,
        verbose=False, allow_writing_files=False, thread_count=2)

def matrix(rows):
    # Keep the fixed baseline feature policy during history expansion.
    # Explicit historical gallop flags remain sparse; disable in inference too.
    clean = [{**r, 'prestartFeatures': {**r['prestartFeatures'], 'gallop5': None}} for r in rows]
    return enriched_matrix(clean)

def xgb_estimator():
    from xgboost import XGBClassifier
    return XGBClassifier(**XGB_PARAMETERS)


def backtest(rows, compare_xgboost=False):
    groups, folds = {}, []
    for date, train, test in v85_folds(rows, MIN_TRAIN_DATES, MIN_TRAIN_STARTERS):
        train_x, test_x = matrix(train), matrix(test)
        labels = np.array([r['winner'] for r in train])
        model = estimator()
        model.fit(train_x, labels)
        pred = model.predict_proba(test_x)[:, 1]
        xgb_pred = [None] * len(test)
        if compare_xgboost:
            xgb = xgb_estimator()
            xgb.fit(train_x, labels)
            xgb_pred = xgb.predict_proba(test_x)[:, 1]
        fold = {}
        for row, score, xgb_score in zip(test, pred, xgb_pred):
            fold.setdefault(row['raceId'], []).append({**row, 'score': float(score),
                                                       'xgboostScore': float(xgb_score) if xgb_score is not None else None})
        groups.update(fold)
        folds.append({'date': date, 'trainUntil': max(r['date'] for r in train),
                      'trainStarts': len(train), 'trainV75Starts': sum(game_type(r) == 'V75' for r in train),
                      'metrics': evaluate(fold, 'score')})
        print('V85_FOLD', date, len(train), 'training starts', len(fold), 'test races', flush=True)
    metrics = evaluate(groups, 'score')
    if len(folds) < 2 or metrics['races'] < 12:
        raise ValueError('Insufficient independent chronological test races')
    paired = clean_paired(groups)
    return {'scope': 'V85_ONLY', 'folds': folds, 'metrics': metrics,
            'pairedModel': evaluate(paired, 'score'),
            'pairedXGBoost': evaluate(paired, 'xgboostScore') if compare_xgboost else None,
            'xgboostParameters': XGB_PARAMETERS if compare_xgboost else None,
            'retrospectiveFinalPool': evaluate(paired, 'marketFinalPct', market=True),
            'marketCaveat': 'Final pool, not an independently archived prestart observation.',
            'byTrack': {track: evaluate({rid:items for rid,items in groups.items() if items[0].get('track') == track}, 'score')
                        for track in sorted({items[0].get('track') or 'Unknown' for items in groups.values()})},
            'racePredictions': [{'raceId': rid, 'date': items[0]['date'], 'gameType': 'V85',
                                 'top3': [r['number'] for r in sorted(items, key=lambda r: (-r['score'], r['number']))[:3]],
                                 'winner': next(r['number'] for r in items if r['winner'])}
                                for rid, items in sorted(groups.items())]}


def later_holdout(rows):
    train, test = later_v85_split(rows)
    if len(train) < MIN_TRAIN_STARTERS or len({r['raceId'] for r in test}) < 12:
        return None
    model = estimator()
    model.fit(matrix(train), np.array([r['winner'] for r in train]))
    groups = {}
    for row, score in zip(test, model.predict_proba(matrix(test))[:, 1]):
        groups.setdefault(row['raceId'], []).append({**row, 'score': float(score)})
    paired = clean_paired(groups)
    return {'scope': 'V85_ONLY', 'trainUntil': max(r['date'] for r in train), 'trainStarts': len(train),
            'testFrom': min(r['date'] for r in test), 'testUntil': max(r['date'] for r in test),
            'metrics': evaluate(groups, 'score'), 'pairedModel': evaluate(paired, 'score'),
            'retrospectiveFinalPool': evaluate(paired, 'marketFinalPct', market=True),
            'caveat': 'Fixed parameters; no fitting on or tuning against this period in this run. Some dates were examined in earlier experiments, so this is not an untouched prospective test.'}


def compare_previous(validation):
    path = ROOT / 'research/baseline_196_races_2026.json'
    if not path.exists():
        return None
    baseline = json.loads(path.read_text(encoding='utf-8'))
    if baseline['parameters'] != estimator().get_params():
        raise ValueError('History expansion comparison requires the same fixed model parameters')
    old = {r['raceId']: r for r in baseline['validation']['racePredictions']}
    paired = [(old[r['raceId']], r) for r in validation['racePredictions'] if r['raceId'] in old]
    if len(paired) != len(old):
        raise ValueError('History expansion comparison is missing baseline test races')
    if any(a['winner'] != b['winner'] for a,b in paired):
        raise ValueError('Winner differs from the archived baseline comparison')
    def counts(items):
        n = len(items)
        return {'races': n, 'top1Count': sum(r['winner'] == r['top3'][0] for r in items),
                'top3Count': sum(r['winner'] in r['top3'] for r in items)}
    return {'sameRaces': len(paired), 'baseline': counts([a for a,b in paired]),
            'expanded': counts([b for a,b in paired]), 'baselineSource': path.relative_to(ROOT).as_posix()}

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
    expanded = any(game_type(r) == 'V75' for r in rows)
    validation = backtest(rows, compare_xgboost=expanded)
    if expanded:
        validation['laterHoldout'] = later_holdout(rows)
        validation['sameRaceHistoryComparison'] = compare_previous(validation)
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
    report['training']['byGameType'] = {kind: {'races': len({r['raceId'] for r in rows if game_type(r) == kind}),
                                             'starts': sum(game_type(r) == kind for r in rows)} for kind in ('V75', 'V85')}
    if expanded:
        report['software']['xgboost'] = __import__('xgboost').__version__
        evaluation = {'schemaVersion': 1, 'training': report['training'], 'trainingDataQuality': doc['dataQuality'],
                      'parameters': report['parameters'], 'software': report['software'], 'validation': validation,
                      'generatedAt': report['generatedAt'], 'limitations': report['limitations']}
        (ROOT/'research/expanded_model_evaluation_2026.json').write_bytes((json.dumps(evaluation, ensure_ascii=False, indent=2)+'\n').encode('utf-8'))
    output = ROOT/'rounds'/data['roundId']/'model.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'training': report['training'], 'validation': validation['metrics'],
                      'top3': [{'leg': r['leg'], 'horses': r['top3']} for r in ranked]}, ensure_ascii=False), flush=True)
if __name__ == '__main__': main()
