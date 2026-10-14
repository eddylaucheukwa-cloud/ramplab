"""Scanline union masks: O(height * vertices), no full-resolution mask."""
import math
import random
from .region_geometry import polygon, rectangle, EPS


def row_intervals(vertices, y):
    crossings, boundaries = [], []
    for a, b in zip(vertices,vertices[1:]+vertices[:1]):
        if abs(a[1]-b[1]) <= EPS:
            if abs(y-a[1]) <= EPS:
                boundaries.append(tuple(sorted((a[0],b[0]))))
        elif (a[1] > y) != (b[1] > y):
            crossings.append(a[0]+(y-a[1])*(b[0]-a[0])/(b[1]-a[1]))
        if abs(y-a[1]) <= EPS:
            boundaries.append((a[0],a[0]))
    crossings.sort()
    return list(zip(crossings[::2],crossings[1::2])) + boundaries


def pixel_runs(width, height, regions=None):
    if width <= 0 or height <= 0:
        raise ValueError('Image has no pixel dimensions')
    if regions is None:
        return [(0,width*height)]
    if not regions:
        raise ValueError('No enabled regions')
    polygons = []
    for region in regions:
        kind, vertices = region
        vertices = rectangle(vertices[0],vertices[2]) if kind == 'RECT' else polygon(vertices)
        polygons.append((vertices,min(v[1] for v in vertices),max(v[1] for v in vertices)))
    y0 = max(0, math.ceil(min(p[1] for p in polygons)*height-.5-EPS))
    y1 = min(height-1, math.floor(max(p[2] for p in polygons)*height-.5+EPS))
    runs = []
    for y in range(y0,y1+1):
        v = (y+.5)/height
        spans = []
        for vertices, low, high in polygons:
            if low-EPS <= v <= high+EPS:
                for a,b in row_intervals(vertices,v):
                    start = max(0, math.ceil(a*width-.5-EPS))
                    end = min(width, math.floor(b*width-.5+EPS)+1)
                    if start < end:
                        spans.append((start,end))
        spans.sort()
        merged = []
        for start,end in spans:
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0],max(end,merged[-1][1]))
            else:
                merged.append((start,end))
        for start,end in merged:
            absolute = y*width+start
            if runs and runs[-1][0]+runs[-1][1] == absolute:
                runs[-1] = (runs[-1][0],runs[-1][1]+end-start)
            else:
                runs.append((absolute,end-start))
    if not runs:
        raise ValueError('Selection contains no pixel centers; enlarge the region')
    return runs


def sample_indices(runs, max_samples=20000):
    if max_samples < 1:
        raise ValueError('Sample limit must be positive')
    total = sum(length for _,length in runs)
    count = min(total,max_samples)
    rng = random.Random(410)
    # Jitter each disjoint stratum to avoid repeated stripes/checkerboard aliasing.
    offsets = [rng.randrange(i*total//count,(i+1)*total//count) for i in range(count)]
    indices, run_index, preceding = [], 0, 0
    for offset in offsets:
        while offset >= preceding+runs[run_index][1]:
            preceding += runs[run_index][1]
            run_index += 1
        indices.append(runs[run_index][0]+offset-preceding)
    return indices
