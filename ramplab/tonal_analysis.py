"""Robust lightness bands with dominant-subcluster sample representatives."""
from .color_spaces import linear_rgb_to_oklab, distance2
from .clustering import kmeans, MERGE_DISTANCE


def percentile(sorted_values, fraction):
    index = (len(sorted_values)-1)*fraction
    lower = int(index)
    upper = min(lower+1, len(sorted_values)-1)
    return sorted_values[lower] + (sorted_values[upper]-sorted_values[lower])*(index-lower)


def tonal_palette(rgb, count=5):
    if not rgb:
        raise ValueError('No valid pixels to analyze')
    labs = [linear_rgb_to_oklab(c) for c in rgb]
    values = sorted(p[0] for p in labs)
    low, high = percentile(values, .02), percentile(values, .98)
    # A small highlight/shadow population should survive collapsed robust percentiles.
    if high-low < 1e-8:
        low, high = values[0], values[-1]
    bands = [[] for _ in range(count)]
    for i, lab in enumerate(labs):
        j = min(count-1, max(0, int((lab[0]-low)/(high-low)*count))) if high-low > 1e-8 else 0
        bands[j].append(i)
    result = []
    for indices in bands:
        if not indices:
            continue
        points = [labs[i] for i in indices]
        centers, populations, labels = kmeans(points, min(3, len(points)), iterations=12)
        dominant = max(range(len(centers)), key=lambda j: populations[j])
        # Actual source pixel nearest the dominant center: no muddy RGB average.
        local = min((i for i, label in enumerate(labels) if label == dominant),
                    key=lambda i: distance2(points[i], centers[dominant]))
        source = indices[local]
        entry = dict(color=tuple(rgb[source]), lightness=labs[source][0], weight=len(indices)/len(rgb))
        if result and distance2(labs[source], linear_rgb_to_oklab(result[-1]['color'])) < MERGE_DISTANCE**2:
            result[-1]['weight'] += entry['weight']
        else:
            result.append(entry)
    result.sort(key=lambda entry: entry['lightness'])
    return result
