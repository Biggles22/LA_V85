"""Rebuild every known historical V85 round from hashed raw API responses.

Run with --offline to reproduce the corpus without contacting ATG. The legacy
aggregate is only an index of game IDs and a recovery baseline, never training
evidence. Unknown results quarantine the entire race at the shared gate.
"""
import argparse
import datetime as dt
import hashlib
import json
from scripts import historical_pilot as h
from scripts.data_quality import LEGACY, CURRENT, load_training_data, prepare_training_data


def write_json(path, value):
    path.write_bytes((json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    h.OFFLINE = args.offline
    legacy = json.loads(LEGACY.read_text(encoding='utf-8'))
    old = load_training_data(LEGACY)
    old_ids = {r['raceId'] for r in legacy['rows']}
    old_eligible = {r['raceId'] for r in old['rows']}
    games = sorted({r['gameId'] for r in legacy['rows']})
    rows, rounds, attempts, sources, source_rejections = [], [], [], {}, []

    def source(path):
        payload = h.get_json(path)
        saved = json.loads((h.CACHE / (hashlib.sha256(path.encode()).hexdigest() + '.json')).read_text(encoding='utf-8'))
        sources[path] = {k: saved[k] for k in ('sourceUrl', 'retrievedAt', 'sha256')}
        return payload

    for gid in games:
        day = gid.split('_')[1]
        if day >= dt.date.today().isoformat():
            raise ValueError('Historical index contains a current or future race date')
        game = source('/games/' + gid)
        count = 0
        for entry in game['races']:
            rid = entry['id']
            raw = source('/races/' + rid + '/extended')
            parsed = h.parse_historical_race(raw, game, day)
            rejection = 'dead_heat_not_supported' if sum((s.get('result') or {}).get('place') in (1, '1') for s in raw['starts']) > 1 else 'parser_rejected'
            clean = prepare_training_data({'rows': parsed or []})
            attempts.append({'gameId': gid, 'raceId': rid, 'registered': len(raw['starts']),
                             'accepted': bool(clean['rows']),
                             'reason': clean['dataQuality']['quarantine'][0]['reason'] if clean['dataQuality']['quarantine'] else (None if clean['rows'] else rejection)})
            if parsed:
                rows.extend(parsed)
            else:
                active = sum(not (s.get('scratched') is True or (s.get('result') or {}).get('scratched') is True or (s.get('horse') or {}).get('scratched') is True) for s in raw['starts'])
                source_rejections.append({'raceId': rid, 'rows': active, 'reason': rejection})
            count += bool(clean['rows'])
        rounds.append({'date': day, 'gameId': gid, 'attemptedRaces': len(game['races']), 'completeRaces': count})
        print('RECOVER', gid, count, '/', len(game['races']), 'complete races', flush=True)

    rows.sort(key=lambda r: (r['date'], r['raceId'], r['number']))
    document = {'schemaVersion': 2, 'gameTypes': ['V85'],
                'asOfDate': max(s['retrievedAt'][:10] for s in sources.values()),
                'method': 'Rebuild complete active fields from archived extended races; explicit scratches, disqualifications and nullable results.',
                'leakageControls': 'Only dated starts strictly earlier than each race enter features. Career aggregates, current outcomes and market shares excluded from features.',
                'marketWarning': 'marketFinalPct is retrospective close-of-pool data, not an archived prestart observation.',
                'source': 'ATG site racinginfo API (unofficial)',
                'dates': sorted({r['date'] for r in rows}), 'rounds': rounds,
                'starterCount': len(rows), 'raceCount': len({r['raceId'] for r in rows}),
                'rawSources': list(sources.values()), 'sourceRejections': source_rejections, 'rows': rows}
    clean = prepare_training_data(document)
    eligible = {r['raceId'] for r in clean['rows']}
    if old_eligible - eligible:
        raise ValueError('Recovery lost previously eligible races: ' + str(sorted(old_eligible - eligible)))
    if old_ids - {a['raceId'] for a in attempts}:
        raise ValueError('Not all legacy races were re-fetched')
    audit = {'schemaVersion': 1, 'legacySourceSha256': hashlib.sha256(LEGACY.read_bytes()).hexdigest(),
             'before': old['dataQuality'], 'after': clean['dataQuality'],
             'attemptedRaces': len(attempts), 'recoveredQuarantinedRaces': len((old_ids - old_eligible) & eligible),
             'retainedEligibleRaces': len(old_eligible & eligible),
             'additionalRaces': len(eligible - old_ids),
             'remainingQuarantinedLegacyRaces': sorted((old_ids - old_eligible) - eligible),
             'rawResponses': len(sources), 'attempts': attempts,
             'featurePolicy': 'No career statistics added. A historical API response alone does not establish that all aggregate fields were frozen before the race.'}
    write_json(CURRENT, document)
    audit['sourceSha256'] = hashlib.sha256(CURRENT.read_bytes()).hexdigest()
    write_json(h.ROOT / 'research/history_recovery_2026.json', audit)
    print(json.dumps({k:v for k,v in audit.items() if k not in ('before','after','attempts')}, ensure_ascii=False), flush=True)
    print('ELIGIBLE', clean['raceCount'], 'races', clean['starterCount'], 'starts', flush=True)


if __name__ == '__main__':
    main()
