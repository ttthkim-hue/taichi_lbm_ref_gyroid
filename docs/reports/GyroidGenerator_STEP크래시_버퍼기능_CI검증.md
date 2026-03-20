# GyroidGenerator — STEP 후 종료 현상 수정 · Z 버퍼 토글 · GitHub CI 검증

**일자:** 2026-03-20  

## 1. 증상

- STL 생성 후 STEP 변환 중 **프로그램이 그냥 종료**되는 경우가 있었음 (Windows exe).

## 2. 원인 (유력)

**Tkinter는 메인 스레드에서만 UI를 다뤄야 함.**  
백그라운드 워커 스레드에서 `root.after(0, ...)` 로 `DoubleVar.set` / 버튼 상태를 바꾸는 코드가 있었고, **Windows에서 이 패턴은 정의되지 않은 동작**이며 창이 닫히거나 프로세스가 비정상 종료할 수 있음.  
(네이티브 OCP 단계와 겹치면 재현이 더 잘 될 수 있음.)

## 3. 조치

| 항목 | 내용 |
|------|------|
| **UI 스레딩** | `ui_queue` + 메인 스레드 `_tick_main_thread` 에서만 `Button` / `DoubleVar` 갱신 |
| **버튼 복구** | `finally` 에서도 `root.after` 대신 `_ui_btn(True)` |
| **STEP 시간 안내** | 로그에 1~4단계 진행 메시지 + “수 분~10분 이상” 안내 |
| **메모리** | STEP 직전 `del` 대용량 배열/메쉬 + `gc.collect()` |
| **Z 5mm 버퍼** | 체크박스 **기본 ON**: z∈[5,105] mm / **OFF**: z∈[0,110] mm |
| **파일명** | 버퍼 구분: `..._buf.stl` / `..._fullz.stl` (및 동일 `.step`) |

## 4. STEP 변환 시간

- **STL보다 훨씬 오래 걸릴 수 있음.**  
- OCP **Sewing** 이 특히 면 수에 비례해 무거움.  
- res=60·외벽 포함 기준으로 **수 분**은 흔하고, **10분 이상**도 가능.

## 5. GitHub Actions 검증

워크플로 `.github/workflows/build-gyroid-generator-windows.yml`:

1. **`verify-python-syntax`** (ubuntu-latest): `python3 -m py_compile gyroid_gui.py`
2. **`pyinstaller-windows`** (windows-latest, `needs: verify-python-syntax`): cadquery + PyInstaller + 아티팩트 업로드

GUI·STEP 런타임은 CI에서 자동 클릭 테스트하지 않음 (Tk 헤드리스 한계).  
**exe 형식·빌드 성공**은 해당 워크플로로 검증.

푸시 후 최신 Run URL은 저장소 **Actions** 탭에서 확인.

## 6. 사용자 확인 사항 (Windows)

1. 최신 **GyroidGenerator-windows.zip** 다운로드  
2. STEP 체크 후 생성 → 로그에 `(1/4)…(4/4)` 진행이 보이는지  
3. 완료 전 창이 닫히지 않는지  
4. **Z 버퍼** on/off 각각으로 `*_buf` / `*_fullz` 파일명·높이 확인  

---

*본 문서는 코드 변경과 CI 구성을 기준으로 작성됨.*
