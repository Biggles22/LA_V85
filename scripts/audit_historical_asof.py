"""Check archived horse-statistic transitions; do not enable new features."""
import collections
import argparse
import datetime as dt
import json
from scripts import historical_pilot as h
from scripts.data_quality import result_label


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expanded', action='store_true')
    args = parser.parse_args()
    source_file = h.ROOT / 'research/historical_expanded_2024_2026.json' if args.expanded else h.DEST
    corpus = json.loads(source_file.read_text(encoding='utf-8'))
    horses, problems = collections.defaultdict(list), []
    observed = excluded_history = 0
    for source in corpus['rawSources']:
        path = source['sourceUrl'].removeprefix(h.BASE)
        h.OFFLINE = True
        raw = h.get_json(path)  # validates the cached source hash and identity
        if h.cache_document(path)['sha256'] != source['sha256']:
            raise ValueError('Historical manifest source hash mismatch')
        if not path.startswith('/races/'):
            continue
        day = dt.date.fromisoformat(raw['id'][:10])
        for start in raw['starts']:
            horse = start.get('horse', {})
            if start.get('scratched') is True or (start.get('result') or {}).get('scratched') is True:
                continue
            observed += 1
            records = (horse.get('results') or {}).get('records', [])
            excluded_history += sum(h.date_only(r.get('date')) is not None and h.date_only(r['date']) >= day for r in records)
            history = h.past_records(start, day)
            assert all(r['date'] < day.isoformat() for r in history)
            years = (horse.get('statistics') or {}).get('years', {})
            if any(str(year).isdigit() and int(year) > day.year for year in years):
                problems.append({'raceId': raw['id'], 'horseId': horse.get('id'), 'reason': 'future_statistics_year'})
            if horse.get('id') is not None:
                horses[horse['id']].append({'raceId': raw['id'], 'date': day.isoformat(),
                                          'name': horse.get('name'), 'history': history,
                                          'life': (horse.get('statistics') or {}).get('life', {}),
                                          'winner': result_label(start.get('result'))[0]})
    pairs = []
    for hid, entries in horses.items():
        entries.sort(key=lambda x: (x['date'], x['raceId']))
        for a, b in zip(entries, entries[1:]):
            if not b['history'] or b['history'][0]['id'] != a['raceId'] or a['winner'] is None:
                continue
            av, bv = a['life'].get('starts'), b['life'].get('starts')
            aw, bw = a['life'].get('placement', {}).get('1'), b['life'].get('placement', {}).get('1')
            if not all(type(x) is int for x in (av, bv, aw, bw)):
                continue
            pairs.append({'horseId': hid, 'horse': b['name'], 'beforeRace': a['raceId'], 'nextRace': b['raceId'],
                          'startsBefore': av, 'startsNext': bv, 'winsBefore': aw, 'winsNext': bw,
                          'firstRaceWinner': a['winner'],
                          'consistent': bv == av + 1 and bw == aw + a['winner']})
    report = {'schemaVersion': 1, 'source': source_file.relative_to(h.ROOT).as_posix(),
              'activeSnapshotsChecked': observed, 'nonPastHistoryRecordsExcluded': excluded_history,
              'futureYearStatistics': problems, 'consecutiveStartPairs': len(pairs),
              'consistentPairs': sum(p['consistent'] for p in pairs),
              'mismatches': [p for p in pairs if not p['consistent']],
              'pairs': pairs,
              'conclusion': 'Sample consistency checks only, not proof that every field is frozen. Career statistics remain excluded from model inputs.'}
    destination = 'research/historical_asof_audit_expanded_2026.json' if args.expanded else 'research/historical_asof_audit_2026.json'
    (h.ROOT / destination).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('pairs','mismatches')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
