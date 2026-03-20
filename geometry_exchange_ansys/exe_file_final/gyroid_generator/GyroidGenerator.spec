# -*- mode: python ; coding: utf-8 -*-
# STEP: 빌드 환경에 cadquery(→OCP) 설치 후 PyInstaller 실행 (CI / build_windows.bat)

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

runtime_hooks = [os.path.join(_spec_dir, "pyi_rth_gyroid_ocp.py")]

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
    a.binaries,
    a.datas,
    [],
    name="GyroidGenerator",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
