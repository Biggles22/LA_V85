"""Score immutable normalized forecasts against official race winner sets."""
def score(records, winners, size):
    seen = set()
    hits = 0
    legs = []
    for record in records:
        race = record['raceId']
        numbers = [h['number'] for h in record['horses']]
        if race in seen or len(numbers) != size or len(set(numbers)) != size:
            raise ValueError('Duplicate race or ambiguous selection')
        seen.add(race)
        if race not in winners or not winners[race]:
            continue
        legs.append(record['leg'])
        hits += bool(set(numbers) & set(winners[race]))
    return {'hits': hits, 'races': len(legs), 'legs': legs}
