#!/usr/bin/env python3
"""Collect backward-only form proxies for the verified current round."""
import concurrent.futures
import datetime as dt
import json
import urllib.request
import update_bjerke_form as model
from update_current_round import ROOT, TZ, time_value


def main():
    config = json.loads((ROOT / 'rounds.json').read_text())
    info = next(r for r in config['rounds'] if r['id'] == config['current'])
    data = json.loads((ROOT / info['data']).read_text())
    now = dt.datetime.now(TZ)
    if data['status'] != 'verified' or now >= time_value(data['startTime']):
        raise ValueError('Verified prestart data required')
    model.DAY = dt.date.fromisoformat(data['date'])
    def collect(race):
        url = model.API + race['raceId'] + '/extended'
        with urllib.request.urlopen(urllib.request.Request(url, headers=model.HEADERS), timeout=28) as response:
            raw = json.load(response)
        if raw.get('id') != race['raceId']:
            raise ValueError('Extended race identity mismatch')
        found = {s['number']: s for s in raw['starts']}
        horses = []
        for horse in race['starts']:
            start = found.get(horse['number'])
            if not start or model.normalize(start['horse']['name']) != model.normalize(horse['name']):
                raise ValueError('Extended horse identity mismatch')
            horses.append(model.analysis_entry(horse, start))
        return {'leg': race['leg'], 'raceNumber': race['raceNumber'], 'startMethod': race['startMethod'], 'sourceUrl': url, 'horses': horses}
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(collect, data['races']))
    model.add_contextual_scores(results, data['races'])
    output = {'schemaVersion': 2, 'roundId': data['roundId'], 'gameId': data['gameId'], 'snapshotId': data['snapshotId'], 'retrievedAt': now.isoformat(), 'method': 'Preliminär delranking från historisk form, klass och tempo/spår där underlag finns. Ingen kalibrerad vinstchans eller tränad XGBoost/CatBoost-prognos.', 'races': results}
    destination = ROOT / 'rounds' / data['roundId'] / 'form.json'
    destination.write_text(json.dumps(output, ensure_ascii=False, indent=2) + '\n')
    print('Collected form for', sum(len(r['horses']) for r in results), 'horses')


if __name__ == '__main__':
    main()
