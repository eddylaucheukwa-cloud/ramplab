"""Run with blender -b --factory-startup --python tests/blender_smoke_test.py."""
from pathlib import Path
import sys
import tempfile
import json

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import bpy
import ramplab
from ramplab import properties, operators, region_operators, region_overlay, ramp_builder
from ramplab.region_geometry import rectangle
from ramplab.image_sampling import extract_region_samples


def run():
    ramplab.register()
    image = bpy.data.images.new('RampLab Red Blue',width=32,height=16,float_buffer=True)
    image.filepath = str(Path(tempfile.gettempdir())/'ramplab-smoke-reference.png')
    data = [v for y in range(16) for x in range(32) for v in ((1,0,0,1) if x<16 else (0,0,1,1))]
    image.pixels.foreach_set(data)
    image.update()
    settings = bpy.context.scene.ramplab
    settings.image = image
    # Exercise both pixel storage paths without allocating a genuinely huge test image.
    from unittest.mock import patch
    from ramplab import image_sampling
    with patch.object(image_sampling,'HEAP_BUFFER_LIMIT',0):
        assert len(extract_region_samples(image)[0]) == 32*16
    linear_test = bpy.data.images.new('Linear middle gray',1,1,float_buffer=True)
    linear_test.pixels.foreach_set([.5,.5,.5,1])
    assert extract_region_samples(linear_test)[0][0] == (.5,.5,.5)
    red = region_operators.add_region(image,'RECT',rectangle((0,0),(.5,1)))
    red.name = 'Red Left'
    blue = region_operators.add_region(image,'POLYGON',[(.5,0),(1,0),(1,1),(.5,1)])
    blue.name = 'Blue Right'
    # Changed dimensions/path must warn instead of silently reusing selections.
    red.width += 1
    try:
        operators.validate_region(image,red)
    except ValueError:
        pass
    else:
        raise AssertionError('Resized image region must be rejected')
    red.width -= 1
    original_nodes = set(bpy.context.object.active_material.node_tree.nodes[:]) if bpy.context.object.active_material else set()
    for mode in ['DOMINANT','TONAL']:
        settings.mode = mode
        assert bpy.ops.ramplab.analyze(scope='FULL') == {'FINISHED'}
        assert bpy.ops.ramplab.analyze(scope='ALL') == {'FINISHED'}
        assert bpy.ops.ramplab.analyze(scope='COMBINED') == {'FINISHED'}
        for region,axis in [(red,0),(blue,2)]:
            colors = [e.color for e in properties.preview_node(region.result).color_ramp.elements]
            assert all(c[axis] > .99 and c[2-axis] < 1e-5 for c in colors),list(colors)
    settings.mode = 'DOMINANT'
    settings.region_mode = 'SAVED'
    settings.preview_scope = 'ACTIVE'
    assert bpy.ops.ramplab.analyze(scope='ALL') == {'FINISHED'}
    area = bpy.context.screen.areas[0]
    previous_type = area.type
    area.type = 'NODE_EDITOR'
    space = area.spaces.active
    space.tree_type = 'ShaderNodeTree'
    space.shader_type = 'OBJECT'
    material = bpy.data.materials.new('RampLab Smoke')
    material.use_nodes = True
    bpy.context.object.active_material = material
    tree = material.node_tree
    constant = tree.nodes.new('ShaderNodeValToRGB')
    ramp_builder.populate(constant.color_ramp,[((1,0,0,1),0),((0,1,0,1),.6),((0,0,1,1),.9)],'CONSTANT')
    for value,expected in [(.2,(1,0,0)),(.6001,(0,1,0)),(.99,(0,0,1))]:
        assert tuple(constant.color_ramp.evaluate(value))[:3] == expected
    tree.nodes.remove(constant)
    before_nodes = len(tree.nodes)
    before_links = [(link.from_node.name,link.to_node.name) for link in tree.links]
    with bpy.context.temp_override(area=area,region=next(r for r in area.regions if r.type=='WINDOW')):
        assert bpy.ops.ramplab.generate(action='ALL') == {'FINISHED'}
        ramps = [n for n in tree.nodes if n.bl_idname == 'ShaderNodeValToRGB']
        assert len(ramps) == 2
        assert len(tree.nodes) == before_nodes+2
        assert len({n['ramplab_region_id'] for n in ramps}) == 2
        assert len({tuple(n.location) for n in ramps}) == 2
        assert [(l.from_node.name,l.to_node.name) for l in tree.links] == before_links
        image.ramplab.active_index = 0
        result = red.result
        preview = properties.preview_node(result)
        preview.color_ramp.elements[0].color = (.15,.25,.35,1)
        settings.interpolation = 'EASE'
        assert preview.color_ramp.interpolation == 'EASE'
        ramp_builder.select_nodes(tree,[ramps[0]])
        assert bpy.ops.ramplab.generate(action='UPDATE') == {'FINISHED'}
        assert tuple(ramps[0].color_ramp.elements[0].color) == tuple(preview.color_ramp.elements[0].color)
        assert ramps[0].color_ramp.interpolation == 'EASE'
        assert len(tree.nodes) == before_nodes+2
        ramp_builder.select_nodes(tree,[])
        try:
            bpy.ops.ramplab.generate(action='UPDATE')
        except RuntimeError:
            pass
        else:
            raise AssertionError('No selection must be rejected')
        ramp_builder.select_nodes(tree,[next(n for n in tree.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')])
        try:
            bpy.ops.ramplab.generate(action='UPDATE')
        except RuntimeError:
            pass
        else:
            raise AssertionError('Wrong node must be rejected')
        settings.color_count = 6
        try:
            operators.validate_result(settings,red.result,'ACTIVE',[red])
        except ValueError:
            pass
        else:
            raise AssertionError('Stale result must be rejected')
        settings.color_count = 5
        assert bpy.ops.ramplab.generate(action='CREATE') == {'FINISHED'}
        assert len(tree.nodes) == before_nodes+3
        # Blender 5.1 always enables material nodes; test the stable no-material case.
        from types import SimpleNamespace
        empty_context = SimpleNamespace(space_data=SimpleNamespace(type='NODE_EDITOR',
            tree_type='ShaderNodeTree',shader_type='OBJECT',id=None,pin=False),material=None,object=None)
        try:
            ramp_builder.resolve_tree(empty_context)
        except ValueError:
            pass
        else:
            raise AssertionError('Missing material must be rejected')
    area.type = previous_type
    with tempfile.TemporaryDirectory() as temp:
        path = str(Path(temp)/'regions.blend')
        uid = red.uid
        geometry = [tuple(p.uv) for p in red.points]
        # Packed still image exercises byte sRGB decoding and native datablock loading.
        png = str(Path(temp)/'reference.png')
        byte_source = bpy.data.images.new('Byte test',1,1,float_buffer=False)
        byte_source.pixels[:] = (.5,.5,.5,1)
        byte_source.filepath_raw = png
        byte_source.file_format = 'PNG'
        byte_source.save()
        loaded = bpy.data.images.load(png,check_existing=False)
        loaded.pack()
        rgb,_ = extract_region_samples(loaded)
        assert abs(rgb[0][0]-.21586) < .003,rgb
        image.pack()
        bpy.ops.wm.save_as_mainfile(filepath=path)
        bpy.ops.wm.open_mainfile(filepath=path)
        restored = bpy.context.scene.ramplab.image
        assert len(restored.ramplab.regions) == 2
        assert restored.ramplab.regions[0].uid == uid
        assert [tuple(p.uv) for p in restored.ramplab.regions[0].points] == geometry
        assert properties.preview_node(restored.ramplab.regions[0].result)
        operators.validate_region(restored,restored.ramplab.regions[0])
        # Saved relative paths must keep the same result signature and geometry.
        assert restored.ramplab.regions[0].source_path == image_sampling.image_path(restored)
        operators.validate_result(bpy.context.scene.ramplab,restored.ramplab.regions[0].result,
                                  'ACTIVE',[restored.ramplab.regions[0]])
    assert region_overlay._handler is not None
    ramplab.unregister()
    assert region_overlay._handler is None
    assert not region_overlay._sessions and not region_operators._running
    assert region_operators.before_load not in bpy.app.handlers.load_pre
    assert not hasattr(bpy.types.Scene,'ramplab')
    assert not hasattr(bpy.types.Image,'ramplab')
    ramplab.register()
    ramplab.unregister()
    print('RAMPLAB_BLENDER_SMOKE_PASS',bpy.app.version_string)


if __name__ == '__main__':
    run()
