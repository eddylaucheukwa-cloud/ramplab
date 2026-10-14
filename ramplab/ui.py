"""Two synchronized native panels and the Blender ColorRamp preview widget."""
import json
import bpy
from . import properties
from .color_spaces import rgb_hex
from .operators import validate_region, regions_for_scope, signature


class RL_UL_regions(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        row = layout.row(align=True)
        row.prop(item,'enabled',text='')
        row.prop(item,'name',text='',emboss=False,icon='MESH_PLANE' if item.kind == 'RECT' else 'MESH_DATA')
        row.prop(item,'visible',text='',icon='HIDE_OFF' if item.visible else 'HIDE_ON',emboss=False)


def region_list(layout, settings):
    image = settings.image
    if not image:
        return
    data = image.ramplab
    layout.template_list('RL_UL_regions','',data,'regions',data,'active_index',rows=3)
    region = properties.active_region(image)
    if region:
        layout.prop(region,'name',text='Active Region')
        row = layout.row(align=True)
        row.prop(region,'enabled')
        row.prop(region,'visible')
        row.prop(region,'color',text='')
        try:
            validate_region(image,region)
        except ValueError:
            box = layout.box()
            box.alert = True
            box.label(text='Image size/path changed',icon='ERROR')
            box.label(text='Recreate regions on this image.')
    row = layout.row(align=True)
    row.operator('ramplab.region_manage',text='Delete Region',icon='REMOVE').action = 'DELETE'
    row.operator('ramplab.region_manage',text='Clear All',icon='TRASH').action = 'CLEAR'


def draw_preview(layout, settings):
    result = properties.current_result(settings)
    node = properties.preview_node(result)
    if not node:
        layout.label(text='Analyze to preview editable colors.',icon='INFO')
        return
    box = layout.box()
    box.label(text='Combined Regions' if result.scope == 'COMBINED' else 'Editable Result')
    try:
        metadata = json.loads(result.metadata)
        mode_name = 'Tonal Shading' if metadata['parameters']['mode'] == 'TONAL' else 'Dominant Palette'
        box.label(text=f'{mode_name} • {metadata["image"]}')
        regions = regions_for_scope(settings,result.scope)
        if result.signature != signature(settings,result.scope,regions):
            box.label(text='Settings changed: reanalyze to output.',icon='ERROR')
    except (ValueError,KeyError,TypeError):
        box.label(text='Selection changed: reanalyze to output.',icon='ERROR')
    box.template_color_ramp(node,'color_ramp',expand=True)
    try:
        weights = json.loads(result.weights)
    except (ValueError,TypeError):
        weights = []
    elements = node.color_ramp.elements
    for i,element in enumerate(elements):
        row = box.row(align=True)
        row.prop(element,'color',text='')
        row.label(text=rgb_hex(element.color))
        row.prop(element,'position',text='')
        if len(weights) == len(elements):
            row.label(text=f'{weights[i]*100:.1f}%')
        elif len(weights) == 1 and i == 0:
            row.label(text='100% (solid)')
    box.label(text='Reanalyze replaces manual edits.',icon='INFO')
    if result.warning:
        for warning in result.warning.split('; '):
            box.label(text=warning,icon='ERROR')


class RL_PT_main(bpy.types.Panel):
    bl_label = 'RampLab'
    bl_space_type = 'NODE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'RampLab'

    @classmethod
    def poll(cls, context):
        return context.space_data.tree_type == 'ShaderNodeTree'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.ramplab
        layout.template_ID(settings,'image',open='ramplab.import_image')
        layout.operator('ramplab.import_image',icon='FILE_FOLDER')
        image = settings.image
        if image and image.preview and image.preview.icon_id:
            layout.template_icon(icon_value=image.preview.icon_id,scale=5.)
        layout.prop(settings,'region_mode')
        if settings.region_mode != 'FULL':
            region_list(layout,settings)
            layout.label(text='Draw regions in an Image Editor.',icon='INFO')
        layout.prop(settings,'mode')
        layout.prop(settings,'color_count')
        if settings.mode == 'DOMINANT':
            layout.prop(settings,'sorting')
            layout.prop(settings,'palette_positioning')
            if settings.sorting == 'FREQUENCY':
                layout.label(text='Frequency order is not tonal order.',icon='INFO')
        else:
            layout.prop(settings,'tonal_positioning')
            layout.label(text='Perceptual lightness: dark to light.')
        layout.prop(settings,'interpolation')
        layout.prop(settings,'ignore_transparent')
        if settings.ignore_transparent:
            layout.prop(settings,'alpha_threshold')
        column = layout.column(align=True)
        column.enabled = image is not None
        column.operator('ramplab.analyze',text='Analyze Full Image' if settings.region_mode == 'FULL' else 'Analyze Active Region',icon='VIEWZOOM').scope = 'AUTO'
        if settings.region_mode != 'FULL':
            column.operator('ramplab.analyze',text='Analyze Combined Regions').scope = 'COMBINED'
            column.operator('ramplab.analyze',text='Analyze All Enabled Regions').scope = 'ALL'
            column.operator('ramplab.region_manage',text='Preview Active Region').action = 'PREVIEW'
        draw_preview(layout,settings)
        column = layout.column(align=True)
        column.operator('ramplab.generate',text='Create New ColorRamp',icon='NODE').action = 'CREATE'
        column.operator('ramplab.generate',text='Update Selected ColorRamp').action = 'UPDATE'
        if settings.region_mode != 'FULL':
            column.operator('ramplab.generate',text='Generate Ramps for All Regions').action = 'ALL'


class RL_PT_regions(bpy.types.Panel):
    bl_label = 'RampLab Regions'
    bl_space_type = 'IMAGE_EDITOR'
    bl_region_type = 'UI'
    bl_category = 'RampLab Regions'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.ramplab
        layout.template_ID(settings,'image',open='ramplab.import_image')
        if context.space_data.image != settings.image:
            layout.label(text='Editor and reference differ.',icon='INFO')
            layout.operator('ramplab.show_image')
            layout.operator('ramplab.use_editor_image')
        row = layout.row(align=True)
        row.enabled = settings.image is not None and context.space_data.image == settings.image
        row.operator('ramplab.rectangle_select',icon='MESH_PLANE')
        row.operator('ramplab.polygon_select',icon='MESH_DATA')
        layout.label(text='Rectangle: drag • Esc cancels')
        layout.label(text='Polygon: clicks • Enter finishes')
        layout.label(text='Backspace removes last vertex')
        layout.prop(settings,'show_overlay')
        region_list(layout,settings)
        if settings.image:
            row = layout.row(align=True)
            row.operator('ramplab.analyze',text='Analyze Active').scope = 'ACTIVE'
            row.operator('ramplab.analyze',text='Analyze Combined').scope = 'COMBINED'
        layout.label(text='Generate nodes in the Shader Editor.')


CLASSES = (RL_UL_regions,RL_PT_main,RL_PT_regions)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
