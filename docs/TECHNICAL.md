# RampLab 1.0.1

Offline reference-image color extraction for Blender. Includes Dominant Palette,
Tonal Shading, rectangle/polygon selections, persistent named regions, union
analysis, editable previews, and safe creation/update of real ColorRamp nodes.

Targets: Blender **5.2 LTS** and **4.5 LTS**. This build has been exercised in
**Blender 5.1.0**, including an actual GUI process. Target-version
verification remains outstanding; see [testing details](TESTING.md).

## Installation

1. Download `ramplab-1.0.1.zip` from the release assets, or use `dist/` in a source checkout.
2. In Blender, open **Edit → Preferences → Get Extensions**.
3. Open the top-right menu and choose **Install from Disk**. Select the ZIP.
4. Enable RampLab if it is not enabled automatically.
5. Open a **Shader Editor**, press **N**, and choose **RampLab**.

Do not unzip the archive before installing. The manifest and entry point are at
the archive root. No external packages, network, cloud service, or keys are required.
Blender's bundled NumPy accelerates clustering; a standard-library fallback is
provided and tested. RampLab requests file access to import images and to use
temporary file-backed pixel storage for large images.

## Quick walkthrough

**Import Image → Choose Mode → Analyze → Review Colors → Create/Update ColorRamp.**

1. Select an object with an editable material and enable material nodes if needed.
2. Use **Import Image**, or select an existing Image datablock, including packed images.
3. Choose **Full Image**, **Dominant Palette** or **Tonal Shading**, and 3–8 colors.
4. Click **Analyze Full Image**. A low-diversity image may return fewer colors.
5. Edit colors, positions, and interpolation in the native ColorRamp preview.
   The rows beneath it show editable swatches, sRGB hex values, and original sample
   proportions. Proportions describe the analysis, not edited segment lengths.
6. Click **Create New ColorRamp**. The new node is selected, placed beside the
   existing graph, and left unconnected.
7. To update a node, select **exactly one ColorRamp**, make it active, and click
   **Update Selected ColorRamp**. Links, other nodes, and material properties are
   preserved. Blender Undo reverses analysis, region edits, and node output.

Changing interpolation updates the current preview without reclustering. Changing
analysis settings requires an explicit reanalysis before output. Reanalyze replaces
manual edits; adjusting colors/positions never starts automatic image analysis.
The preview's interpolation control also directly determines output interpolation.

## Regions: two synchronized native panels

RampLab never changes your workspace or editor type. Open an **Image Editor**
yourself, press **N**, and choose **RampLab Regions**. Both panels use the same
reference image and per-image region collection.

- **Show Reference Here** displays the selected reference in this existing editor.
- **Use This Editor Image** makes the editor's current image the shared reference.
- **Rectangle Select:** press LMB, drag in any direction, release to save. Escape
  or right-click cancels. Borders are clipped to the image; zero-area drags are rejected.
- **Polygon Select:** click vertices, press Enter or double-click to finish.
  Backspace removes the last vertex; Escape/right-click cancels. Concave polygons
  work; self-intersections, collinear/duplicate degeneracy, and more than 64 vertices
  are rejected with an explanation. Vertices are clipped to the image boundaries.
- Middle-mouse and wheel navigation pass through during selection. After completion
  the modal tool releases its cursor and navigation behaves normally.
- Select and rename regions in either list. Each region has separate Enabled,
  Visible, and outline-color controls. Visibility affects only drawing; Enabled
  controls inclusion in combined/all-region actions. The active region can be
  analyzed even when it is disabled for combined extraction.
- **Selection Overlay** hides saved selections; an in-progress selection still
  displays live feedback. Active outlines/fills are emphasized.

In the Shader Editor, choose a region mode to reveal the list and region actions.
Rectangle/Polygon modes analyze the active saved selection; they do not secretly
launch another editor. Multiple Saved Regions exposes the same saved selections.

