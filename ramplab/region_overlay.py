"""One native Image Editor overlay handler; no background redraw timers."""
import bpy
from . import properties
from .region_geometry import normalized_to_region
from .image_sampling import image_path

_handler = None
_sessions = {}


def draw_shape(view2d, vertices, color, active=False, closed=True, fill=True):
    if len(vertices) < 2:
        return
    import gpu
    from gpu_extras.batch import batch_for_shader
    from mathutils import Vector
    from mathutils.geometry import tessellate_polygon
    points = [normalized_to_region(view2d,p) for p in vertices]
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    shader.bind()
    if closed and fill and len(points) >= 3:
        triangles = tessellate_polygon([[Vector((x,y,0)) for x,y in points]])
        if triangles:
            # 4.5 returns Vectors; newer mathutils returns flattened vertex indices.
            coords = [points[v] if isinstance(v,int) else (v.x,v.y) for triangle in triangles for v in triangle]
            shader.uniform_float('color',(*color,.20 if active else .08))
            batch_for_shader(shader,'TRIS',{'pos':coords}).draw(shader)
    shader.uniform_float('color',(*color,1. if active else .65))
    gpu.state.line_width_set(2. if active else 1.)
    batch_for_shader(shader,'LINE_STRIP',{'pos':points+[points[0]] if closed else points}).draw(shader)
    gpu.state.point_size_set(5. if active else 3.)
    batch_for_shader(shader,'POINTS',{'pos':points}).draw(shader)


def draw():
    context = bpy.context
    if not context.area or context.area.type != 'IMAGE_EDITOR' or not context.region or context.region.type != 'WINDOW':
        return
    settings = context.scene.ramplab
    image = settings.image
    if not image or context.space_data.image != image:
        return
    import gpu
    previous_blend = gpu.state.blend_get()
    previous_width = gpu.state.line_width_get()
    try:
        gpu.state.blend_set('ALPHA')
        if settings.show_overlay:
            for i,region in enumerate(image.ramplab.regions):
                if region.visible and (region.width,region.height) == tuple(image.size) and region.source_path == image_path(image):
                    draw_shape(context.region.view2d,[tuple(p.uv) for p in region.points],tuple(region.color),
                               active=i == image.ramplab.active_index)
        session = _sessions.get(context.area.as_pointer())
        if session and not session.stopped:
            vertices,closed = session.preview()
            draw_shape(context.region.view2d,vertices,(1.,.65,.15),active=True,closed=closed,fill=closed)
    finally:
        gpu.state.blend_set(previous_blend)
        gpu.state.line_width_set(previous_width)
        gpu.state.point_size_set(1.)


def register():
    global _handler
    if _handler is None:
        _handler = bpy.types.SpaceImageEditor.draw_handler_add(draw,(),'WINDOW','POST_PIXEL')


def unregister():
    global _handler
    _sessions.clear()
    if _handler is not None:
        bpy.types.SpaceImageEditor.draw_handler_remove(_handler,'WINDOW')
        _handler = None
