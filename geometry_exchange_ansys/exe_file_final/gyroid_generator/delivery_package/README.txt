Gyroid Catalyst Support - STEP/STL Generator
=============================================

[중요] Windows 사용자:
  - STL+STEP 모두 쓰려면 **GyroidGenerator_Windows_CI.exe** 사용 (GitHub Actions 빌드, OCP 포함).
  - 이름만 GyroidGenerator.exe 인 파일은 Linux(ELF)일 수 있음 → Windows에서 실행 불가.
  - 재빌드: 상위 폴더 README_BUILD.md / build_windows.bat / GitHub Actions.

1. GyroidGenerator_Windows_CI.exe (또는 최신 CI 산출 exe) 실행
2. a (단위셀 크기)와 t (두께) 입력
3. "생성 시작" 클릭
4. 선택한 출력 폴더에 .stl / .step 파일 생성
5. ANSYS SpaceClaim에서 File -> Open

파라미터 가이드:
  a = 3~8 mm (작을수록 촘촘, 표면적↑)
  t = 0.05~0.5 (클수록 벽 두꺼움)

기본 제공 형상:
  gyroid_a50_t30.step    - a=5mm, t=0.3 (기준)
  empty_duct_v32.step    - 빈 덕트
  reference_6x6_v32.step - 6x6 채널

주의:
  - 구버전( OCP 미포함 ) exe에서는 STEP 저장이 건너뛰어질 수 있음 → 위 CI 빌드 exe로 교체.
  - 그래도 STEP 실패 시: STL 생성 후 SpaceClaim에서 STL -> Convert to Solid -> STEP 저장.