- **Analyze Active Region:** uses only that region's pixels and stores its result.
- **Analyze Combined Regions:** analyzes the union of all enabled areas, with each
  overlapping pixel counted once; shows a separate combined result.
- Selecting another saved region switches back to its independent result. Use
  **Preview Active Region** to leave the combined preview explicitly.
- **Analyze All Enabled Regions:** stores one independently editable result per region.
- **Create New ColorRamp:** outputs whichever full/active/combined result is shown.
- **Generate Ramps for All Regions:** creates exactly one node per enabled region
  for each command invocation. Missing results are analyzed; existing edited results
  are retained. Stale results require explicit **Analyze All Enabled Regions**.
  Nodes use labels such as `RampLab | Sky`, carry a UUID region ID in custom
  metadata, and are arranged in separated rows/columns beside the existing graph.
  Running Create/Generate again intentionally creates another independent set.

Save the `.blend` to persist regions, UUIDs, names, visibility, active selection,
analysis metadata, and edited previews. Drawing a region gives its image a fake
user so otherwise-unused image definitions survive saving. For external file images,
pack the image or preserve its file path to make the project portable. Switching
reference images exposes each image's own regions. Changing an image's dimensions
or file path blocks its old regions and warns you to recreate them on the current
image; RampLab never silently rebinds a region to another image. Paths are compared
canonically, so Blender converting an absolute path into a relative path while
saving does not invalidate regions or analysis results.

## Algorithms and stop positions

**Dominant Palette:** deterministically sample at most 20,000 selected pixels,
convert linear RGB to OKLab, seed K-means++ with a fixed random seed, and run up to
32 Lloyd iterations. Empty clusters are retained during iteration and discarded
from the output. Centers within an internal OKLab distance of 0.012 are merged,
with populations conserved. Sort by lightness, perceptual hue, or descending
sample frequency. Frequency order is not a shading gradient. Constant is the
default interpolation. Uniform Constant bands use starts `0, 1/N, …, (N−1)/N`;
the last color therefore occupies a real interval. Population Constant bands use
cumulative proportions. Blended ramps span 0–1 with evenly spaced stops or
normalized population midpoints.

**Tonal Shading:** separately estimate the selected pixels' 2nd/98th percentile
OKLab lightness range and partition it into 3–8 lightness bands. Fold the tails
into endpoint bands. In each nonempty band, use a small perceptual subclustering
pass, then choose an actual source sample nearest the dominant subcluster center.
This avoids naive RGB averaging across unrelated hues. Merge adjacent nearly
identical representatives and order by lightness. Tonal positions normalize the
representatives' lightness into 0–1, with a small minimum separation for collapsed
positions; uniform positioning is also available. Hue/frequency sorting is hidden
in this mode to preserve its natural order. Constant, Linear, and Ease work.

This is **tonal/lightness-based extraction**, not physical shadow detection. A
photograph cannot reliably separate illumination, surface reflectance, and local
color. Artists can adjust every stop to suit the material. A solid-color result
contains one distinct color; Blender requires two ramp elements, so it is copied
to positions 0 and 1. The 100% swatch annotation identifies this case.

## Coordinates, masking, and performance

Normalized image coordinates are canonical: `(0,0)` is bottom left and `(1,1)`
is top right, matching Blender's pixel-buffer orientation. Image Editor View2D
maps to normalized UV coordinates, not pixel coordinates. Modal input uses the
editor's WINDOW region even when invoked from its sidebar. Overlays transform
normalized points back through the current View2D every draw, including zoom,
pan, resize, and display-scale changes.

Masking operates on pixel centers. Rectangle/polygon boundaries are inclusive;
scanline parity with explicit boundary handling supports concave simple polygons.
Polygon bounds limit the rows processed. Scanline intervals are unioned before
sampling, so overlapping regions cannot bias statistics. Disjoint population
strata use fixed-seed jitter, avoiding duplicate samples and regular-grid aliasing.
No full-resolution selection mask is allocated. Tiny regions with at least one
pixel center work; a region covering no pixel center is rejected.

