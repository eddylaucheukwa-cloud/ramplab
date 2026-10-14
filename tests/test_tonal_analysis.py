import unittest
from ramplab.tonal_analysis import tonal_palette
from ramplab.positions import stop_positions


class Tonal(unittest.TestCase):
    def test_gradient(self):
        rgb = [(i/255,)*3 for i in range(256)]
        output = tonal_palette(rgb,8)
        self.assertEqual(len(output),8)
        self.assertEqual(output,sorted(output,key=lambda e:e['lightness']))
        self.assertAlmostEqual(sum(e['weight'] for e in output),1)
        positions = stop_positions(output,'TONAL','LINEAR',tonal=True)
        self.assertEqual(positions[0],0)
        self.assertEqual(positions[-1],1)
        self.assertTrue(all(b>a for a,b in zip(positions,positions[1:])))

    def test_uniform_and_low_diversity(self):
        for color in [(0,0,0),(1,1,1),(.3,.4,.1)]:
            output = tonal_palette([color]*100,8)
            self.assertEqual(len(output),1)
            self.assertEqual(output[0]['color'],color)
        self.assertEqual(len(tonal_palette([(0,0,0)]*100+[(1,1,1)],8)),2)

    def test_actual_sample_representatives(self):
        rgb = [(1,0,0),(.5,0,0),(.1,0,0),(0,1,0),(0,0,1)]*10
        output = tonal_palette(rgb,5)
        self.assertTrue(all(e['color'] in rgb for e in output))

    def test_collapsed_positions(self):
        entries = [{'lightness':v,'weight':1/4} for v in [0,.5,.5,1]]
        output = stop_positions(entries,'TONAL','EASE',tonal=True)
        self.assertTrue(all(0<=v<=1 for v in output))
        self.assertTrue(all(b>a for a,b in zip(output,output[1:])))

    def test_determinism(self):
        colors = [(i/64,(i%4)/4,.1) for i in range(64)]
        self.assertEqual(tonal_palette(colors),tonal_palette(colors))

    def test_empty(self):
        with self.assertRaises(ValueError):
            tonal_palette([])
