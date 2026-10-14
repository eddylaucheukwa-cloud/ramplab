"""Region persistence/masking are included in the common Blender smoke runner."""
from pathlib import Path
import runpy

if __name__ == '__main__':
    runpy.run_path(str(Path(__file__).with_name('blender_smoke_test.py')),run_name='__main__')