Analysis runs only in explicit operators, on Blender's main thread, with progress
reporting. One raw pixel read is reused within all-region commands; no pixel cache
survives an operation, so pixel edits, region edits, alpha changes, and changed
settings cannot return a cached analysis. Existing previews are deliberate
snapshots: after painting/reloading pixels at the same path/size, explicitly
Reanalyze to refresh them. No clustering occurs on UI redraw. Draw handlers are
removed on unregister, transient tools cancel on Escape/editor changes/file load,
and the extension uses no timers or unsafe background RNA threads.

Blender RNA exposes whole-buffer `foreach_get`, so the initial pixel transfer is
still proportional to image size even for a small region. Buffers up to 128 MiB
use a compact float array; larger reads use a temporary file-backed mmap and are
cleaned up after analysis. This bounds Python heap allocation, but large images
still need temporary disk space and can cause OS paging. Only selected pixels
are converted or clustered. The NumPy-free fallback is slower on large samples.

## Color management and limitations

- Analysis assumes standard **linear Rec.709/sRGB primaries** and Blender's standard
  color configuration. OKLab conversions and hex display use those primaries.
- Byte `sRGB` image buffers expose encoded channel values: decode exactly once.
  Float buffers expose stored float values and are treated as already scene-linear;
  no additional sRGB decode is applied. Byte Non-Color/Linear references are treated
  as linear. Float PREMUL references are unpremultiplied when alpha is nonzero.
- Preview swatches and node colors store the same linear RGBA values; hex codes
  encode those RGB values to sRGB. AgX/other render view transforms may make a
  rendered material look different from an sRGB hex swatch.
- Unsupported image color-space names are rejected. Custom OCIO configurations or
  different working-space primaries are not automatically converted and should
  not be used without converting the reference into standard Rec.709 first.
- HDR/negative samples are clipped to SDR [0,1] with a warning. Non-finite samples
  are skipped. Alpha filtering defaults to alpha > 0.01; extraction outputs opaque
  RGB colors, with output alpha editable in the preview. If all sampled pixels are
  invalid/transparent, enlarge the selection or adjust filtering.
- Still FILE and GENERATED images are supported, including packed files. UDIM,
  movies, sequences, Render Result, Viewer images, and linked read-only images are
  rejected. Unreadable/empty images report a clear error.
- The thumbnail appears when Blender supplies a native preview icon; the native
  Image Editor provides the full image view. No custom image-editor replacement.
- Result preview ramps live in small `.RampLab Preview` node groups linked from
  image properties. Reanalysis reuses them; deleting regions releases unused
  previews. Disabling the extension removes its UI/handlers while retaining saved
  data. Preview groups are not connected to materials.
- Optional toon-material helper and advanced weighted regions are intentionally
  omitted. The two required extraction algorithms and all core region workflows
  are included. Generated ramps can be used in Eevee or Cycles materials; this
  extension does not create an Eevee-only Shader-to-RGB helper.

## Development and verification

From the source project root:

```text
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/run_tests.py --blender "path/to/blender.exe"
python scripts/package_extension.py
blender -b --factory-startup --command extension validate dist/ramplab-1.0.1.zip
```

GUI runtime test (isolated test process, exits on completion):

```text
blender --factory-startup --enable-event-simulate --python tests/blender_interaction_test.py
```

Running the checks writes unit/smoke logs, GUI results, and screenshots to the
local Git-ignored `test-results/` directory.
The GUI runner drives modal callbacks with synthetic events in a real Blender
window and validates actual View2D transforms, GPU drawing, and Undo/Redo.
Unit tests include the mandatory red-left/blue-right correctness case in both
extraction modes. The common Blender smoke test also tests regions; the separate
`blender_region_smoke_test.py` entry point runs it for convenience.

License: GNU GPL version 3 or later. See [LICENSE](../LICENSE).
