# RampLab

**Turn a reference image into an editable Blender ColorRamp.**

RampLab is an offline Blender extension for artists building stylized materials,
illustrations, and color studies. Extract the main colors of an image, create a
dark-to-light tonal ramp, or isolate a specific area with a rectangle or polygon.
Review and adjust the colors before creating real Blender nodes.

![RampLab in Blender: reference image, saved regions, extracted colors, and editable ColorRamp nodes](docs/images/01-overview.png)

[Download the installable ZIP](https://github.com/eddylaucheukwa-cloud/ramplab/releases/latest)
· [Illustrated tutorial](docs/TUTORIAL.md)
· [Try the example project](examples/README.md)

## What it does

- **Dominant Palette:** find representative colors using perceptual OKLab clustering.
- **Tonal Shading:** extract colors in dark-to-light order for artistic tonal remapping.
- **Full image or selected regions:** draw rectangles and concave polygons in Blender's Image Editor.
- **Saved regions:** name selections, switch between them, and save them in the `.blend` file.
- **Combined extraction:** analyze the union of enabled regions without counting overlaps twice.
- **Editable preview:** adjust swatches, ramp positions, and interpolation with native Blender controls.
- **Real node output:** create a ColorRamp, update exactly one selected ColorRamp, or generate one ramp per enabled region.
- **Offline workflow:** no cloud services, network calls, API keys, or mandatory extra packages.

Generated nodes are left unconnected so you decide where to use them. Blender Undo
supports the analysis, region, and node operations. RampLab does not require Blender MCP.

## Install

1. Download **`ramplab-1.0.1.zip`** from [Releases](https://github.com/eddylaucheukwa-cloud/ramplab/releases/latest).
2. Open **Edit → Preferences → Get Extensions** in Blender.
3. Open the top-right menu and choose **Install from Disk**.
4. Select the ZIP and enable **RampLab** if needed.
5. Open the **Shader Editor**, press **N**, and choose the **RampLab** tab.

Use the extension ZIP from the release assets. GitHub's **Source code (zip)** and
**Code → Download ZIP** contain the whole repository and are not the installable extension.

| Blender version | Verification |
| --- | --- |
| **5.1.0** | Tested with native GUI, installation, node output, save/reopen, and undo/redo |
| **4.5 LTS** | Compatibility target; runtime verification pending |
| **5.2 LTS** | Compatibility target; runtime verification pending |

The extension manifest requires Blender 4.5 or newer. See [testing details](docs/TESTING.md).

## Your first ramp

**Import Image → Choose Mode → Analyze → Review Colors → Create ColorRamp.**

1. Select an object with an editable material in the Shader Editor.
2. In **RampLab**, click **Import Image** or choose an existing image datablock.
3. Choose **Full Image**, an extraction mode, and **Color Count** (3–8).
4. Click **Analyze Full Image**.
5. Edit the preview colors and positions, then click **Create New ColorRamp**.

![Dominant palette extraction using RampLab's native Blender preview](docs/images/02-dominant-palette.png)

To update a node, select **exactly one ColorRamp**, make it active, and click
**Update Selected ColorRamp**. Other nodes and links are preserved.

For selections, open an **Image Editor → N → RampLab Regions**. Drag a rectangle,
or click polygon vertices and press **Enter**. Return to the Shader Editor, choose
a saved region, and click **Analyze Active Region**.

Follow the [illustrated tutorial](docs/TUTORIAL.md) for both extraction modes,
region selection, combined extraction, and node updates.

## Choosing a mode

| | Dominant Palette | Tonal Shading |
| --- | --- | --- |
| Best for | Main colors, clothing, vegetation, palette studies | Sky, hair, and stylized dark-to-light remapping |
| How it works | K-means++ clustering in OKLab | Robust lightness bands with representative source colors |
| Order | Brightness, Hue, or Frequency | Dark to light |
| Positioning | Uniform or population-based | Uniform or normalized tonal lightness |

Tonal Shading uses perceptual lightness. It does **not** physically detect shadows
or separate lighting from material color. Frequency ordering in Dominant Palette
does not imply a shading gradient.

## Things to know

- A low-diversity reference can produce fewer distinct colors than requested.
- **Reanalyze replaces manual preview edits.** Changing interpolation alone does not recluster.
- Source images are not cropped, resized, or painted by RampLab.
- Standard sRGB / linear Rec.709 references are supported. HDR samples are clipped to SDR with a warning; custom OCIO primaries need prior conversion.
- Still and packed images are supported. UDIMs, movies, sequences, and linked read-only images are outside this release's scope.
- When you move a project that uses external files, keep its reference images available or pack them. Stored region path checks can require recreating regions after source-path changes.

See the [technical guide](docs/TECHNICAL.md) for algorithms, color management,
performance, and limitations.

## Development

The extension lives in [`ramplab/`](ramplab/). Algorithms and geometry are testable
without Blender; UI and node integration use `bpy`.

```sh
python -m unittest discover -s tests -p "test_*.py" -v
python scripts/package_extension.py
python scripts/run_tests.py --blender "/path/to/blender"
```

NumPy is used when available, with a tested standard-library fallback. There are
no mandatory dependencies to install for the extension.

[Testing](docs/TESTING.md) · [Contributing](CONTRIBUTING.md) · [Changelog](CHANGELOG.md)

## License

GNU GPL **3.0 or later**. See [LICENSE](LICENSE).
