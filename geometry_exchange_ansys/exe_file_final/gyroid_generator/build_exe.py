#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import shutil
import subprocess
import sys


def run_command(cmd: list[str]) -> int:
    print("실행:", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Gyroid GUI PyInstaller 빌드 스크립트")
    parser.add_argument(
        "--stl-only",
        action="store_true",
        help="경량 빌드(기본 import 문제 시 fallback): STL 중심 빌드 이름 사용",
    )
    parser.add_argument(
        "--with-hidden-imports",
        action="store_true",
        help="OCP/cadquery hidden-import를 강제로 포함",
    )
    args = parser.parse_args()

    pyinstaller = shutil.which("pyinstaller")
    if not pyinstaller:
        print("오류: pyinstaller를 찾을 수 없습니다. pip install pyinstaller 후 재시도하세요.")
        return 1

    name = "GyroidGenerator_STL" if args.stl_only else "GyroidGenerator"
    cmd = [
        pyinstaller,
        "--onefile",
        "--windowed",
        "--name",
        name,
        "gyroid_gui.py",
    ]

    if args.with_hidden_imports and not args.stl_only:
        cmd.extend(
            [
                "--hidden-import=OCP",
                "--hidden-import=cadquery",
                "--collect-all=OCP",
            ]
        )

    code = run_command(cmd)
    if code != 0:
        print("\n기본 빌드 실패.")
        if not args.stl_only:
            print("다음 대안을 시도해 보세요:")
            print("  python build_exe.py --with-hidden-imports")
            print("  python build_exe.py --stl-only")
        return code

    print(f"\n완료: dist/{name}")
    if sys.platform.startswith("win"):
        print(f"배포 파일: dist/{name}.exe")
    else:
        print(f"배포 파일: dist/{name} (원하면 파일명에 .exe를 붙여 배포 가능)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
