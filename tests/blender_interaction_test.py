"""GUI runtime verification in an isolated Blender process; quits after testing.

blender --factory-startup --enable-event-simulate --python tests/blender_interaction_test.py
The timer belongs only to this test runner, not to the installed extension.
"""
from pathlib import Path
from types import SimpleNamespace
import json
import sys
import traceback
import bpy

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import ramplab
from ramplab import region_operators,region_overlay,properties,ui
from ramplab.region_geometry import normalized_to_region,mouse_to_normalized

OUT = ROOT/'test-results'
OUT.mkdir(exist_ok=True)
STATE = {}
DRAW_ERRORS = []
DRAW_CALLS = []
original_draw = region_overlay.draw


def checked_draw():
    try:
        original_draw()
        DRAW_CALLS.append(True)
    except Exception:
        DRAW_ERRORS.append(traceback.format_exc())
        raise


region_overlay.draw = checked_draw


def checked_panel(original):
    def draw(self,context):
        try:
            original(self,context)
            DRAW_CALLS.append(True)
        except Exception:
            DRAW_ERRORS.append(traceback.format_exc())
            raise
    return draw


ui.RL_PT_main.draw = checked_panel(ui.RL_PT_main.draw)
ui.RL_PT_regions.draw = checked_panel(ui.RL_PT_regions.draw)
original_draw_item = ui.RL_UL_regions.draw_item


def checked_item(self,context,layout,data,item,icon,active_data,active_propname,index):
    try:
        original_draw_item(self,context,layout,data,item,icon,active_data,active_propname,index)
    except Exception:
        DRAW_ERRORS.append(traceback.format_exc())
        raise


ui.RL_UL_regions.draw_item = checked_item


def event(region,uv,kind,value='PRESS'):
    x,y = normalized_to_region(region.view2d,uv)
    return SimpleNamespace(type=kind,value=value,mouse_x=region.x+x,mouse_y=region.y+y)


def setup():
    (OUT/'interaction.json').write_text(json.dumps({'status':'RUNNING'}))
    temporary = OUT/'gui-temp'
    temporary.mkdir(exist_ok=True)
    bpy.context.preferences.filepaths.temporary_directory = str(temporary)
    bpy.context.preferences.view.show_splash = False
    ramplab.register()
    area = max(bpy.context.screen.areas,key=lambda a:a.width*a.height)
    area.type = 'IMAGE_EDITOR'
    image = bpy.data.images.new('Interaction Red Blue',512,256,float_buffer=True)
    image.pixels.foreach_set([v for y in range(256) for x in range(512) for v in ((1,0,0,1) if x<256 else (0,0,1,1))])
    image.update()
    bpy.context.scene.ramplab.image = image
    area.spaces.active.image = image
    area.spaces.active.show_region_ui = True
    STATE.update(area=area,image=image,stage=0)
    area.tag_redraw()


