# PyInstaller runtime hook — Windows frozen exe에서 OCP/OCCT DLL 검색 경로만 추가
import os
import sys

if sys.platform == "win32" and getattr(sys, "frozen", False):
    _meipass = getattr(sys, "_MEIPASS", None)
    if _meipass and os.path.isdir(_meipass):

        def _add(p: str) -> None:
            if os.path.isdir(p):
                try:
                    os.add_dll_directory(p)
                except (AttributeError, OSError, FileNotFoundError):
                    pass

        _add(_meipass)
        for _sub in ("OCP", "Library", "lib", "bin", "cadquery"):
            _add(os.path.join(_meipass, _sub))
