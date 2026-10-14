import unittest
from unittest.mock import patch
from ramplab import clustering
from ramplab.color_spaces import distance2
from ramplab.positions import stop_positions


class Clustering(unittest.TestCase):
    def test_solids(self):
        for rgb in [(0,0,0),(1,1,1),(.2,.7,.1)]:
            output = clustering.dominant_palette([rgb]*30,8)
            self.assertEqual(len(output),1)
            self.assertAlmostEqual(output[0]['weight'],1)
            self.assertLess(distance2(rgb,output[0]['color']),1e-12)

    def test_two_color_population(self):
        output = clustering.dominant_palette([(1,0,0)]*30+[(0,0,1)]*10,8,'FREQUENCY')
        self.assertEqual(len(output),2)
        self.assertAlmostEqual(output[0]['weight'],.75)
        self.assertLess(distance2(output[0]['color'],(1,0,0)),1e-10)

    def test_near_duplicates(self):
        self.assertEqual(len(clustering.dominant_palette([(.2,.2,.2),(.201,.2,.2)]*20,5)),1)

    def test_deterministic(self):
        colors = [(i/100,(i*7%100)/100,(i*13%100)/100) for i in range(100)]
        self.assertEqual(clustering.dominant_palette(colors),clustering.dominant_palette(colors))

    def test_fallback(self):
        colors = [(1,0,0)]*10+[(0,0,1)]*10+[(0,1,0)]*10
        accelerated = clustering.dominant_palette(colors,5)
        with patch.object(clustering,'np',None):
            fallback = clustering.dominant_palette(colors,5)
        self.assertEqual(len(fallback),3)
        for a,b in zip(accelerated,fallback):
            self.assertLess(distance2(a['color'],b['color']),1e-10)
            self.assertAlmostEqual(a['weight'],b['weight'])

    def test_empty(self):
        with self.assertRaises(ValueError):
            clustering.dominant_palette([])

    def test_constant_uniform_segment_positions(self):
        entries = [{'lightness':i*.2,'weight':.25} for i in range(4)]
        self.assertEqual(stop_positions(entries),[0,.25,.5,.75])
        self.assertEqual(stop_positions(entries,interpolation='LINEAR'),[0,1/3,2/3,1])

    def test_population_segment_positions(self):
        entries = [{'weight':w} for w in [.6,.3,.1]]
        output = stop_positions(entries,'POPULATION')
        self.assertAlmostEqual(output[1],.6)
        self.assertAlmostEqual(output[2],.9)
        output = stop_positions(entries,'POPULATION','EASE')
        self.assertEqual(output[0],0)
        self.assertEqual(output[-1],1)
