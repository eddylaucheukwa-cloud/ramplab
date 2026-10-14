"""Explicit analysis, editable native previews, and safe node output."""
import json
import bpy
from bpy.props import StringProperty, EnumProperty
from bpy_extras.io_utils import ImportHelper
from . import properties, ramp_builder
from .clustering import dominant_palette
from .tonal_analysis import tonal_palette
from .positions import stop_positions
from .image_sampling import read_pixels, extract_region_samples, image_path


def geometry(region):
    return region.kind,[tuple(point.uv) for point in region.points]


def validate_region(image, region):
    if (region.width,region.height) != tuple(image.size) or region.source_path != image_path(image):
        raise ValueError(f'Image dimensions/path changed since "{region.name}" was drawn. Recreate the region on the current image')


def regions_for_scope(settings, scope):
    image = settings.image
    if not image:
        raise ValueError('Import or select a reference image first')
    if not image.is_editable:
        raise ValueError('Make the reference image local before saving RampLab results')
    if scope == 'FULL':
        return None
    if scope == 'ACTIVE':
        region = properties.active_region(image)
        if not region:
            raise ValueError('Draw a rectangle or polygon in an Image Editor first')
        regions = [region]
    else:
        regions = [region for region in image.ramplab.regions if region.enabled]
        if not regions:
            raise ValueError('Enable at least one saved region')
    for region in regions:
        validate_region(image,region)
    return regions


def parameters(settings):
    return dict(mode=settings.mode,count=settings.color_count,
                sorting=settings.sorting if settings.mode == 'DOMINANT' else 'BRIGHTNESS',
                positioning=settings.palette_positioning if settings.mode == 'DOMINANT' else settings.tonal_positioning,
                alpha=settings.alpha_threshold if settings.ignore_transparent else -1.)


def signature(settings, scope, regions):
    image = settings.image
    return json.dumps(dict(parameters=parameters(settings),scope=scope,size=list(image.size),
                           path=image_path(image),space=image.colorspace_settings.name,is_float=image.is_float,
                           alpha_mode=image.alpha_mode,
                           regions=[(r.uid,geometry(r)) for r in regions] if regions else None),sort_keys=True)


def analyze(settings, scope, regions, pixels):
    region_data = [geometry(r) for r in regions] if regions else None
    rgb,warnings = extract_region_samples(settings.image,region_data,alpha_threshold=parameters(settings)['alpha'],data=pixels)
    entries = (dominant_palette(rgb,settings.color_count,settings.sorting) if settings.mode == 'DOMINANT'
               else tonal_palette(rgb,settings.color_count))
    params = parameters(settings)
    positions = stop_positions(entries,params['positioning'],settings.interpolation,settings.mode == 'TONAL')
    return entries,positions,warnings,signature(settings,scope,regions)


def save_result(result, settings, scope, region_id, analysis):
    entries,positions,warnings,sig = analysis
    if not result.preview_tree:
        result.preview_tree = bpy.data.node_groups.new('.RampLab Preview','ShaderNodeTree')
    node = properties.preview_node(result)
    if not node:
        node = result.preview_tree.nodes.new('ShaderNodeValToRGB')
        node.name = 'RampLab Preview'
    stops = [(tuple(e['color'])+(1.,),pos) for e,pos in zip(entries,positions)]
    ramp_builder.populate(node.color_ramp,stops,settings.interpolation)
    result.scope = scope
    result.source_id = region_id
    result.signature = sig
    result.metadata = json.dumps(dict(parameters=parameters(settings),sample_limit=20000,
                                      image=settings.image.name,entries=entries,positions=positions))
    result.weights = json.dumps([e['weight'] for e in entries])
    result.warning = '; '.join(warnings)


def output_stops(result):
    node = properties.preview_node(result)
    if not node:
        raise ValueError('Analyze first; there is no editable result')
    return [(tuple(e.color),e.position) for e in node.color_ramp.elements], node.color_ramp.interpolation


def validate_result(settings, result, scope, regions):
    if not properties.preview_node(result):
        raise ValueError('Analyze this selection first')
    if result.signature != signature(settings,scope,regions):
        raise ValueError('Image, regions, or analysis settings changed. Reanalyze explicitly to replace the previous edited result')
    return output_stops(result)


def remove_result(result):
    tree = result.preview_tree
    result.preview_tree = None
    if tree and tree.users == 0:
        bpy.data.node_groups.remove(tree)


class RL_OT_import(bpy.types.Operator, ImportHelper):
    bl_idname = 'ramplab.import_image'
    bl_label = 'Import Image'
    bl_options = {'REGISTER','UNDO'}
    filename_ext = ''
    filter_glob: StringProperty(default='*.png;*.jpg;*.jpeg;*.webp;*.tif;*.tiff;*.bmp;*.exr;*.hdr', options={'HIDDEN'})

    def execute(self, context):
        try:
            image = bpy.data.images.load(self.filepath,check_existing=True)
            if min(image.size) <= 0:
                raise ValueError('Blender could not read the image')
            context.scene.ramplab.image = image
            context.scene.ramplab.preview_scope = 'FULL'
            return {'FINISHED'}
        except (RuntimeError,ValueError,OSError) as error:
            self.report({'ERROR'},str(error))
            return {'CANCELLED'}


class RL_OT_show_image(bpy.types.Operator):
    bl_idname = 'ramplab.show_image'
    bl_label = 'Show Reference Here'
    bl_description = 'Show the reference in this existing Image Editor; no workspace changes'

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'IMAGE_EDITOR' and context.scene.ramplab.image

    def execute(self, context):
        context.space_data.image = context.scene.ramplab.image
        return {'FINISHED'}


