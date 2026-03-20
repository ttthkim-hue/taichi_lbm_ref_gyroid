@echo off
chcp 65001 >nul
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo ============================================
echo GyroidGenerator - Windows PE 빌드 (PyInstaller)
echo ============================================
echo.
echo 주의: 이 스크립트는 **Windows**에서만 실행하세요.
echo       Linux/WSL에서 만든 바이너리는 .exe여도 Windows에서 동작하지 않습니다.
echo.

set "PYEXE="
py -3.12 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.12"
if not defined PYEXE py -3.11 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.11"
if not defined PYEXE py -3.10 -c "import sys" >nul 2>&1 && set "PYEXE=py -3.10"
if not defined PYEXE where python >nul 2>&1 && set "PYEXE=python"
if not defined PYEXE (
  echo [오류] Python 3.10~3.12를 찾을 수 없습니다. https://www.python.org/downloads/
  exit /b 1
)

echo 사용 Python: %PYEXE%
%PYEXE% -c "import sys; print('version:', sys.version)" || exit /b 1

if not exist ".venv_win\Scripts\activate.bat" (
  echo 가상환경 생성: .venv_win
  %PYEXE% -m venv .venv_win || exit /b 1
)

call ".venv_win\Scripts\activate.bat" || exit /b 1
python -m pip install --upgrade pip wheel setuptools || exit /b 1

echo.
echo [1/2] 필수 패키지 설치 (STL + GUI) ...
pip install numpy scipy scikit-image trimesh manifold3d pyinstaller || exit /b 1

echo.
echo [선택] STEP 출력에 cadquery/OCP가 필요하면 아래 줄의 주석을 제거한 뒤 다시 실행하세요.
REM pip install cadquery

echo.
echo [2/2] PyInstaller 빌드 ...
pyinstaller --noconfirm GyroidGenerator.spec || exit /b 1

echo.
echo ============================================
echo 완료: dist\GyroidGenerator.exe
echo 배포 시 dist 폴더 전체를 함께 복사하거나, onefile exe만 복사해도 됩니다.
echo ============================================
pause
