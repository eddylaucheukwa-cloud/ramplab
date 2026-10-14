"""Deterministic K-means++ in OKLab, optionally accelerated by NumPy."""
import math
import random
from .color_spaces import linear_rgb_to_oklab, oklab_to_linear_rgb, distance2

try:
    import numpy as np
except ImportError:
    np = None

MERGE_DISTANCE = 0.012


def kmeans(points, count, iterations=32):
    if not points:
        raise ValueError('No valid pixels to analyze')
    count = max(1, min(count, len(points)))
    rng = random.Random(1729)
    centers = [tuple(points[rng.randrange(len(points))])]
    nearest = [float('inf')] * len(points)
    for _ in range(1, count):
        nearest = [min(d, distance2(p, centers[-1])) for p, d in zip(points, nearest)]
        total = sum(nearest)
        if total < 1e-18:
            break
        target = rng.random()*total
        for p, d in zip(points, nearest):
            target -= d
            if target <= 0:
                centers.append(tuple(p))
                break
    if np is not None:
        data = np.asarray(points, dtype=np.float64)
        for _ in range(iterations):
            c = np.asarray(centers)
            labels = ((data[:, None, :] - c[None, :, :])**2).sum(axis=2).argmin(axis=1)
            new = [tuple(data[labels == j].mean(axis=0)) if (labels == j).any() else centers[j]
                   for j in range(len(centers))]
            movement = max(distance2(a, b) for a, b in zip(new, centers))
            centers = new
            if movement < 1e-10:
                break
        labels = ((data[:, None, :] - np.asarray(centers)[None, :, :])**2).sum(axis=2).argmin(axis=1).tolist()
    else:
        for _ in range(iterations):
            labels = [min(range(len(centers)), key=lambda j: distance2(p, centers[j])) for p in points]
            sums = [[0., 0., 0.] for _ in centers]
            populations = [0]*len(centers)
            for p, j in zip(points, labels):
                populations[j] += 1
                for axis in range(3):
                    sums[j][axis] += p[axis]
            new = [tuple(v/populations[j] for v in sums[j]) if populations[j] else centers[j]
                   for j in range(len(centers))]
            movement = max(distance2(a, b) for a, b in zip(new, centers))
            centers = new
            if movement < 1e-10:
                break
        labels = [min(range(len(centers)), key=lambda j: distance2(p, centers[j])) for p in points]
    populations = [labels.count(j) for j in range(len(centers))]
    return centers, populations, labels


def dominant_palette(rgb, count=5, sorting='BRIGHTNESS', merge_distance=MERGE_DISTANCE):
    labs = [linear_rgb_to_oklab(c) for c in rgb]
    centers, populations, _ = kmeans(labs, count)
    groups = []
    for center, population in zip(centers, populations):
        if not population:
            continue
        found = next((g for g in groups if distance2(center, g[0]) < merge_distance**2), None)
        if found is None:
            groups.append([center, population])
        else:
            weight = found[1] + population
            found[0] = tuple((a*found[1]+b*population)/weight for a, b in zip(found[0], center))
            found[1] = weight
    if sorting == 'FREQUENCY':
        groups.sort(key=lambda g: (-g[1], g[0]))
    elif sorting == 'HUE':
        groups.sort(key=lambda g: (math.atan2(g[0][2], g[0][1]) % (2*math.pi), g[0][0]))
    else:
        groups.sort(key=lambda g: g[0])
    return [dict(color=tuple(max(0., min(1., v)) for v in oklab_to_linear_rgb(lab)),
                 lightness=lab[0], weight=n/len(rgb)) for lab, n in groups]
