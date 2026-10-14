"""Build a reproducible modern-extension ZIP with the manifest at archive root."""
from pathlib import Path
import hashlib
import zipfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]


def build():
    source = ROOT/'ramplab'
    manifest = tomllib.loads((source/'blender_manifest.toml').read_text(encoding='utf8'))
    destination = ROOT/'dist'/f'ramplab-{manifest["version"]}.zip'
    destination.parent.mkdir(exist_ok=True)
    files = sorted(p for p in source.iterdir() if p.is_file() and p.suffix in {'.py','.toml','.md','.txt'})
    assert (source/'__init__.py') in files
    with zipfile.ZipFile(destination,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for file in files:
            info = zipfile.ZipInfo(file.name,date_time=(2026,10,13,0,0,0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info,file.read_bytes())
    with zipfile.ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert {'blender_manifest.toml','__init__.py','README.md','LICENSE.txt'} <= set(archive.namelist())
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    (destination.parent/(destination.name+'.sha256')).write_text(f'{digest}  {destination.name}\n')
    print(f'{destination}\nSHA256 {digest}')
    return destination


if __name__ == '__main__':
    build()
