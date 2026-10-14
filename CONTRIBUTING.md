# Contributing to RampLab

Small, focused improvements and reproducible bug reports are welcome.

## Report an issue

Include your Blender version, operating system, extraction mode, and the exact
steps that reproduce the problem. Mention whether the reference is packed,
transparent, HDR, or uses a custom color space. A small synthetic image or a
shareable screenshot helps; do not upload private reference material.

## Make a change

1. Fork the repository and make a branch for the change.
2. Follow the existing separation between pure analysis/geometry and Blender UI.
3. Add a focused regression test for changed algorithm or geometry behavior.
4. Run the standalone tests, then affected Blender checks where available.
5. Describe the behavior change, validation, and any remaining version limitations.

```sh
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/package_extension.py
python scripts/run_tests.py --blender "/path/to/blender"
```

For GUI interaction checks, launch an isolated Blender process:

```sh
blender --factory-startup --enable-event-simulate --python tests/blender_interaction_test.py
```

Do not run tests on an unsaved production scene. Keep extraction deterministic,
avoid mandatory new dependencies, and preserve the user's source image and graph.

Contributions are distributed under GPL-3.0-or-later, the project's existing license.
