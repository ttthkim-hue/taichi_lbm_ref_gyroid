# -*- mode: python ; coding: utf-8 -*-
# onedir 모드 + step_converter를 별도 exe로 빌드

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

# ── 메인 GUI (OCP 불필요 — STL만 담당) ──
gui_hiddenimports = [
    "skimage.measure",
    "skimage.measure._marching_cubes_lewiner",
    "trimesh",
    "trimesh.exchange",
    "trimesh.intersections",
    "trimesh.path",
    "trimesh.path.polygons",
    "manifold3d",
    "shapely",
    "shapely.ops",
    "rtree",
    "numpy",
    "scipy",
    "scipy.ndimage",
]

gui_analysis = Analysis(
    ["gyroid_gui.py"],
    pathex=[_spec_dir],
    binaries=[],
    datas=[],
    hiddenimports=gui_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
gui_pyz = PYZ(gui_analysis.pure)

gui_exe = EXE(
    gui_pyz,
    gui_analysis.scripts,
    [],
    exclude_binaries=True,
    name="GyroidGenerator",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

# ── STEP 변환기 (OCP 포함) ──
step_hiddenimports = gui_hiddenimports + ocp_hiddenimports

step_analysis = Analysis(
    ["step_converter.py"],
    pathex=[_spec_dir],
    binaries=ocp_binaries,
    datas=ocp_datas,
    hiddenimports=step_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
step_pyz = PYZ(step_analysis.pure)

step_exe = EXE(
    step_pyz,
    step_analysis.scripts,
    [],
    exclude_binaries=True,
    name="step_converter",
    debug=False,
    strip=False,
    upx=False,
    console=True,
)

# ── 하나의 폴더에 모두 COLLECT ──
coll = COLLECT(
    gui_exe,
    gui_analysis.binaries,
    gui_analysis.datas,
    step_exe,
    step_analysis.binaries,
    step_analysis.datas,
    strip=False,
    upx=False,
    name="GyroidGenerator",
)
