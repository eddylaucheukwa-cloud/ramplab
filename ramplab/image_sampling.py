"""Blender pixel acquisition and shared full/region sampling, without source edits."""
from array import array
from contextlib import contextmanager
import math
import mmap
import os
import tempfile
from .color_spaces import srgb_to_linear
from .region_mask import pixel_runs, sample_indices

HEAP_BUFFER_LIMIT = 128 * 1024 * 1024
SUPPORTED_SPACES = {'sRGB', 'Non-Color', 'Linear', 'Linear Rec.709', 'Linear Rec.709 (sRGB)'}


def image_path(image):
    """Canonical path survives Blender's absolute-to-relative save conversion."""
    if not image.filepath:
        return ''
    import bpy
    return os.path.normcase(os.path.abspath(bpy.path.abspath(image.filepath,library=image.library)))


@contextmanager
def read_pixels(image):
    if image.source not in {'FILE','GENERATED'}:
        raise ValueError('Use a single still image (not UDIM, movie, sequence, or Render Result)')
    width,height = image.size
    if width <= 0 or height <= 0:
        raise ValueError('Image is empty or unreadable; reload it or import a valid file')
    length = len(image.pixels)
    if length != width*height*image.channels or image.channels not in {1,2,3,4}:
        raise ValueError('Image has a missing or unsupported pixel buffer')
    if image.colorspace_settings.name not in SUPPORTED_SPACES:
        raise ValueError('Unsupported color space: use sRGB or Linear Rec.709 reference images')
    if length*4 <= HEAP_BUFFER_LIMIT:
        data = array('f',[0])*length
        image.pixels.foreach_get(data)
        yield data
    else:
        # RNA exposes only whole-buffer foreach_get. File-backed storage bounds heap use.
        with tempfile.TemporaryFile() as backing:
            backing.truncate(length*4)
            with mmap.mmap(backing.fileno(),length*4) as mapping:
                data = memoryview(mapping).cast('f')
                try:
                    image.pixels.foreach_get(data)
                    yield data
                finally:
                    data.release()


def filtered_samples(data, width, height, channels=4, regions=None, max_samples=20000,
                     alpha_threshold=.01, decode_srgb=False, premultiplied=False):
    if len(data) != width*height*channels:
        raise ValueError('Missing pixel buffer')
    runs = pixel_runs(width,height,regions)
    samples = []
    warnings = set()
    for index in sample_indices(runs,max_samples):
        start = index*channels
        pixel = tuple(data[start+j] for j in range(channels))
        if not all(math.isfinite(v) for v in pixel):
            warnings.add('Non-finite pixels skipped')
            continue
        alpha = pixel[-1] if channels in {2,4} else 1.
        if alpha_threshold >= 0 and alpha <= alpha_threshold:
            continue
        rgb = pixel[:3] if channels >= 3 else (pixel[0],)*3
        if premultiplied and alpha > 1e-8:
            rgb = tuple(v/alpha for v in rgb)
        if any(v < 0 or v > 1 for v in rgb):
            warnings.add('HDR/out-of-gamut samples clipped to SDR [0,1]')
        rgb = tuple(max(0.,min(1.,v)) for v in rgb)
        if decode_srgb:
            rgb = tuple(srgb_to_linear(v) for v in rgb)
        samples.append(rgb)
    if not samples:
        raise ValueError('Selection contains no valid sampled pixels (transparent/invalid); enlarge it or change alpha filtering')
    return samples, sorted(warnings)


def extract_region_samples(image, region=None, max_samples=20000, alpha_threshold=.01, data=None):
    regions = None if region is None else ([region] if isinstance(region,tuple) else region)
    if data is None:
        with read_pixels(image) as pixels:
            return extract_region_samples(image,region,max_samples,alpha_threshold,pixels)
    return filtered_samples(data,*image.size,channels=image.channels,regions=regions,
                            max_samples=max_samples,alpha_threshold=alpha_threshold,
                            decode_srgb=not image.is_float and image.colorspace_settings.name == 'sRGB',
                            premultiplied=image.is_float and image.alpha_mode == 'PREMUL')
