"""Shared data contract for historical training, without network access.

The old corpus is evidence, not a source of verifiable gallop observations.
Never mutate it or silently infer missing runners/results from market shares.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / 'research/historical_pilot_2026.json'
CURRENT = ROOT / 'research/historical_pilot_v2.json'


class InsufficientHistory(RuntimeError):
    """Expected readiness state, distinct from invalid data or a program error."""


def publish_unavailable(destination, error, source):
    """Replace stale v2 metrics with an explicit, traceable readiness result."""
    doc = load_training_data(source)
    report = {'status': 'insufficient_data', 'reason': str(error),
              'sourceRaceCount': doc['raceCount'], 'sourceStarts': doc['starterCount'],
              'trainingDataQuality': doc['dataQuality']}
    Path(destination).write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    print('MODEL NOT READY:', str(error))


def gallop_status(record):
    """Only an explicit boolean galloped flag establishes gallop/no gallop.

    Disqualification has several causes. In particular disqualified=False says
    nothing about whether a horse galloped and recovered during the race.
    Unknown codes and absent flags stay unknown until the source is verified.
    """
    value = record.get('galloped') if isinstance(record, dict) else None
    return value if type(value) is bool else None


def result_label(result):
    """Return (winner label, status); unknown results are never negative labels."""
    if not isinstance(result, dict):
        return None, 'unknown'
    value = result.get('place')
    if isinstance(value, str) and value.strip().isdigit():
        value = int(value.strip())
    valid = type(value) in (int, float) and math.isfinite(value) and value == int(value) and 0 <= value <= 30
    if result.get('disqualified') is True:
        if valid and value > 0:
            return None, 'conflicting'
        return 0, 'disqualified'
    if valid:
        return int(value == 1), 'placed' if value > 0 else 'unplaced'
    return None, 'unknown'


def prepare_training_data(document):
    """Use whole, complete fields only; quarantine incomplete/ambiguous races.

    A legacy coverage of exactly 1 certifies all registered rows survived its
    parser. Lower legacy coverage mixes scratches and unknown results, so it
    cannot be safely repaired from the aggregates. Legacy gallop is disabled.
    """
    groups = {}
    for row in document.get('rows', []):
        if not isinstance(row, dict) or not isinstance(row.get('raceId'), str):
            raise ValueError('Historical row lacks race identity')
        groups.setdefault(row['raceId'], []).append(row)
    accepted, excluded, reasons = [], [], Counter()
    source_rejected = document.get('sourceRejections', [])
    rejected_ids = set()
    for item in source_rejected:
        if (not isinstance(item, dict) or not isinstance(item.get('raceId'), str)
                or item['raceId'] in groups or item['raceId'] in rejected_ids
                or type(item.get('rows')) is not int or item['rows'] < 0
                or not isinstance(item.get('reason'), str)):
            raise ValueError('Invalid raw-source rejection provenance')
        rejected_ids.add(item['raceId'])
    previous = document.get('dataQuality', {})
    if (not isinstance(previous, dict) or previous.get('eligibleRaces') != len(groups)
            or previous.get('eligibleStarts') != sum(map(len, groups.values()))):
        previous = {}
    legacy_races = masked = 0
    for rid, rows in sorted(groups.items()):
        n = len(rows)
        legacy = all('dataContractVersion' not in r for r in rows)
        reason = None
        numbers = [r.get('number') for r in rows]
        if not 6 <= n <= 20 or any(type(x) is not int or x < 1 for x in numbers) or len(set(numbers)) != n:
            reason = 'invalid_or_duplicate_field'
        elif len({r.get('date') for r in rows}) != 1 or any(not isinstance(r.get('horse'), str) or not r['horse'].strip() for r in rows):
            reason = 'inconsistent_identity'
        elif any(not isinstance(r.get('prestartFeatures'), dict) or r['prestartFeatures'].get('field') != n for r in rows):
            reason = 'field_size_mismatch'
        elif any(type(r.get('winner')) is not int or r['winner'] not in (0, 1) for r in rows):
            reason = 'unknown_result'
        elif sum(r['winner'] for r in rows) != 1:
            reason = 'winner_not_unique'
        elif legacy and any(r.get('resultCoverage') != 1 for r in rows):
            reason = 'legacy_field_requires_raw_refetch'
        elif not legacy:
            for r in rows:
                counts = r.get('raceCounts', {})
                if (r.get('dataContractVersion') != 2 or r.get('resultCoverage') != 1
                        or r.get('resultStatus') not in ('placed', 'unplaced', 'disqualified')
                        or (r['winner'] == 1 and r.get('resultStatus') != 'placed')
                        or counts.get('active') != n or counts.get('knownResults') != n
                        or counts.get('unknownResults') != 0
                        or type(counts.get('scratched')) is not int or counts['scratched'] < 0
                        or counts.get('registered') != n + counts['scratched']):
                    reason = 'unverified_v2_field'
                    break
                coverage = r.get('featureCoverage', {})
                known, history = coverage.get('gallopObservedStarts'), coverage.get('historyStarts')
                risk = r['prestartFeatures'].get('gallop5')
                if (type(known) is not int or type(history) is not int or not 0 <= known <= history <= 5
                        or (risk is not None and (type(risk) not in (int, float)
                            or not math.isfinite(risk) or not 0 <= risk <= 1 or known < 2))):
                    reason = 'unverified_gallop_coverage'
                    break
        if reason:
            reasons[reason] += 1
            excluded.append({'raceId': rid, 'rows': n, 'reason': reason})
            continue
        if legacy:
            legacy_races += 1
        for row in rows:
            item = copy.deepcopy(row)
            if legacy:
                masked += item['prestartFeatures'].get('gallop5') is not None
                item['prestartFeatures']['gallop5'] = None
                item['riskDataStatus'] = 'legacy_gallop_not_verifiable'
            accepted.append(item)
    accepted.sort(key=lambda r: (r['date'], r['raceId'], r['number']))
    # Revalidation is idempotent: keep the original exclusion/provenance trail,
    # but always validate every row above rather than trusting a quality flag.
    prior_excluded = previous.get('quarantine', [])
    excluded = list({x['raceId']: x for x in prior_excluded + source_rejected + excluded}.values())
    reasons = Counter(x['reason'] for x in excluded)
    source_races = previous.get('sourceRaces', len(groups) + len(source_rejected))
    source_starts = previous.get('sourceStarts', sum(map(len, groups.values())) + sum(x['rows'] for x in source_rejected))
    quality = {
        'contractVersion': 2, 'sourceRaces': source_races, 'sourceStarts': source_starts,
        'eligibleRaces': len({r['raceId'] for r in accepted}), 'eligibleStarts': len(accepted),
        'excludedRaces': len(excluded), 'legacyEligibleRaces': legacy_races,
        'maskedLegacyGallopValues': masked + previous.get('maskedLegacyGallopValues', 0),
        'exclusionReasons': dict(reasons), 'quarantine': excluded,
        'limitations': ['Legacy gallop values require raw-source verification and are disabled.',
                       'Historical final market shares are not archived prestart observations.',
                       'A smaller complete-field subset is selected data, not validated betting evidence.'],
    }
    for key in ('sourceFile', 'sourceSha256'):
        if key in previous:
            quality[key] = previous[key]
    return {**document, 'rows': accepted, 'raceCount': quality['eligibleRaces'],
            'starterCount': len(accepted), 'rawSourceRaceCount': source_races, 'dataQuality': quality}


def load_training_data(path=None):
    source = Path(path) if path is not None else (CURRENT if CURRENT.exists() else LEGACY)
    raw = source.read_bytes()
    document = prepare_training_data(json.loads(raw))
    document['dataQuality'].update({'sourceFile': source.relative_to(ROOT).as_posix() if source.is_relative_to(ROOT) else source.name,
                                    'sourceSha256': hashlib.sha256(raw).hexdigest()})
    return document


def main():
    doc = load_training_data()
    quality = doc['dataQuality']
    quality['featureCoverage'] = {
        key: {'observed': sum(r['prestartFeatures'].get(key) is not None for r in doc['rows']),
              'missing': sum(r['prestartFeatures'].get(key) is None for r in doc['rows'])}
        for key in sorted({k for r in doc['rows'] for k in r['prestartFeatures']})
    }
    out = ROOT / 'research/training_data_quality_2026.json'
    out.write_text(json.dumps(quality, ensure_ascii=False, indent=2) + '\n')
    print(f"Training data: {quality['eligibleRaces']} complete races, {quality['eligibleStarts']} starts; "
          f"{quality['excludedRaces']} races quarantined; {quality['maskedLegacyGallopValues']} unsafe risk values disabled.")


if __name__ == '__main__':
    main()
