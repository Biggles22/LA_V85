"""Count winner hits only on explicit frozen choices and settled race identities."""
def metric(rankings, winners, size):
    rows = []
    for race_id, choices in rankings.items():
        if race_id not in winners or not winners[race_id]:
            continue
        if len(choices) != size or len(set(choices)) != size:
            raise ValueError('Expected exactly %s unique ordered choices' % size)
        rows.append((race_id, bool(set(choices) & set(winners[race_id]))))
    return {'hits': sum(hit for _, hit in rows), 'races': len(rows),
            'raceIds': [rid for rid, _ in rows], 'hitRaceIds': [rid for rid, hit in rows if hit]}


def score(first, top3, winners):
    return {'first': metric(first, winners, 1), 'top3': metric(top3, winners, 3)}


def paired(left, right, winners):
    answer = {}
    for name, size in [('first', 1), ('top3', 3)]:
        common = sorted(set(left[name]) & set(right[name]) & set(winners))
        answer[name] = {'left': metric({r:left[name][r] for r in common}, winners, size),
                        'right': metric({r:right[name][r] for r in common}, winners, size)}
    return answer
