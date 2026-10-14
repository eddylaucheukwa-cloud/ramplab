import unittest
from ramplab.image_sampling import filtered_samples
from ramplab.region_geometry import rectangle
from ramplab.clustering import dominant_palette
from ramplab.tonal_analysis import tonal_palette


class Sampling(unittest.TestCase):
    def setUp(self):
        self.data = [v for y in range(8) for x in range(8) for v in ((1,0,0,1) if x<4 else (0,0,1,1))]

    def test_mandatory_red_left_blue_right(self):
        left = [('RECT',rectangle((0,0),(.5,1)))]
        right = [('RECT',rectangle((.5,0),(1,1)))]
        red,_ = filtered_samples(self.data,8,8,regions=left)
        blue,_ = filtered_samples(self.data,8,8,regions=right)
        self.assertEqual(set(red),{(1,0,0)})
        self.assertEqual(set(blue),{(0,0,1)})
        for extraction in [dominant_palette,tonal_palette]:
            self.assertGreater(extraction(red)[0]['color'][0],.99)
            self.assertLess(extraction(red)[0]['color'][2],1e-6)
            self.assertGreater(extraction(blue)[0]['color'][2],.99)

    def test_combined_union_no_duplicate_weight(self):
        regions = [('RECT',rectangle((0,0),(.75,1))),('RECT',rectangle((.25,0),(1,1)))]
        samples,_ = filtered_samples(self.data,8,8,regions=regions)
        self.assertEqual(len(samples),64)
        self.assertEqual(samples.count((1,0,0)),32)

    def test_transparency(self):
        data = [1,0,0,0]*4
        with self.assertRaises(ValueError):
            filtered_samples(data,2,2)
        self.assertEqual(len(filtered_samples(data,2,2,alpha_threshold=-1)[0]),4)

    def test_nonfinite(self):
        data = [float('nan'),0,0,1,1,0,0,1]
        samples,warnings = filtered_samples(data,2,1)
        self.assertEqual(samples,[(1,0,0)])
        self.assertTrue(warnings)

    def test_byte_srgb_and_float_linear(self):
        data = [.5,.5,.5,1]
        self.assertAlmostEqual(filtered_samples(data,1,1,decode_srgb=True)[0][0][0],.21404114)
        self.assertEqual(filtered_samples(data,1,1,decode_srgb=False)[0][0],(.5,.5,.5))

    def test_premultiplied_and_hdr(self):
        self.assertEqual(filtered_samples([.25,.1,0,.5],1,1,premultiplied=True)[0][0],(.5,.2,0))
        samples,warnings = filtered_samples([2,-.1,0,1],1,1)
        self.assertEqual(samples[0],(1,0,0))
        self.assertTrue(warnings)

    def test_grayscale_and_missing_buffer(self):
        self.assertEqual(filtered_samples([.25,.5],2,1,channels=1)[0],[(.25,)*3,(.5,)*3])
        with self.assertRaises(ValueError):
            filtered_samples([],10,10)

    def test_no_source_mutation(self):
        before = self.data[:]
        filtered_samples(self.data,8,8)
        self.assertEqual(self.data,before)
