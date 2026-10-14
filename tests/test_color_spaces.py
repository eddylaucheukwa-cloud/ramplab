import math
import unittest
from ramplab.color_spaces import (linear_rgb_to_oklab, oklab_to_linear_rgb,
                                  srgb_to_linear, linear_to_srgb, rgb_hex)


class ColorSpaces(unittest.TestCase):
    def test_roundtrip(self):
        for rgb in [(0,0,0),(1,1,1),(1,0,0),(0,1,0),(0,0,1),(.18,.3,.7),(.001,.002,.003)]:
            for a,b in zip(rgb,oklab_to_linear_rgb(linear_rgb_to_oklab(rgb))):
                self.assertAlmostEqual(a,b,places=6)

    def test_transfer_roundtrip(self):
        for value in [0,.003,.04,.04045,.18,.5,1]:
            self.assertAlmostEqual(value,linear_to_srgb(srgb_to_linear(value)),places=7)
        self.assertAlmostEqual(srgb_to_linear(.5),.21404114048223255)

    def test_reference_red(self):
        lab = linear_rgb_to_oklab((1,0,0))
        for a,b in zip(lab,(.62795536,.22486306,.12584630)):
            self.assertAlmostEqual(a,b,places=6)

    def test_hex_is_srgb(self):
        self.assertEqual(rgb_hex((srgb_to_linear(.5),0,1,1)),'#8000FF')
        self.assertEqual(rgb_hex((0,0,0)),'#000000')

    def test_gray_chroma(self):
        for value in [.01,.3,1]:
            _,a,b = linear_rgb_to_oklab((value,)*3)
            self.assertLess(math.hypot(a,b),1e-6)
