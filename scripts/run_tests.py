"""Standalone tests plus optional actual Blender smoke test, with saved logs."""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
VERSION = tomllib.loads((ROOT/'ramplab'/'blender_manifest.toml').read_text())['version']


def run(command,log):
    result = subprocess.run(command,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
    log.write_text(result.stdout,encoding='utf8')
    print(result.stdout)
    if result.returncode:
        raise SystemExit(result.returncode)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--blender',default=shutil.which('blender'))
    args = parser.parse_args()
    output = ROOT/'test-results'
    output.mkdir(exist_ok=True)
    run([sys.executable,'-m','unittest','discover','-s','tests','-p','test_*.py','-v'],output/'unit-tests.txt')
    if args.blender:
        run([args.blender,'-b','--factory-startup','--python-exit-code','1','--python','tests/blender_smoke_test.py'],output/'blender-smoke.txt')
        run([args.blender,'-b','--factory-startup','--python-exit-code','1','--python','tests/blender_install_test.py'],output/'blender-install.txt')
        run([args.blender,'-b','--factory-startup','--command','extension','validate',f'dist/ramplab-{VERSION}.zip'],output/'extension-validation.txt')
    else:
        print('Blender executable unavailable: integration tests were NOT run.')


if __name__ == '__main__':
    main()
