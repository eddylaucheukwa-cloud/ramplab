"""Image Editor rectangle/polygon modal tools and persistent region management."""
import colorsys
import uuid
import bpy
from bpy.app.handlers import persistent
from bpy.props import EnumProperty
from . import properties, region_overlay
from .operators import remove_result
from .image_sampling import image_path
from .region_geometry import rectangle, polygon, clamp_point, mouse_to_normalized, MAX_VERTICES

_running = {}


def add_region(image, kind, vertices):
    vertices = rectangle(vertices[0],vertices[2]) if kind == 'RECT' else polygon(vertices)
    data = image.ramplab
    region = data.regions.add()
    region.uid = uuid.uuid4().hex
    region.name = f'{"Rectangle" if kind == "RECT" else "Polygon"} {len(data.regions)}'
    region.kind = kind
    region.width,region.height = image.size
    region.source_path = image_path(image)
    region.color = colorsys.hsv_to_rgb((len(data.regions)*.61803398875) % 1,.65,.95)
    for point in vertices:
        region.points.add().uv = point
    data.active_index = len(data.regions)-1
    image.use_fake_user = True
    return region


class SelectionSession:
    """Pure interaction state; RNA is changed only after valid completion."""
    def __init__(self, kind):
        self.kind = kind
        self.start = None
        self.mouse = (0.,0.)
        self.vertices = []

    def press(self, point):
        self.mouse = clamp_point(point)
        if self.kind == 'RECT':
            self.start = self.mouse
        elif not self.vertices or self.vertices[-1] != self.mouse:
            if len(self.vertices) >= MAX_VERTICES:
                raise ValueError(f'Polygon vertex limit is {MAX_VERTICES}; press Enter to finish')
            self.vertices.append(self.mouse)

    def move(self, point):
        self.mouse = clamp_point(point)

    def backspace(self):
        if self.vertices:
            self.vertices.pop()

    def finish(self):
        if self.kind == 'RECT':
            if self.start is None:
                raise ValueError('Click and drag across the image first')
            return rectangle(self.start,self.mouse)
        return polygon(self.vertices)

    def preview(self):
        if self.kind == 'RECT':
            if self.start is None:
                return [],False
            x0,y0 = self.start
            x1,y1 = self.mouse
            return [(x0,y0),(x1,y0),(x1,y1),(x0,y1)],True
        return self.vertices+[self.mouse],False


