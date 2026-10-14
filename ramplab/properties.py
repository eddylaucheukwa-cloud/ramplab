"""Persistent settings and per-image regions/results shared by both editors."""
import bpy
from bpy.props import (BoolProperty, CollectionProperty, EnumProperty, FloatVectorProperty,
                       FloatProperty, IntProperty, PointerProperty, StringProperty)


def redraw(owner_or_context, context=None):
    context = context or owner_or_context
    if context and context.window_manager:
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type in {'IMAGE_EDITOR','NODE_EDITOR'}:
                    area.tag_redraw()


def interpolation_changed(settings, context):
    image = settings.image
    if image:
        result = current_result(settings)
        node = preview_node(result)
        if node:
            node.color_ramp.interpolation = settings.interpolation
    redraw(context)


def active_region_changed(data, context):
    settings = context.scene.ramplab if context and context.scene else None
    if settings and settings.image == data.id_data:
        settings.preview_scope = 'ACTIVE'
    redraw(context)


def image_changed(settings, context):
    settings.preview_scope = 'FULL' if settings.region_mode == 'FULL' else 'ACTIVE'
    redraw(context)


def region_mode_changed(settings, context):
    settings.preview_scope = 'FULL' if settings.region_mode == 'FULL' else 'ACTIVE'
    redraw(context)


class RLPoint(bpy.types.PropertyGroup):
    uv: FloatVectorProperty(size=2, min=0., max=1.)


class RLResult(bpy.types.PropertyGroup):
    preview_tree: PointerProperty(type=bpy.types.NodeTree)
    signature: StringProperty()
    metadata: StringProperty()
    weights: StringProperty()
    warning: StringProperty()
    scope: StringProperty()
    source_id: StringProperty()


class RLRegion(bpy.types.PropertyGroup):
    uid: StringProperty()
    name: StringProperty(default='Region', update=redraw)
    kind: EnumProperty(items=[('RECT','Rectangle',''),('POLYGON','Polygon','')])
    points: CollectionProperty(type=RLPoint)
    enabled: BoolProperty(name='Enabled', default=True, update=redraw)
    visible: BoolProperty(name='Visible', default=True, update=redraw)
    color: FloatVectorProperty(name='Outline Color', subtype='COLOR', size=3,
                              default=(.2,.7,1.), min=0., max=1., update=redraw)
    width: IntProperty()
    height: IntProperty()
    source_path: StringProperty()
    result: PointerProperty(type=RLResult)


class RLImageData(bpy.types.PropertyGroup):
    regions: CollectionProperty(type=RLRegion)
    active_index: IntProperty(default=0, min=0, update=active_region_changed)
    full_result: PointerProperty(type=RLResult)
    combined_result: PointerProperty(type=RLResult)


class RLSettings(bpy.types.PropertyGroup):
    image: PointerProperty(name='Reference Image', type=bpy.types.Image, update=image_changed)
    region_mode: EnumProperty(name='Region Mode', items=[
        ('FULL','Full Image','Analyze the complete reference image'),
        ('RECT','Rectangle Selection','Analyze the active saved region; draw in Image Editor'),
        ('POLYGON','Polygon Selection','Analyze the active saved region; draw in Image Editor'),
        ('SAVED','Multiple Saved Regions','Switch, combine, or generate saved regions')], update=region_mode_changed)
    mode: EnumProperty(name='Extraction Mode', items=[
        ('DOMINANT','Dominant Palette','Representative perceptual color clusters'),
        ('TONAL','Tonal Shading','Lightness-based colors from dark to light')])
    color_count: IntProperty(name='Color Count', min=3, max=8, default=5)
    sorting: EnumProperty(name='Sorting', items=[('BRIGHTNESS','Brightness','Dark to light'),
        ('HUE','Hue','Perceptual hue order'),('FREQUENCY','Frequency','Largest group first; not a shading gradient')])
    interpolation: EnumProperty(name='Interpolation', items=[('CONSTANT','Constant','Discrete bands'),
        ('LINEAR','Linear','Linear blend'),('EASE','Ease','Smooth blend')], update=interpolation_changed)
    palette_positioning: EnumProperty(name='Stop Positioning', items=[('UNIFORM','Uniform','Equal bands'),
        ('POPULATION','Population','Band lengths follow color proportions')])
    tonal_positioning: EnumProperty(name='Stop Positioning', items=[('TONAL','Tonal','Normalized lightness'),
        ('UNIFORM','Uniform','Evenly spaced stops')])
    ignore_transparent: BoolProperty(name='Ignore Transparent Pixels', default=True)
    alpha_threshold: FloatProperty(name='Alpha Threshold', default=.01, min=0., max=1.)
    show_overlay: BoolProperty(name='Selection Overlay', default=True, update=redraw)
    preview_scope: StringProperty(default='FULL')


def active_region(image):
    if not image:
        return None
    data = image.ramplab
    return data.regions[data.active_index] if 0 <= data.active_index < len(data.regions) else None


def current_result(settings):
    if not settings.image:
        return None
    if settings.preview_scope == 'COMBINED':
        return settings.image.ramplab.combined_result
    if settings.region_mode == 'FULL':
        return settings.image.ramplab.full_result
    region = active_region(settings.image)
    return region.result if region else None


def preview_node(result):
    if result and result.preview_tree:
        return result.preview_tree.nodes.get('RampLab Preview')
    return None


CLASSES = (RLPoint, RLResult, RLRegion, RLImageData, RLSettings)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Scene.ramplab = PointerProperty(type=RLSettings)
    bpy.types.Image.ramplab = PointerProperty(type=RLImageData)


def unregister():
    del bpy.types.Scene.ramplab
    del bpy.types.Image.ramplab
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
