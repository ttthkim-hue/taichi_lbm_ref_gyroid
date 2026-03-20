Gyroid Catalyst Support - STEP/STL Generator
=============================================

[중요] Windows 사용자: 이 폴더의 GyroidGenerator.exe 가 실행되지 않으면,
       Linux용 바이너리일 수 있습니다. 상위 폴더의 README_BUILD.md 와
       build_windows.bat 로 Windows PC에서 다시 빌드하세요.

1. GyroidGenerator(.exe) 실행
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
  - cadquery/OCP 미설치 환경에서는 STEP 변환이 건너뛰어질 수 있습니다.
  - 이 경우 STL 출력 후 SpaceClaim에서 STL -> Convert to Solid -> STEP 저장을 사용하세요.
