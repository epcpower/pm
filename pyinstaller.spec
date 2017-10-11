# -*- mode: python -*-

import os
import pathlib


def collect(prefix, search_in, *extensions):
    for dir_name, subdirs, files in os.walk(search_in):
        for filename in (f for f in files if f.endswith(extensions)):
            filename = pathlib.Path(dir_name, filename)
            yield (filename, pathlib.Path(dir_name).relative_to(prefix))


data_files = []

name = 'epcpm'

prefix = pathlib.Path('src', name)
search_in = prefix
data_files.extend(collect(prefix, search_in, '.ui', '.ico', '.png'))


a = Analysis(
    [str(pathlib.Path('src', name, '__main__.py'))],
    pathex=['..'],
    binaries=[],
    datas=[(str(pathlib.Path(p).resolve()), pp) for p, pp in data_files],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name=name,
    debug=False,
    strip=False,
    upx=True,
    console=True,
    icon=str(pathlib.Path('src', name, 'icon.ico')),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name=name,
)