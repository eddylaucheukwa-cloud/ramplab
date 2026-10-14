# RampLab 1.0.1

First public release of RampLab, an offline Blender extension that converts
reference images and selected regions into editable ColorRamp nodes.

## Included

- Dominant Palette extraction using K-means++ in OKLab.
- Tonal Shading extraction with dark-to-light source representatives.
- Full-image, rectangle, polygon, and combined-region analysis.
- Named regions stored with the `.blend` file.
- Editable native previews, proportions, hex values, and stop positioning.
- Create/update ColorRamp operations and independent ramps for enabled regions.
- A packed example project and an illustrated tutorial captured in Blender.
- A fix for normal absolute-to-relative image path changes when saving.

## Install

Download **ramplab-1.0.1.zip** from the assets below. In Blender, open
**Edit → Preferences → Get Extensions → menu → Install from Disk**, select the
ZIP, and enable RampLab. Open **Shader Editor → N → RampLab**.

Do not install GitHub's automatic Source code ZIP as the extension.

[Illustrated tutorial](https://github.com/eddylaucheukwa-cloud/ramplab/blob/main/docs/TUTORIAL.md)
· [Example project](https://github.com/eddylaucheukwa-cloud/ramplab/tree/main/examples)

## Verification and limitations

43 standalone tests pass. Native installation, GUI, node output, undo/redo, and
save/reopen checks have been run in **Blender 5.1.0**. **4.5 LTS** and **5.2 LTS**
are compatibility targets whose runtime verification is still pending.

The extension assumes standard sRGB / linear Rec.709 color management. HDR values
are clipped to SDR with a warning. Still and packed images are supported; UDIMs,
movies, sequences, and linked read-only images are outside this release's scope.

License: GPL-3.0-or-later. No cloud, API key, or Blender MCP dependency.
