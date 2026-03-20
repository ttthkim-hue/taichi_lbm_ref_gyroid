# GyroidGenerator 빌드 안내

## 왜 기존 `delivery_package/GyroidGenerator.exe`가 Windows에서 안 열렸나?

그 파일은 **Linux ELF 실행 파일**입니다. 이름만 `.exe`일 뿐, Windows PE 형식이 아닙니다.  
(WSL/리눅스에서 `file GyroidGenerator.exe` → `ELF 64-bit ...`)

**Windows용 실행 파일은 Windows에서 PyInstaller를 돌려야만** 생성됩니다.

---

## Windows에서 빌드 (권장)

1. **Python 3.11 또는 3.12** 설치 ([python.org](https://www.python.org/downloads/)).  
   - 설치 시 **“Add python.exe to PATH”** 선택 권장.

2. 탐색기에서 이 폴더로 이동:
   `geometry_exchange_ansys\exe_file_final\gyroid_generator`

3. **`build_windows.bat`** 더블클릭 또는 CMD에서 실행:
   ```bat
   build_windows.bat
   ```

4. 성공 시 출력:
   - `dist\GyroidGenerator.exe` ← **이 파일이 진짜 Windows용**

5. **STEP 변환**까지 exe에 넣으려면 `build_windows.bat` 안의 다음 줄 주석을 해제 후 재실행:
   ```bat
   pip install cadquery
   ```
   - 용량이 크고, 환경에 따라 Visual C++ 재배포 패키지가 필요할 수 있습니다.
   - STEP 없이 STL만 쓰면 `cadquery` 없이도 동작합니다.

---

## 수동 빌드 (동일 환경)

```bat
cd geometry_exchange_ansys\exe_file_final\gyroid_generator
py -3.12 -m venv .venv_win
.venv_win\Scripts\activate
pip install -r requirements.txt
pyinstaller --noconfirm GyroidGenerator.spec
```

---

## GitHub Actions로 빌드 (Windows 러너, 로컬 Windows 불필요)

1. 이 저장소를 GitHub에 푸시합니다. (`geometry_exchange_ansys/.../gyroid_generator` 소스가 **커밋에 포함**되어 있어야 합니다.)
2. GitHub에서 **Actions** 탭 → **Build GyroidGenerator (Windows exe)** 워크플로 선택.
3. **Run workflow** 실행 (필요 시 `install_cadquery` 로 STEP 포함 빌드).
4. 완료 후 해당 실행(run) 하단 **Artifacts** → `GyroidGenerator-windows.zip` 다운로드 → 압축 해제 후 `GyroidGenerator.exe` 사용.

워크플로 파일: `.github/workflows/build-gyroid-generator-windows.yml`  
`main` / `master` 브랜치에 `gyroid_generator` 경로가 푸시되면 자동으로 한 번 빌드됩니다.

---

## Linux/WSL에서 빌드할 때

- 같은 `GyroidGenerator.spec`으로 빌드하면 **Linux용 ELF**가 나옵니다.
- 배포 파일명은 **`GyroidGenerator_linux`** 등으로 두고, Windows 패키지와 혼동하지 마세요.

```bash
cd geometry_exchange_ansys/exe_file_final/gyroid_generator
source .venv/bin/activate   # 또는 새 venv
pip install -r requirements.txt
pyinstaller --noconfirm GyroidGenerator.spec
# 결과: dist/GyroidGenerator (ELF)
```

---

## 실행 시 Windows에서 자주 나는 문제

| 증상 | 조치 |
|------|------|
| SmartScreen 경고 | “추가 정보” → “실행” |
| VCRUNTIME140.dll 없음 | [Microsoft VC++ 재배포 패키지](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist) x64 설치 |
| Tk 창이 안 뜸 | 동일 OS(64bit)용 Python으로 다시 빌드 |

---

## 소스

- 진입점: `gyroid_gui.py`
- 스펙: `GyroidGenerator.spec`
