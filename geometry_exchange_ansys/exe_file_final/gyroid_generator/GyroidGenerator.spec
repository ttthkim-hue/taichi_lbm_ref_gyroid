# -*- mode: python ; coding: utf-8 -*-
# onedir 모드: DLL을 폴더에 직접 배치하여 OCCT DLL 로딩 안정화

import os

from PyInstaller.utils.hooks import collect_all

_spec_dir = os.path.dirname(os.path.abspath(SPEC))

ocp_datas = []
ocp_binaries = []
ocp_hiddenimports = []
try:
    _d, _b, _h = collect_all("OCP")
    ocp_datas = list(_d)
    ocp_binaries = list(_b)
    ocp_hiddenimports = list(_h)
except Exception:
    pass

hiddenimports = [
    "skimage.measure",
    "skimage.measure._marching_cubes_lewiner",
    "trimesh",
    "trimesh.exchange",
    "manifold3d",
    "numpy",
    "scipy",
    "scipy.ndimage",
] + ocp_hiddenimports

# onedir에서는 DLL이 같은 폴더에 있으므로 runtime hook 불필요
runtime_hooks = []

a = Analysis(
    ["gyroid_gui.py"],
    pathex=[_spec_dir],
    binaries=ocp_binaries,
    datas=ocp_datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=runtime_hooks,
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="GyroidGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="GyroidGenerator",
)
