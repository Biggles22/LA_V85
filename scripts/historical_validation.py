"""Pure chronological split helpers: mixed historical training, V85-only testing."""


def game_type(row):
    return row.get('gameType') or str(row.get('gameId', '')).split('_')[0]


def v85_folds(rows, min_dates=4, min_starts=160):
    for day in sorted({r['date'] for r in rows if game_type(r) == 'V85'}):
        train = [r for r in rows if r['date'] < day]
        test = [r for r in rows if r['date'] == day and game_type(r) == 'V85']
        if len(train) >= min_starts and len({r['date'] for r in train}) >= min_dates:
            yield day, train, test


def later_v85_split(rows, boundary='2026-08-01'):
    return ([r for r in rows if r['date'] < boundary],
            [r for r in rows if r['date'] >= boundary and game_type(r) == 'V85'])
