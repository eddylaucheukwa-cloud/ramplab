import unittest
from ramplab.region_geometry import (rectangle,polygon,contains,normalized_to_pixel,
    normalized_to_region,mouse_to_normalized)


class FakeView:
    def __init__(self,scale,offset):
        self.scale,self.offset = scale,offset

    def region_to_view(self,x,y):
        return ((x-self.offset[0])/self.scale[0],(y-self.offset[1])/self.scale[1])

    def view_to_region(self,x,y,clip=False):
        return (x*self.scale[0]+self.offset[0],y*self.scale[1]+self.offset[1])


class Geometry(unittest.TestCase):
    def test_reverse_rectangle(self):
        self.assertEqual(rectangle((.8,.9),(.2,.1)),rectangle((.2,.1),(.8,.9)))

    def test_clipping(self):
        self.assertEqual(rectangle((-.2,.2),(1.2,.8)),[(0,.2),(1,.2),(1,.8),(0,.8)])

    def test_degenerate_rectangle(self):
        with self.assertRaises(ValueError):
            rectangle((.2,.2),(.2,.8))

    def test_convex_and_boundary(self):
        points = polygon([(0,0),(1,0),(.5,1)])
        self.assertTrue(contains((.5,.4),points))
        self.assertTrue(contains((.5,0),points))
        self.assertFalse(contains((.9,.9),points))

    def test_concave(self):
        points = polygon([(0,0),(1,0),(1,.4),(.4,.4),(.4,1),(0,1)])
        self.assertTrue(contains((.2,.8),points))
        self.assertFalse(contains((.8,.8),points))

    def test_invalid_polygons(self):
        for points in [[(0,0),(1,1),(0,1),(1,0)],[(0,0),(.5,.5),(1,1)],
                       [(0,0),(1,0)],[(0,0),(1,0),(1,0),(0,1)],[(float('nan'),0),(1,0),(0,1)]]:
            with self.assertRaises(ValueError):
                polygon(points)

    def test_coordinate_preservation(self):
        for scale,offset in [((400,200),(0,0)),((1200,600),(-400,60)),((800,400),(200,-170))]:
            view = FakeView(scale,offset)
            uv = (.25,.75)
            self.assertEqual(mouse_to_normalized(view,*normalized_to_region(view,uv)),uv)
        self.assertEqual(normalized_to_pixel((0,0),100,50),(0,0))
        self.assertEqual(normalized_to_pixel((1,1),100,50),(99,49))

    def test_vertex_limit(self):
        with self.assertRaises(ValueError):
            polygon([(i/65,.5) for i in range(65)])

    def test_small_self_intersecting_polygon(self):
        with self.assertRaises(ValueError):
            polygon([(0,0),(.004,.003),(0,.003),(.003,0)])
