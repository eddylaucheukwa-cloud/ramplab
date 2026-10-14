import unittest
from ramplab.region_mask import pixel_runs,sample_indices
from ramplab.region_geometry import rectangle,contains


def indices(runs):
    return {i for start,length in runs for i in range(start,start+length)}


class Masks(unittest.TestCase):
    def test_center_rectangle(self):
        region = ('RECT',rectangle((.25,.25),(.75,.75)))
        self.assertEqual(indices(pixel_runs(4,4,[region])),{5,6,9,10})

    def test_outside_rectangle(self):
        region = ('RECT',[(-1,-1),(1,-1),(1,.5),(-1,.5)])
        self.assertEqual(indices(pixel_runs(4,4,[region])),set(range(8)))

    def test_concave_against_point_in_polygon(self):
        points = [(0,0),(1,0),(1,.4),(.4,.4),(.4,1),(0,1)]
        expected = {y*20+x for y in range(20) for x in range(20) if contains(((x+.5)/20,(y+.5)/20),points)}
        self.assertEqual(indices(pixel_runs(20,20,[('POLYGON',points)])),expected)

    def test_triangle_boundaries(self):
        points = [(0,0),(1,0),(0,1)]
        expected = {y*10+x for y in range(10) for x in range(10) if contains(((x+.5)/10,(y+.5)/10),points)}
        self.assertEqual(indices(pixel_runs(10,10,[('POLYGON',points)])),expected)

    def test_overlapping_union(self):
        a = ('RECT',rectangle((0,0),(.75,1)))
        b = ('RECT',rectangle((.25,0),(1,1)))
        runs = pixel_runs(8,4,[a,b,a])
        self.assertEqual(indices(runs),set(range(32)))
        self.assertEqual(sum(n for _,n in runs),32)

    def test_tiny_and_empty(self):
        a = ('RECT',rectangle((.49,.49),(.51,.51)))
        self.assertEqual(indices(pixel_runs(1,1,[a])),{0})
        with self.assertRaises(ValueError):
            pixel_runs(100,100,[('RECT',rectangle((0,0),(.001,.001)))])
        with self.assertRaises(ValueError):
            pixel_runs(10,10,[])

    def test_large_sampling_is_bounded(self):
        output = sample_indices(pixel_runs(20000,20000),20000)
        self.assertEqual(len(output),20000)
        self.assertEqual(len(set(output)),20000)
        self.assertEqual(output,sample_indices(pixel_runs(20000,20000),20000))
        self.assertEqual(sample_indices([(10,3)],20000),[10,11,12])
