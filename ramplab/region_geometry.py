"""Canonical bottom-left image UV geometry; polygon boundaries are included."""
import math

EPS = 1e-10
MAX_VERTICES = 64


def clamp_point(point):
    if len(point) != 2 or not all(math.isfinite(v) for v in point):
        raise ValueError('Region coordinates must be finite pairs')
    return tuple(max(0., min(1., float(v))) for v in point)


def rectangle(a, b):
    a, b = clamp_point(a), clamp_point(b)
    x0, x1 = sorted((a[0], b[0]))
    y0, y1 = sorted((a[1], b[1]))
    if (x1-x0)*(y1-y0) < EPS:
        raise ValueError('Selection has negligible area')
    return [(x0,y0), (x1,y0), (x1,y1), (x0,y1)]


def cross(a, b, c):
    return (b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0])


def on_segment(p, a, b):
    return abs(cross(a,b,p)) <= EPS and min(a[0],b[0])-EPS <= p[0] <= max(a[0],b[0])+EPS and min(a[1],b[1])-EPS <= p[1] <= max(a[1],b[1])+EPS


def intersects(a, b, c, d):
    ac, ad, ca, cb = cross(a,b,c), cross(a,b,d), cross(c,d,a), cross(c,d,b)
    return ((ac*ad < 0 and ca*cb < 0) or on_segment(c,a,b) or
            on_segment(d,a,b) or on_segment(a,c,d) or on_segment(b,c,d))


def polygon(vertices):
    points = [clamp_point(v) for v in vertices]
    if len(points) > 1 and points[0] == points[-1]:
        points.pop()
    if not 3 <= len(points) <= MAX_VERTICES:
        raise ValueError(f'Polygon requires 3–{MAX_VERTICES} vertices')
    n = len(points)
    for i in range(n):
        if points[i] == points[(i+1)%n]:
            raise ValueError('Polygon has duplicate adjacent vertices')
        for j in range(i+1,n):
            if j == i+1 or (i == 0 and j == n-1):
                continue
            if intersects(points[i],points[(i+1)%n],points[j],points[(j+1)%n]):
                raise ValueError('Self-intersecting polygons are not supported')
    area = sum(points[i][0]*points[(i+1)%n][1]-points[(i+1)%n][0]*points[i][1] for i in range(n))/2
    if abs(area) < EPS:
        raise ValueError('Polygon vertices must enclose a nonzero area')
    return points


def contains(point, vertices):
    inside = False
    x, y = point
    for a, b in zip(vertices, vertices[1:]+vertices[:1]):
        if on_segment(point,a,b):
            return True
        if (a[1] > y) != (b[1] > y):
            crossing = a[0] + (y-a[1])*(b[0]-a[0])/(b[1]-a[1])
            if x < crossing:
                inside = not inside
    return inside


def mouse_to_normalized(view2d, x, y):
    # Image Editor View2D is UV space, not image-pixel space.
    return tuple(view2d.region_to_view(x, y))


def normalized_to_region(view2d, point):
    return tuple(view2d.view_to_region(*point, clip=False))


def normalized_to_pixel(point, width, height):
    u, v = clamp_point(point)
    return min(width-1, int(u*width)), min(height-1, int(v*height))
