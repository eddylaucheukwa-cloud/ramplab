"""Install the delivered ZIP into a temporary Blender extension repository."""
from pathlib import Path
import tempfile
import bpy
import addon_utils
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT/'ramplab'/'blender_manifest.toml').read_text())['version']

with tempfile.TemporaryDirectory(prefix='ramplab-install-') as directory:
    bpy.context.preferences.use_preferences_save = False
    repo = bpy.context.preferences.extensions.repos.new(name='RampLab temporary verification',
        module='ramplab_verify',custom_directory=directory)
    try:
        result = bpy.ops.extensions.package_install_files(repo=repo.module,
            filepath=str(ROOT/'dist'/f'ramplab-{VERSION}.zip'),enable_on_install=True)
        assert result == {'FINISHED'},result
        module_name = 'bl_ext.ramplab_verify.ramplab'
        assert addon_utils.check(module_name)[1],addon_utils.check(module_name)
        assert hasattr(bpy.types.Scene,'ramplab')
        image = bpy.data.images.new('Installed ZIP Image',2,2,float_buffer=True)
        image.pixels.foreach_set([1,0,0,1]*4)
        bpy.context.scene.ramplab.image = image
        assert bpy.ops.ramplab.analyze(scope='FULL') == {'FINISHED'}
        addon_utils.disable(module_name,default_set=True)
        assert not hasattr(bpy.types.Scene,'ramplab')
        print('RAMPLAB_ZIP_INSTALL_PASS',bpy.app.version_string)
    finally:
        bpy.context.preferences.extensions.repos.remove(repo)
