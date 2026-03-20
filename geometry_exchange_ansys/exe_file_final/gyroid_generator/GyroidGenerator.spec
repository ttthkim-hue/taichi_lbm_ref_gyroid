# -*- mode: python ; coding: utf-8 -*-
# Windows: build_windows.bat (PyInstaller는 Windows에서 실행해야 PE .exe 생성)
# Linux/WSL: pyinstaller GyroidGenerator.spec → ELF (확장자 .exe여도 Windows에서 실행 불가)

hiddenimports = [
    'skimage.measure',
    'skimage.measure._marching_cubes_lewiner',
    'trimesh',
    'trimesh.exchange',
    'manifold3d',
    'numpy',
    'scipy',
    'scipy.ndimage',
    # STEP(OCP): cadquery 설치 후 빌드 시에만 필요할 수 있음
    # 'OCP',
]

a = Analysis(
    ['gyroid_gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name='GyroidGenerator',
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
