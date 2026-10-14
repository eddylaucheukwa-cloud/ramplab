"""Validated, undo-friendly edits to native ColorRamp nodes."""
import math
import bpy


def validate_stops(stops):
    if not stops or len(stops) > 8:
        raise ValueError('Analyze a palette with 1–8 colors first')
    positions = []
    for color, position in stops:
        if len(color) != 4 or not all(math.isfinite(v) and 0 <= v <= 1 for v in color):
            raise ValueError('Ramp colors must be finite RGBA values in [0,1]')
        if not math.isfinite(position) or not 0 <= position <= 1:
            raise ValueError('Stop positions must lie in [0,1]')
        positions.append(position)
    if any(b-a < 1e-6 for a,b in zip(sorted(positions),sorted(positions)[1:])):
        raise ValueError('Separate coincident ramp stops before generating')
    return sorted(stops,key=lambda stop: stop[1])


def populate(ramp, stops, interpolation):
    stops = validate_stops(stops)
    if interpolation not in {'CONSTANT','LINEAR','EASE'}:
        raise ValueError('Unsupported interpolation')
    while len(ramp.elements) > 2:
        ramp.elements.remove(ramp.elements[-1])
    # Blender requires at least two elements. A solid result is duplicated at 0/1.
    if len(stops) == 1:
        stops = [(stops[0][0],0.),(stops[0][0],1.)]
    ramp.elements[0].position = 0.
    ramp.elements[1].position = 1.
    ramp.elements[0].color = stops[0][0]
    ramp.elements[0].position = stops[0][1]
    ramp.elements[1].color = stops[-1][0]
    ramp.elements[1].position = stops[-1][1]
    for color,position in stops[1:-1]:
        element = ramp.elements.new(position)
        element.color = color
    ramp.interpolation = interpolation
    ramp.color_mode = 'RGB'


def resolve_tree(context):
    space = context.space_data
    if not space or space.type != 'NODE_EDITOR' or space.tree_type != 'ShaderNodeTree':
        raise ValueError('Run this action in a material Shader Editor')
    if space.shader_type != 'OBJECT':
        raise ValueError('Switch the Shader Editor to an object material')
    material = space.id if isinstance(space.id,bpy.types.Material) else getattr(context,'material',None)
    if material is None and not space.pin and context.object:
        material = context.object.active_material
    if not material or not material.use_nodes or not material.node_tree:
        raise ValueError('Create or select a material with Use Nodes enabled first')
    tree = space.edit_tree or material.node_tree
    if not tree or tree.bl_idname != 'ShaderNodeTree' or not tree.is_editable:
        raise ValueError('The current material shader node tree is not editable')
    return tree


def selected_ramp(tree):
    node = tree.nodes.active
    selected = [n for n in tree.nodes if n.select]
    if not node or not node.select or node.bl_idname != 'ShaderNodeValToRGB' or selected != [node]:
        raise ValueError('Select exactly one ColorRamp node and make it active')
    return node


def new_ramp(tree, stops, interpolation, label, region_id='', location=None):
    validate_stops(stops)
    node = tree.nodes.new('ShaderNodeValToRGB')
    try:
        node.label = label
        node.width = 300
        node['ramplab_region_id'] = region_id
        node['ramplab_generated'] = True
        if location is None:
            right = max((n.location.x+max(n.width,200) for n in tree.nodes if n != node),default=-400)
            location = (right+80,0)
        node.location = location
        populate(node.color_ramp,stops,interpolation)
    except Exception:
        tree.nodes.remove(node)
        raise
    return node


def select_nodes(tree, nodes):
    for node in tree.nodes:
        node.select = node in nodes
    if nodes:
        tree.nodes.active = nodes[0]