def step():
    try:
        area = STATE['area']
        region = next(r for r in area.regions if r.type == 'WINDOW')
        with bpy.context.temp_override(area=area,region=region):
            stage = STATE['stage']
            image = bpy.context.scene.ramplab.image
            if stage == 0:
                next(r for r in area.regions if r.type == 'UI').active_panel_category = 'RampLab Regions'
                bpy.ops.image.view_all(fit_view=True)
            elif stage == 1:
                for uv in [(0,0),(.25,.75),(1,1)]:
                    back = mouse_to_normalized(region.view2d,*normalized_to_region(region.view2d,uv))
                    assert max(abs(a-b) for a,b in zip(uv,back)) < .015,(uv,back)
                assert bpy.ops.ramplab.rectangle_select('INVOKE_DEFAULT') == {'RUNNING_MODAL'}
                op = region_operators._running[area.as_pointer()]
                assert bpy.ops.ramplab.rectangle_select('INVOKE_DEFAULT') == {'CANCELLED'}
                assert op.modal(bpy.context,event(region,(.45,.9),'LEFTMOUSE')) == {'RUNNING_MODAL'}
                op.modal(bpy.context,event(region,(.05,.1),'MOUSEMOVE','NOTHING'))
                assert op.modal(bpy.context,event(region,(.05,.1),'LEFTMOUSE','RELEASE')) == {'FINISHED'}
                assert len(image.ramplab.regions) == 1
                assert not region_operators._running and not region_overlay._sessions
                assert bpy.ops.ramplab.analyze(scope='ACTIVE') == {'FINISHED'}
                assert all(e.color[0] > .99 and e.color[2] < 1e-5 for e in properties.preview_node(image.ramplab.regions[0].result).color_ramp.elements)
                assert bpy.ops.ramplab.polygon_select('INVOKE_DEFAULT') == {'RUNNING_MODAL'}
                op = region_operators._running[area.as_pointer()]
                for uv in [(.55,.1),(.75,.1),(.75,.9),(.55,.9)]:
                    op.modal(bpy.context,event(region,uv,'LEFTMOUSE'))
                op.modal(bpy.context,event(region,(.55,.9),'BACK_SPACE'))
                assert len(op.session.vertices) == 3
                op.modal(bpy.context,event(region,(.55,.9),'LEFTMOUSE'))
                assert op.modal(bpy.context,event(region,(.55,.9),'RET')) == {'FINISHED'}
                assert len(image.ramplab.regions) == 2
                assert bpy.ops.ramplab.analyze(scope='ACTIVE') == {'FINISHED'}
                assert all(e.color[2] > .99 and e.color[0] < 1e-5 for e in properties.preview_node(image.ramplab.regions[1].result).color_ramp.elements)
                # Cancellation does not change persistent selections.
                assert bpy.ops.ramplab.polygon_select('INVOKE_DEFAULT') == {'RUNNING_MODAL'}
                op = region_operators._running[area.as_pointer()]
                op.modal(bpy.context,event(region,(.2,.2),'LEFTMOUSE'))
                assert op.modal(bpy.context,event(region,(.2,.2),'ESC')) == {'CANCELLED'}
                assert len(image.ramplab.regions) == 2
                STATE['uv_before'] = [tuple(p.uv) for p in image.ramplab.regions[0].points]
                bpy.ops.image.view_zoom_ratio(ratio=2.)
                bpy.ops.image.view_pan(offset=(70,-40))
            elif stage == 2:
                assert [tuple(p.uv) for p in image.ramplab.regions[0].points] == STATE['uv_before']
                for uv in [(.25,.25),(.75,.75)]:
                    back = mouse_to_normalized(region.view2d,*normalized_to_region(region.view2d,uv))
                    assert max(abs(a-b) for a,b in zip(uv,back)) < .015
                bpy.ops.image.view_all(fit_view=True)
                bpy.ops.ramplab.analyze(scope='COMBINED')
                image.ramplab.active_index = 0
                assert bpy.context.scene.ramplab.preview_scope == 'ACTIVE'
                # Start a live preview to ensure the draw callback renders transient geometry.
                bpy.ops.ramplab.rectangle_select('INVOKE_DEFAULT')
                op = region_operators._running[area.as_pointer()]
                op.modal(bpy.context,event(region,(.3,.3),'LEFTMOUSE'))
                op.modal(bpy.context,event(region,(.7,.7),'MOUSEMOVE','NOTHING'))
            elif stage == 3:
                bpy.ops.screen.screenshot(filepath=str(OUT/'region-overlay.png'))
                region_operators.cancel_all()
                assert not region_overlay._sessions
                # Switching editor type while a selection runs cancels it.
                bpy.ops.ramplab.polygon_select('INVOKE_DEFAULT')
                op = region_operators._running[area.as_pointer()]
                area.type = 'NODE_EDITOR'
                assert op.modal(bpy.context,event(region,(.2,.2),'MOUSEMOVE')) == {'CANCELLED'}
                assert not region_operators._running
                area.spaces.active.tree_type = 'ShaderNodeTree'
                area.spaces.active.show_region_ui = True
                material = bpy.data.materials.new('Interaction Material')
                material.use_nodes = True
                bpy.context.object.active_material = material
            elif stage == 4:
                next(r for r in area.regions if r.type == 'UI').active_panel_category = 'RampLab'
                bpy.ops.ed.undo_push(message='RampLab before generation')
                assert bpy.ops.ramplab.generate(action='ALL') == {'FINISHED'}
                bpy.ops.ed.undo_push(message='RampLab after generation')
                assert len([n for n in bpy.context.object.active_material.node_tree.nodes if n.bl_idname=='ShaderNodeValToRGB']) == 2
                bpy.ops.ed.undo()
                assert len([n for n in bpy.context.object.active_material.node_tree.nodes if n.bl_idname=='ShaderNodeValToRGB']) == 0
                bpy.ops.ed.redo()
                assert len([n for n in bpy.context.object.active_material.node_tree.nodes if n.bl_idname=='ShaderNodeValToRGB']) == 2
            elif stage == 5:
                bpy.ops.screen.screenshot(filepath=str(OUT/'shader-panel.png'))
                assert DRAW_CALLS,'GPU overlay callback never ran'
                assert not DRAW_ERRORS,DRAW_ERRORS
                ramplab.unregister()
                assert region_overlay._handler is None
                assert not region_operators._running
                (OUT/'interaction.json').write_text(json.dumps({'status':'PASS','blender':bpy.app.version_string,
                    'checks':['real View2D roundtrip/zoom','rectangle reverse drag','polygon/backspace',
                              'red/blue separation','cancel','duplicate invocation','editor switch',
                              'live GPU overlay','UI drawing','generate/undo/redo','unregister']},indent=2))
                bpy.ops.wm.quit_blender()
                return None
            STATE['stage'] += 1
        return .6
    except Exception:
        (OUT/'interaction.json').write_text(json.dumps({'status':'FAIL','stage':STATE.get('stage'),
            'traceback':traceback.format_exc()},indent=2))
        traceback.print_exc()
        try:
            ramplab.unregister()
        finally:
            bpy.ops.wm.quit_blender()
        return None


try:
    setup()
    bpy.app.timers.register(step,first_interval=1.)
except Exception:
    (OUT/'interaction.json').write_text(json.dumps({'status':'FAIL','stage':'setup','traceback':traceback.format_exc()}))
    traceback.print_exc()
    bpy.ops.wm.quit_blender()
