"""Collect calendar-discovered Saturday V75/V85 rounds, with resumable raw evidence."""
import argparse
import collections
import datetime as dt
import hashlib
import json
import urllib.error
from scripts import historical_pilot as h
from scripts.data_quality import CURRENT, prepare_training_data
from scripts.recover_historical import write_json

OUTPUT = h.ROOT / 'research/historical_expanded_2024_2026.json'
REPORT = h.ROOT / 'research/history_expansion_2026.json'


def saturdays(start, end):
    day = start + dt.timedelta(days=(5 - start.weekday()) % 7)
    while day <= end:
        yield day.isoformat()
        day += dt.timedelta(days=7)


def calendar_games(calendar, day):
    if calendar.get('date') != day:
        raise ValueError('Calendar date mismatch')
    result = []
    games = calendar.get('games', {})
    for kind in ('V75', 'V85'):
        entries = games.get(kind, []) if isinstance(games, dict) else [g for g in games if str(g.get('id', '')).startswith(kind + '_')]
        if isinstance(entries, dict):
            entries = [entries]
        for game in entries:
            gid = game.get('id', '')
            if not gid.startswith(kind + '_' + day + '_'):
                raise ValueError('Calendar game date/type mismatch')
            result.append(gid)
    return sorted(set(result))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-date', default='2024-01-01')
    parser.add_argument('--until-date', default='2026-10-31')
    parser.add_argument('--offline', action='store_true')
    args = parser.parse_args()
    start, end = dt.date.fromisoformat(args.from_date), dt.date.fromisoformat(args.until_date)
    if start > end or end >= dt.date.today():
        parser.error('The collection interval must be strictly historical')
    h.OFFLINE, h.COMPRESS_CACHE = args.offline, True
    baseline = json.loads(CURRENT.read_text(encoding='utf-8'))
    baseline_eligible = {r['raceId'] for r in prepare_training_data(baseline)['rows']}
    days = list(saturdays(start, end))
    sources, rows, rounds, attempts, failures, discovery, rejected = {}, {}, [], [], [], [], []

    def source(path):
        value = h.get_json(path)
        saved = h.cache_document(path)
        sources[path] = {**{k: saved[k] for k in ('sourceUrl', 'retrievedAt', 'sha256')},
                         'cachePath': h.cache_path(path).relative_to(h.ROOT).as_posix()}
        return value

    for day in days:
        try:
            games = calendar_games(source('/calendar/day/' + day), day)
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            failures.append({'date': day, 'stage': 'calendar', 'error': str(error)[:200]})
            print('DATE_FAILED', day, str(error)[:100], flush=True)
            continue
        discovery.append({'date': day, 'games': games})
        for gid in games:
            try:
                game = source('/games/' + gid)
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                failures.append({'gameId': gid, 'stage': 'game', 'error': str(error)[:200]})
                continue
            complete = 0
            seen = set()
            for entry in game['races']:
                rid = entry['id']
                if rid in seen:
                    raise ValueError('Duplicate race in game ' + gid)
                seen.add(rid)
                try:
                    raw = source('/races/' + rid + '/extended')
                except (urllib.error.URLError, TimeoutError, ValueError) as error:
                    failures.append({'gameId': gid, 'raceId': rid, 'stage': 'race', 'error': str(error)[:200]})
                    continue
                parsed = h.parse_historical_race(raw, game, day)
                clean = prepare_training_data({'rows': parsed or []})
                reason = None
                if not parsed:
                    reason = 'dead_heat_not_supported' if sum((s.get('result') or {}).get('place') in (1, '1') for s in raw['starts']) > 1 else 'parser_rejected'
                    active = sum(not (s.get('scratched') is True or (s.get('result') or {}).get('scratched') is True or (s.get('horse') or {}).get('scratched') is True) for s in raw['starts'])
                    if rid not in rows:
                        rejected.append({'raceId': rid, 'rows': active, 'reason': reason})
                else:
                    if rid in rows:
                        raise ValueError('Race appears in multiple collected games: ' + rid)
                    rows[rid] = parsed
                    if not clean['rows']:
                        reason = clean['dataQuality']['quarantine'][0]['reason']
                accepted = bool(clean['rows'])
                complete += accepted
                attempts.append({'gameId': gid, 'raceId': rid, 'accepted': accepted, 'reason': reason})
            rounds.append({'date': day, 'gameId': gid, 'gameType': gid.split('_')[0], 'races': len(game['races']), 'eligibleRaces': complete})
            print('COLLECTED', gid, complete, '/', len(game['races']), 'eligible; total', len(rows), 'parsed races', flush=True)
    output_rows = sorted((r for field in rows.values() for r in field), key=lambda r: (r['date'], r['raceId'], r['number']))
    document = {'schemaVersion': 2, 'gameTypes': ['V75', 'V85'],
                'selection': {'from': start.isoformat(), 'until': end.isoformat(), 'weekday': 'Saturday', 'calendarDates': days},
                'asOfDate': max(s['retrievedAt'][:10] for s in sources.values()) if sources else None,
                'method': 'Calendar-discovered Saturday V75/V85 rounds. Whole active fields, raw-source hashes and strictly earlier past-start features.',
                'leakageControls': 'Current outcomes, final pool shares and mutable career aggregates are excluded from model features.',
                'marketWarning': 'Retrospective final pool shares belong to each source game type, not archived prestart snapshots.',
                'dates': sorted({r['date'] for r in output_rows}), 'rounds': rounds,
                'starterCount': len(output_rows), 'raceCount': len(rows), 'sourceRejections': rejected,
                'rawSources': list(sources.values()), 'rows': output_rows}
    clean = prepare_training_data(document)
    eligible = {r['raceId'] for r in clean['rows']}
    missing_baseline = sorted(baseline_eligible - eligible)
    report = {'schemaVersion': 1, 'selection': document['selection'],
              'baselineSha256': hashlib.sha256(CURRENT.read_bytes()).hexdigest(),
              'baselineEligibleRaces': len(baseline_eligible), 'missingBaselineRaces': missing_baseline,
              'calendarDatesAttempted': len(days), 'calendarDatesRead': len(discovery),
              'discovery': discovery, 'rounds': rounds, 'failures': failures, 'attempts': attempts,
              'quality': clean['dataQuality'], 'additionalEligibleRaces': len(eligible - baseline_eligible),
              'byGameType': {kind: {'races': len({r['raceId'] for r in clean['rows'] if r['gameType'] == kind}),
                                    'starts': sum(r['gameType'] == kind for r in clean['rows'])} for kind in ('V75', 'V85')},
              'rawResponseCount': len(sources)}
    write_json(REPORT, report)
    if failures or missing_baseline:
        raise SystemExit('Collection incomplete; raw responses retained for resuming. Existing training data preserved. See history_expansion_2026.json')
    write_json(OUTPUT, document)
    report['sourceSha256'] = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
    write_json(REPORT, report)
    print('COMPLETE', json.dumps({k: report[k] for k in ('additionalEligibleRaces', 'byGameType', 'rawResponseCount', 'sourceSha256')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