class SelectionModal:
    bl_options = {'REGISTER','UNDO','BLOCKING'}
    kind = 'RECT'
    stopped = True

    @classmethod
    def poll(cls, context):
        return context.area and context.area.type == 'IMAGE_EDITOR' and context.scene.ramplab.image is not None

    def invoke(self, context, event):
        settings = context.scene.ramplab
        image = settings.image
        if context.space_data.image != image:
            self.report({'ERROR'},'Click Show Reference Here before selecting a region')
            return {'CANCELLED'}
        if not image.is_editable or image.source not in {'FILE','GENERATED'} or min(image.size) <= 0:
            self.report({'ERROR'},'Select a readable, local still image first')
            return {'CANCELLED'}
        area_key = context.area.as_pointer()
        if area_key in _running:
            self.report({'WARNING'},'A RampLab selection is already running in this editor')
            return {'CANCELLED'}
        self.area = context.area
        self.region = next((r for r in self.area.regions if r.type == 'WINDOW'),None)
        if self.region is None:
            return {'CANCELLED'}
        self.window = context.window
        self.image = image
        self.image_size = tuple(image.size)
        self.source_path = image_path(image)
        self.settings = settings
        self.session = SelectionSession(self.kind)
        self.stopped = False
        _running[area_key] = self
        region_overlay._sessions[area_key] = self
        self.window.cursor_modal_set('CROSSHAIR')
        self.area.header_text_set('RampLab: drag LMB to select · Esc cancels' if self.kind == 'RECT' else
                                  'RampLab: click vertices · Enter/double-click finishes · Backspace removes · Esc cancels')
        self.area.tag_redraw()
        context.window_manager.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def preview(self):
        return self.session.preview()

    def cleanup(self):
        if self.stopped:
            return
        self.stopped = True
        try:
            key = self.area.as_pointer()
            _running.pop(key,None)
            region_overlay._sessions.pop(key,None)
            self.area.header_text_set(None)
            self.area.tag_redraw()
            self.window.cursor_modal_restore()
        except ReferenceError:
            # Area/window may have disappeared during a workspace/file change.
            for key,value in list(_running.items()):
                if value == self:
                    _running.pop(key,None)
                    region_overlay._sessions.pop(key,None)

    def cancel(self, context):
        self.cleanup()

    def modal(self, context, event):
        if self.stopped:
            return {'CANCELLED'}
        try:
            if (context.area != self.area or self.area.type != 'IMAGE_EDITOR' or
                    self.area.spaces.active.image != self.image or self.settings.image != self.image or
                    tuple(self.image.size) != self.image_size or image_path(self.image) != self.source_path):
                self.cleanup()
                return {'CANCELLED'}
            if event.type in {'ESC','RIGHTMOUSE'}:
                self.cleanup()
                return {'CANCELLED'}
            x,y = event.mouse_x-self.region.x,event.mouse_y-self.region.y
            point = mouse_to_normalized(self.region.view2d,x,y)
            self.session.move(point)
            self.area.tag_redraw()
            if event.type == 'MOUSEMOVE':
                return {'RUNNING_MODAL'}
            if event.type == 'BACK_SPACE' and event.value == 'PRESS':
                self.session.backspace()
            if event.type == 'LEFTMOUSE' and event.value == 'PRESS':
                # Ignore presses on the sidebar or outside the Image Editor viewport.
                if not (0 <= x < self.region.width and 0 <= y < self.region.height):
                    return {'RUNNING_MODAL'}
                if any(r.type in {'UI','TOOLS'} and r.width > 1 and
                       r.x <= event.mouse_x < r.x+r.width and r.y <= event.mouse_y < r.y+r.height
                       for r in self.area.regions):
                    return {'RUNNING_MODAL'}
                self.session.press(point)
            finish = ((self.kind == 'RECT' and self.session.start is not None and event.type == 'LEFTMOUSE' and event.value == 'RELEASE') or
                      (self.kind == 'POLYGON' and ((event.type in {'RET','NUMPAD_ENTER'} and event.value == 'PRESS') or
                                                   (event.type == 'LEFTMOUSE' and event.value == 'DOUBLE_CLICK'))))
            if finish:
                try:
                    vertices = self.session.finish()
                except ValueError as error:
                    self.report({'WARNING'},str(error))
                    if self.kind == 'RECT':
                        self.session.start = None
                    return {'RUNNING_MODAL'}
                add_region(self.image,self.kind,vertices)
                self.settings.region_mode = 'RECT' if self.kind == 'RECT' else 'POLYGON'
                self.settings.preview_scope = 'ACTIVE'
                self.cleanup()
                return {'FINISHED'}
            if event.type in {'MIDDLEMOUSE','WHEELUPMOUSE','WHEELDOWNMOUSE','TRACKPADPAN','TRACKPADZOOM','NDOF_MOTION'}:
                return {'PASS_THROUGH'}
            return {'RUNNING_MODAL'}
        except ValueError as error:
            self.report({'WARNING'},str(error))
            return {'RUNNING_MODAL'}
        except (ReferenceError,RuntimeError) as error:
            self.cleanup()
            self.report({'ERROR'},str(error))
            return {'CANCELLED'}


class RL_OT_rectangle(SelectionModal,bpy.types.Operator):
    bl_idname = 'ramplab.rectangle_select'
    bl_label = 'Rectangle Select'
    kind = 'RECT'


class RL_OT_polygon(SelectionModal,bpy.types.Operator):
    bl_idname = 'ramplab.polygon_select'
    bl_label = 'Polygon Select'
    kind = 'POLYGON'


class RL_OT_region_manage(bpy.types.Operator):
    bl_idname = 'ramplab.region_manage'
    bl_label = 'Manage Regions'
    bl_options = {'REGISTER','UNDO'}
    action: EnumProperty(items=[('DELETE','Delete Region',''),('CLEAR','Clear All Regions',''),
                                ('PREVIEW','Preview Active Region','')])

    def execute(self, context):
        settings = context.scene.ramplab
        image = settings.image
        if not image or not image.is_editable:
            self.report({'ERROR'},'Select a local reference image first')
            return {'CANCELLED'}
        data = image.ramplab
        if self.action == 'PREVIEW':
            settings.preview_scope = 'ACTIVE'
            if settings.region_mode == 'FULL':
                settings.region_mode = 'SAVED'
        elif self.action == 'CLEAR':
            for region in data.regions:
                remove_result(region.result)
            data.regions.clear()
            remove_result(data.combined_result)
            data.active_index = 0
            settings.preview_scope = 'ACTIVE'
        else:
            region = properties.active_region(image)
            if not region:
                self.report({'ERROR'},'No active region')
                return {'CANCELLED'}
            remove_result(region.result)
            data.regions.remove(data.active_index)
            data.active_index = max(0,min(data.active_index,len(data.regions)-1))
            settings.preview_scope = 'ACTIVE'
        properties.redraw(context)
        return {'FINISHED'}


def cancel_all():
    for operator in list(_running.values()):
        operator.cleanup()
    _running.clear()
    region_overlay._sessions.clear()


@persistent
def before_load(_):
    cancel_all()


CLASSES = (RL_OT_rectangle,RL_OT_polygon,RL_OT_region_manage)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.app.handlers.load_pre.append(before_load)


def unregister():
    cancel_all()
    if before_load in bpy.app.handlers.load_pre:
        bpy.app.handlers.load_pre.remove(before_load)
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
