# RampLab 1.0.1

Turn a reference image or selected region into an editable Blender ColorRamp.

## Install

In Blender: Edit > Preferences > Get Extensions > menu > Install from Disk.
Select the RampLab extension ZIP and enable it. Open Shader Editor > N > RampLab.

## Use

1. Select an object with an editable material.
2. Import an image or choose an existing image datablock.
3. Choose Full Image, Dominant Palette or Tonal Shading, and 3–8 colors.
4. Analyze Full Image. Review and edit the native preview.
5. Create New ColorRamp, or select exactly one ColorRamp and Update Selected ColorRamp.

For regions: Image Editor > N > RampLab Regions. Display the shared reference.
Rectangle Select: drag and release. Polygon Select: click vertices, then Enter.
Backspace removes a vertex; Escape cancels. In the Shader Editor, choose a saved
region and Analyze Active Region. Analyze Combined Regions uses the enabled union;
Generate Ramps for All Regions creates separate labeled nodes. Save the .blend to
keep selections and results. Reanalyze replaces manual preview edits.

## Documentation

[Illustrated tutorial](https://github.com/eddylaucheukwa-cloud/ramplab/blob/main/docs/TUTORIAL.md)
[Technical guide](https://github.com/eddylaucheukwa-cloud/ramplab/blob/main/docs/TECHNICAL.md)
[Testing](https://github.com/eddylaucheukwa-cloud/ramplab/blob/main/docs/TESTING.md)

## Compatibility and limitations

Tested in Blender 5.1.0. Blender 4.5 LTS and 5.2 LTS are compatibility targets
whose runtime verification remains pending. The manifest requires 4.5 or newer.

Extraction runs offline, without API keys or mandatory extra packages. NumPy
accelerates analysis when available; a standard-library fallback exists.
Blender MCP is not required.

Assumes standard sRGB/linear Rec.709 color management. HDR values are clipped to
SDR with a warning. Tonal Shading extracts lightness bands, not physical shadows.
Still/packed images are supported; UDIM, movie, sequence, Viewer/Render Result,
and linked read-only images are not. Source-path/dimension changes can invalidate
stored regions; normal absolute-to-relative save conversion is handled.

Nodes are editable and left unconnected. Undo is supported. Large images need a
whole-buffer RNA transfer; reads above 128 MiB use temporary file-backed storage,
which can use disk space and OS paging.

License: GPL-3.0-or-later. See LICENSE.txt.
