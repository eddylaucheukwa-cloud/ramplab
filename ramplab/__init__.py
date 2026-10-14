"""RampLab: offline reference-image palettes and persistent image regions."""


def register():
    from . import properties, operators, region_operators, ui, region_overlay
    properties.register()
    operators.register()
    region_operators.register()
    ui.register()
    region_overlay.register()


def unregister():
    from . import properties, operators, region_operators, ui, region_overlay
    region_operators.cancel_all()
    region_overlay.unregister()
    ui.unregister()
    region_operators.unregister()
    operators.unregister()
    properties.unregister()
