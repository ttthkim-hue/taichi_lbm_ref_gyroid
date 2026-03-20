# GyroidGenerator Windows CI 빌드·검증 보고

**일시:** 2026-03-20 (KST)  
**저장소:** https://github.com/ttthkim-hue/taichi_lbm_ref_gyroid  

---

## 1. 수행 내용

| 단계 | 결과 |
|------|------|
| 로컬 변경사항 커밋 | `5fcce26` — 문서·JKCS paper 등 |
| GitHub 저장소 생성·푸시 | `gh repo create ... --push` 성공 |
| Actions 워크플로 실행 | `Build GyroidGenerator (Windows exe)` (workflow_dispatch) |
| Run ID | **23325239093** |
| Job 소요 시간 | 약 **2분** (`pyinstaller-windows`) |

**Run URL:**  
https://github.com/ttthkim-hue/taichi_lbm_ref_gyroid/actions/runs/23325239093  

---

## 2. 빌드 결과

- **상태:** 성공 (녹색 체크)
- **산출 아티팩트:** `GyroidGenerator-windows` (ZIP)
- **CLI 다운로드 예시:**
  ```bash
  gh run download 23325239093 -R ttthkim-hue/taichi_lbm_ref_gyroid -n GyroidGenerator-windows
  ```

---

## 3. 바이너리 검증 (Linux/WSL에서 `file` 명령)

다운로드한 실행 파일:

```text
PE32+ executable (GUI) x86-64, for MS Windows, 7 sections
```

- **의미:** Microsoft Windows용 **64비트 GUI PE** — 기존 Linux ELF `GyroidGenerator.exe`와 형식이 다름.
- **파일 크기:** 약 **67 MB** (onefile PyInstaller)

---

## 4. GUI “실행” 확인 한계

- WSL 환경에 **Wine 미설치**로, GUI 앱을 실제로 띄워 클릭 테스트는 하지 못함.
- **Windows PC에서 확인할 것:**
  1. ZIP 해제 후 `GyroidGenerator.exe` 더블클릭
  2. SmartScreen 시 “추가 정보” → 실행
  3. 창이 뜨면 `a`, `t` 입력 후 STL 생성 테스트

---

## 5. 로컬 복사본 (편의)

CI에서 받은 파일을 프로젝트 배포 폴더에 복사해 두었음 (Git에는 올리지 않음 — `.gitignore` 처리):

`geometry_exchange_ansys/exe_file_final/gyroid_generator/delivery_package/GyroidGenerator_Windows_CI.exe`

Windows에서 `\\wsl$\...\delivery_package\GyroidGenerator_Windows_CI.exe` 로 복사해 사용 가능.

---

## 6. 참고

- Actions 로그에 Node.js 20 deprecation **경고**만 있음 (빌드 실패 아님).
- STEP 내장 빌드는 워크플로에서 `install_cadquery` 수동 실행 시에만 활성화됨 (본 Run에서는 미사용).