class RL_OT_use_editor_image(bpy.types.Operator):
    bl_idname = 'ramplab.use_editor_image'
    bl_label = 'Use This Editor Image'
    bl_options = {'REGISTER','UNDO'}

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'IMAGE_EDITOR' and context.space_data.image

    def execute(self, context):
        context.scene.ramplab.image = context.space_data.image
        return {'FINISHED'}


class RL_OT_analyze(bpy.types.Operator):
    bl_idname = 'ramplab.analyze'
    bl_label = 'Analyze / Reanalyze'
    bl_description = 'Explicitly replace colors and manual edits with a new image analysis'
    bl_options = {'REGISTER','UNDO'}
    scope: EnumProperty(items=[('AUTO','Current',''),('FULL','Full Image',''),('ACTIVE','Active Region',''),
                                ('COMBINED','Combined Regions',''),('ALL','All Regions','')])

    def execute(self, context):
        settings = context.scene.ramplab
        scope = self.scope if self.scope != 'AUTO' else ('FULL' if settings.region_mode == 'FULL' else 'ACTIVE')
        wm = context.window_manager
        wm.progress_begin(0,100)
        try:
            regions = regions_for_scope(settings,scope)
            plans = []
            with read_pixels(settings.image) as pixels:
                if scope == 'ALL':
                    for i,region in enumerate(regions):
                        plans.append((region.result,'ACTIVE',region.uid,analyze(settings,'ACTIVE',[region],pixels)))
                        wm.progress_update(90*(i+1)/len(regions))
                else:
                    target = (settings.image.ramplab.full_result if scope == 'FULL' else
                              settings.image.ramplab.combined_result if scope == 'COMBINED' else regions[0].result)
                    plans.append((target,scope,regions[0].uid if scope == 'ACTIVE' else '',analyze(settings,scope,regions,pixels)))
            # Stage computations before committing: a failed region preserves all previous results.
            for target,result_scope,uid,analysis in plans:
                save_result(target,settings,result_scope,uid,analysis)
            settings.preview_scope = 'COMBINED' if scope == 'COMBINED' else 'FULL' if scope == 'FULL' else 'ACTIVE'
            if scope in {'ACTIVE','ALL'} and settings.region_mode == 'FULL':
                settings.region_mode = 'SAVED'
            warnings = sorted({warning for plan in plans for warning in plan[3][2]})
            self.report({'WARNING'} if warnings else {'INFO'},'; '.join(warnings) if warnings else f'Analyzed {len(plans)} result(s); colors and positions are editable')
            properties.redraw(context)
            return {'FINISHED'}
        except (ValueError,RuntimeError,OSError,MemoryError) as error:
            self.report({'ERROR'},str(error))
            return {'CANCELLED'}
        finally:
            wm.progress_end()


class RL_OT_generate(bpy.types.Operator):
    bl_idname = 'ramplab.generate'
    bl_label = 'Create New ColorRamp'
    bl_options = {'REGISTER','UNDO'}
    action: EnumProperty(items=[('CREATE','Create',''),('UPDATE','Update',''),('ALL','All Regions','')])

    def execute(self, context):
        settings = context.scene.ramplab
        created = []
        try:
            tree = ramp_builder.resolve_tree(context)
            target_node = ramp_builder.selected_ramp(tree) if self.action == 'UPDATE' else None
            if self.action == 'ALL':
                regions = regions_for_scope(settings,'ALL')
                missing = [r for r in regions if not properties.preview_node(r.result)]
                for region in regions:
                    if region not in missing:
                        validate_result(settings,region.result,'ACTIVE',[region])
                if missing:
                    with read_pixels(settings.image) as pixels:
                        plans = [(r,analyze(settings,'ACTIVE',[r],pixels)) for r in missing]
                    for region,analysis in plans:
                        save_result(region.result,settings,'ACTIVE',region.uid,analysis)
                outputs = [(r.name,r.uid,*validate_result(settings,r.result,'ACTIVE',[r])) for r in regions]
            else:
                result = properties.current_result(settings)
                scope = 'COMBINED' if settings.preview_scope == 'COMBINED' else 'FULL' if settings.region_mode == 'FULL' else 'ACTIVE'
                regions = regions_for_scope(settings,scope)
                stops,interpolation = validate_result(settings,result,scope,regions)
                label = regions[0].name if scope == 'ACTIVE' else 'Combined Regions' if scope == 'COMBINED' else settings.image.name
                outputs = [(label,regions[0].uid if scope == 'ACTIVE' else '',stops,interpolation)]
            for _,_,stops,_ in outputs:
                ramp_builder.validate_stops(stops)
            if target_node:
                ramp_builder.populate(target_node.color_ramp,outputs[0][2],outputs[0][3])
            else:
                right = max((n.location.x+max(n.width,200) for n in tree.nodes),default=-400)+80
                for i,(label,uid,stops,interpolation) in enumerate(outputs):
                    created.append(ramp_builder.new_ramp(tree,stops,interpolation,f'RampLab | {label}',uid,
                                                        (right+(i//4)*380,-(i%4)*340)))
                ramp_builder.select_nodes(tree,created)
                try:
                    bpy.ops.node.view_selected()
                except RuntimeError:
                    pass
            self.report({'INFO'},f'Updated selected ColorRamp' if target_node else f'Created {len(created)} ColorRamp(s)')
            return {'FINISHED'}
        except (ValueError,RuntimeError,ReferenceError) as error:
            for node in created:
                tree.nodes.remove(node)
            self.report({'ERROR'},str(error))
            return {'CANCELLED'}


CLASSES = (RL_OT_import,RL_OT_show_image,RL_OT_use_editor_image,RL_OT_analyze,RL_OT_generate)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
