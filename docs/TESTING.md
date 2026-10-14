# Testing and compatibility

Pure extraction and region geometry are tested without Blender. Installation, UI,
and node integration are checked in Blender.

| Check | Result |
| --- | --- |
| Standalone suite, Python 3.11 | **43 passed** |
| Blender 5.1.0 registration and both extraction modes | Passed |
| Temporary ZIP installation, enable, analyze, and disable | Passed |
| Native ColorRamp creation and selected-node update | Passed |
| Multiple independent region ramps and preservation of unrelated links | Passed |
| Native GUI drawing, zoom/pan, and modal callbacks | Passed |
| Undo/redo, clean unregister, packed images, and save/reopen | Passed |
| Absolute-to-relative image path regression | Passed |
| Blender 4.5 LTS | Runtime verification pending |
| Blender 5.2 LTS | Runtime verification pending |

The GUI runner drives modal callbacks using synthetic events in an actual Blender
GUI process. This is not a claim of manual testing on every platform, display
scale, or target version. Window resize and monitor DPI merit further checks.

## Coverage

Color conversions and roundtrips; deterministic clustering; near-duplicate merging;
NumPy-free fallback; black/white/solid/two-color/grayscale references; tonal ordering;
valid stop positions; reverse/clipped rectangles; convex/concave/invalid polygons;
pixel-center boundaries; tiny/empty/transparent selections; non-finite values; HDR
clipping; union deduplication; unique sampling; and persistent UUIDs/results.

The mandatory **red-left/blue-right isolation case** passes in both modes.
Large-image indexing is tested over a synthetic 20,000 × 20,000 pixel domain
without allocating that full buffer. The mmap path is exercised with a smaller
image and a lowered allocation threshold.

## Run

From the repository root, with Python 3.11 or newer:

```sh
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/package_extension.py
python scripts/run_tests.py --blender "/path/to/blender"
```

Logs are written locally to the Git-ignored `test-results/` directory. Without
Blender, the script explicitly reports that integration checks were not run.

GUI checks run in an isolated process and exit on completion:

```sh
blender --factory-startup --enable-event-simulate --python tests/blender_interaction_test.py
```

Do not use an unsaved production scene for testing.

## Performance reference

On the development Windows host, 20,000-sample, 8-color extraction took about
**0.34 s** for Dominant Palette and **0.18 s** for Tonal Shading with NumPy; the
standard-library dominant fallback took **1.99 s**. These exclude Blender pixel
transfer and are not universal guarantees. Run `python scripts/benchmark.py` to
measure your host. Large-image disk/paging behavior has not been benchmarked
across all platforms. See [technical limitations](TECHNICAL.md).
