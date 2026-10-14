"""ColorRamp positions, including left-inclusive constant palette bands."""


def stop_positions(entries, positioning='UNIFORM', interpolation='CONSTANT', tonal=False):
    n = len(entries)
    if n <= 1:
        return [0.0] * n
    if positioning == 'TONAL' and tonal:
        low, high = entries[0]['lightness'], entries[-1]['lightness']
        raw = [(e['lightness']-low)/(high-low) for e in entries] if high-low > 1e-8 else [i/(n-1) for i in range(n)]
    elif positioning == 'POPULATION':
        total = sum(e['weight'] for e in entries)
        weights = [e['weight']/total for e in entries]
        if interpolation == 'CONSTANT':
            # Last color needs a nonzero segment: no stop at 1 for palette bands.
            raw, cumulative = [], 0.
            for weight in weights:
                raw.append(cumulative)
                cumulative += weight
        else:
            centers, cumulative = [], 0.
            for weight in weights:
                centers.append(cumulative + weight/2)
                cumulative += weight
            raw = [(v-centers[0])/(centers[-1]-centers[0]) for v in centers]
    else:
        denominator = n if interpolation == 'CONSTANT' and not tonal else n-1
        raw = [i/denominator for i in range(n)]
    epsilon = 1e-5
    output = []
    for i, position in enumerate(raw):
        lower = output[-1]+epsilon if output else 0.
        output.append(max(lower, min(1-(n-1-i)*epsilon, position)))
    return output
