#!/usr/bin/env python3
"""Audit pinned, previously published race files offline; never train a model.

The output is a result ledger, not the historical_pilot training contract.
No third-party Python is imported and no network requests are made.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import gzip
import hashlib
import io
import json
import re
import tarfile
from collections import Counter, defaultdict
from pathlib import Path

try:
    from scripts.data_quality import gallop_status, result_label
except ModuleNotFoundError:
    from data_quality import gallop_status, result_label

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'archive': {
        'url': 'https://codeload.github.com/lbondarenko/travmodel/tar.gz/de68577d26a3384e0e16d38bbe650297cc586c77',
        'commit': 'de68577d26a3384e0e16d38bbe650297cc586c77',
        'sha256': 'ebd6a48830ac51b5bd4c26895d89bea68fe21df5fd7c9fe47187b7b068c1dfce',
    },
    'sample_game': {
        'url': 'https://raw.githubusercontent.com/jojo-swe/trav-mvp/b937891915b985a48152cbe74ceb9f4c6ec3d47d/data/game_V85_2025-10-25.json',
        'commit': 'b937891915b985a48152cbe74ceb9f4c6ec3d47d',
        'sha256': 'ea82b4e56c504f9b1e41c85ac5f9c25281a725da1430818308e9ec521d3caa07',
    },
    'csv': {
        'url': 'https://raw.githubusercontent.com/jojo-swe/trav-mvp/b937891915b985a48152cbe74ceb9f4c6ec3d47d/data/atg_starters.csv',
        'commit': 'b937891915b985a48152cbe74ceb9f4c6ec3d47d',
        'sha256': 'acab0a86b9a01549f118429780fb633567b184bb0706b05e4bb7a0c4388f6c92',
    },
}


def verified_bytes(path, source):
    if Path(path).stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Source exceeds 64 MiB')
    blob = Path(path).read_bytes()
    if hashlib.sha256(blob).hexdigest() != source['sha256']:
        raise ValueError(f'Source hash mismatch: {Path(path).name}')
    return blob


def check_race(race):
    """Keep complete Swedish harness fields; never remove an unknown result."""
    starts = race.get('starts', [])
    active = [s for s in starts if not (s.get('scratched') is True
              or (s.get('result') or {}).get('scratched') is True)]
    labels = [result_label(s.get('result'))[0] for s in active]
    if race.get('sport') != 'trot' or race.get('track', {}).get('countryCode') != 'SE':
        reason = 'other_sport_or_country'
    elif (race.get('status') != 'results'
          or not re.fullmatch(r'\d{4}-\d{2}-\d{2}_\d+_\d+', str(race.get('id', '')))
          or race['id'][:10] != race.get('date')):
        reason = 'invalid_identity_or_status'
    elif not 6 <= len(active) <= 20:
        reason = 'field_size'
    elif (any(type(s.get('number')) is not int or s['number'] < 1
              or not s.get('horse', {}).get('id') or not s['horse'].get('name') for s in starts)
          or len({s['number'] for s in starts}) != len(starts)
          or len({s['horse']['id'] for s in starts}) != len(starts)):
        reason = 'invalid_or_duplicate_starter'
    elif any(y is None for y in labels):
        reason = 'unknown_result'
    elif sum(labels) != 1:
        reason = 'winner_not_unique'
    else:
        reason = 'eligible_result_field'
    return reason, active


def compare_csv(race_id, active, csv_rows):
    observed = {s['number']: s for s in active}
    flattened = {int(s['start_number']): s for s in csv_rows}
    shared = observed.keys() & flattened.keys()
    return {
        'raceId': race_id, 'rawActive': len(active), 'csvRows': len(csv_rows),
        'missingNumbers': sorted(observed.keys() - flattened.keys()),
        'extraNumbers': sorted(flattened.keys() - observed.keys()),
        'duplicateCsvNumbers': len(csv_rows) - len(flattened),
        'identityOrWinnerConflicts': [n for n in sorted(shared)
            if str(observed[n]['horse']['id']) != flattened[n]['horse_id']
            or result_label(observed[n].get('result'))[0] != int(flattened[n]['won'])],
    }


def run(args):
    raw = {key: verified_bytes(getattr(args, key), source) for key, source in SOURCES.items()}
    games = []
    with tarfile.open(fileobj=io.BytesIO(raw['archive']), mode='r:gz') as archive:
        for member in archive:
            parts = Path(member.name).parts
            if len(parts) != 4 or parts[1:3] != ('data', 'games_hist') or not member.name.endswith('.json.gz'):
                continue
            if not member.isfile() or member.size > 4 * 1024 * 1024:
                raise ValueError('Invalid archive member')
            compressed = archive.extractfile(member).read()
            with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as inner:
                payload = inner.read(8 * 1024 * 1024 + 1)
            if len(payload) > 8 * 1024 * 1024:
                raise ValueError('Race payload exceeds limit')
            game = json.loads(payload)
            if game['id'] + '.json.gz' != parts[-1]:
                raise ValueError('Game filename/identity mismatch')
            games.append((game, {'source': 'archive', 'member': '/'.join(parts[1:]),
                                'sha256': hashlib.sha256(compressed).hexdigest()}))
    games.append((json.loads(raw['sample_game']), {'source': 'sample_game'}))
    csv_rows = list(csv.DictReader(io.StringIO(raw['csv'].decode('utf-8'))))
    csv_groups = defaultdict(list)
    for row in csv_rows:
        csv_groups[row['race_id']].append(row)
    quarantine_blob = Path(args.quarantine).read_bytes()
    quarantine = {r['raceId'] for r in json.loads(quarantine_blob)['quarantine']}
    seen, ledger, comparisons, exclusions = set(), [], [], []
    source_counts, game_types = Counter(), Counter()
    for game, source in games:
        game_types[game['type']] += 1
        for race in game['races']:
            rid = race['id']
            if rid in seen:
                raise ValueError(f'Duplicate raw race: {rid}')
            seen.add(rid)
            reason, active = check_race(race)
            if reason != 'eligible_result_field':
                exclusions.append({'raceId': rid, 'reason': reason})
                continue
            source_counts[game['type']] += 1
            if rid in csv_groups:
                comparisons.append(compare_csv(rid, active, csv_groups[rid]))
            ledger.append({
                'raceId': rid, 'date': race['date'], 'track': race['track']['name'],
                'gameId': game['id'], 'gameType': game['type'], 'source': source,
                'registered': len(race['starts']), 'active': len(active),
                'scratchedNumbers': sorted(s['number'] for s in race['starts'] if s not in active),
                'distance': race.get('distance'), 'startMethod': race.get('startMethod'),
                'starts': [{
                    'number': s['number'], 'horseId': s['horse']['id'], 'horse': s['horse']['name'],
                    'postPosition': s.get('postPosition'), 'distance': s.get('distance'),
                    'driverId': s.get('driver', {}).get('id'),
                    'trainerId': s['horse'].get('trainer', {}).get('id'),
                    'winner': result_label(s.get('result'))[0],
                    'resultStatus': result_label(s.get('result'))[1],
                    'place': s['result'].get('place'),
                    'galloped': gallop_status(s['result']),
                    'marketObservation': 'historical_result_payload_not_prestart',
                    'poolType': game['type'],
                    'betDistributionRaw': s.get('pools', {}).get(game['type'], {}).get('betDistribution'),
                } for s in active],
            })
    ledger.sort(key=lambda r: (r['date'], r['raceId']))
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    ledger_bytes = ''.join(json.dumps(r, ensure_ascii=False, sort_keys=True) + '\n' for r in ledger).encode()
    (output / 'verified-results.jsonl').write_bytes(ledger_bytes)
    incomplete = [x for x in comparisons if x['missingNumbers'] or x['extraNumbers'] or x['duplicateCsvNumbers']]
    report = {
        'schemaVersion': 1, 'checkedOn': dt.datetime.now(dt.timezone.utc).date().isoformat(),
        'status': 'result_archive_only_not_model_ready', 'sources': SOURCES,
        'qualitySourceSha256': hashlib.sha256(quarantine_blob).hexdigest(),
        'games': len(games), 'gameTypes': dict(game_types), 'rawRaces': len(seen),
        'eligibleRaces': len(ledger), 'eligibleStarts': sum(r['active'] for r in ledger),
        'eligibleRaceTypes': dict(source_counts),
        'dateRange': [ledger[0]['date'], ledger[-1]['date']] if ledger else [],
        'quarantinedV85Races': len(quarantine), 'rawOverlapWithQuarantine': sorted(seen & quarantine),
        'exclusionReasons': dict(Counter(x['reason'] for x in exclusions)), 'exclusions': exclusions,
        'gallopObservations': dict(Counter('unknown' if s['galloped'] is None else str(s['galloped']).lower()
                                         for r in ledger for s in r['starts'])),
        'csv': {'rows': len(csv_rows), 'races': len(csv_groups),
                'dateRange': [min(r['date'] for r in csv_rows), max(r['date'] for r in csv_rows)],
                'overlapWithQuarantine': len(csv_groups.keys() & quarantine),
                'comparedRawRaces': len(comparisons), 'incompleteFields': len(incomplete),
                'missingStarters': sum(len(x['missingNumbers']) for x in comparisons),
                'identityOrWinnerConflicts': sum(len(x['identityOrWinnerConflicts']) for x in comparisons),
                'comparisons': comparisons},
        'ledgerSha256': hashlib.sha256(ledger_bytes).hexdigest(),
        'limitations': [
            'Third-party published archives; no direct ATG revalidation was possible.',
            'Only eight eligible races belong to V85; other pools require separate evaluation.',
            'Missing gallop flags remain unknown, never false.',
            'No archived prestart market observations or full per-horse extended history.',
            'Rebuild rolling features from strictly earlier dates; mutable career aggregates were omitted.',
            'CSV has incomplete fields and is excluded from the result ledger.',
            'Raw datasets are stored locally; redistribution licensing has not been established.',
        ],
    }
    (output / 'audit.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ['status', 'games', 'rawRaces', 'eligibleRaces', 'eligibleStarts', 'dateRange', 'ledgerSha256']}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in SOURCES:
        parser.add_argument('--' + key.replace('_', '-'), required=True, type=Path)
    parser.add_argument('--quarantine', type=Path, default=ROOT / 'research/training_data_quality_2026.json')
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args())


if __name__ == '__main__':
    main()
