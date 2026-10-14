# RampLab example project

Open [RampLab-Tutorial.blend](RampLab-Tutorial.blend) after installing and enabling
RampLab. Select the **RampLab Tutorial** workspace if it is not already active.

![Packed landscape, saved regions, and native ColorRamp nodes](../docs/images/01-overview.png)

The example contains a **640 × 400 generated landscape color study**, a **Sky**
rectangle, a **Landscape** polygon, four unconnected editable ColorRamp nodes,
and a short **RampLab - Start Here** guide inside Blender.

The packed image has no external source path, so the sample regions do not depend
on the author's folder layout. [ramplab-reference.png](ramplab-reference.png) is
included if you prefer importing the reference into your own project.

## Try it

1. In Shader Editor → N → RampLab, choose Full Image and an extraction mode.
2. Analyze Full Image, review the preview, and edit a swatch.
3. Create New ColorRamp to add your own result.
4. Choose Multiple Saved Regions, select Sky or Landscape, and Analyze Active Region.
5. In Image Editor → N → RampLab Regions, draw and rename another region.

Ctrl+Z undoes changes. Reanalyze replaces manual preview edits. Generated ramps
are unconnected; wire them into your material as needed.

Read the [illustrated tutorial](../docs/TUTORIAL.md) for the complete workflow.
This example was created in **Blender 5.1.0**. Older Blender users can import the
PNG and follow the guide in a fresh project if the `.blend` cannot be opened.
