# plan_2.3V — L2 재실행 및 VTI 시각화·재검증 보고

**작성일:** 2026-03-19  
**요청:** L2 재실행 → VTI 시각화용 저장 → 재검증 후 보고 (Gyroid 3-g 중지)

---

## 1. 수행한 작업

| 순서 | 항목 | 상태 | 비고 |
|------|------|------|------|
| 1 | Gyroid 3-g 중지 | ✅ | `pkill -f run_gyroid_3ghsv_plan191v` |
| 2 | L2 재실행 | 🔄 실행 중 | `run_l2_ref6x6_plan17v.py` 백그라운드 (100k 스텝, ~70분 예상) |
| 3 | VTI 저장 | 🔄 실행 중 | `save_vti_l2a_diag.py 100000` 백그라운드 (~70분 예상) |
| 4 | 재검증 수치 | ⏳ L2 완료 후 | 동일 스크립트 내 Phase 3 진단 블록으로 출력 |

---

## 2. 실행 명령 및 로그 위치

- **L2 재실행 (재검증 포함)**  
  ```bash
  cd /mnt/h/taichi_lbm_ref_gyroid
  python scripts/run_l2_ref6x6_plan17v.py 2>&1 | tee logs/l2_rerun_plan23v_YYYYMMDD_HHMMSS.txt
  ```
  - 로그: `logs/l2_rerun_plan23v_20260319_054955.txt` (실행 시점에 따라 파일명 날짜/시간 다름)
  - 완료 시 로그에 포함되는 재검증 블록:
    - `[plan_2.3V 진단] z_in/z_out 슬라이스 ρ 역산`
    - z_in, z_out 유체 셀 수, 평균 ρ, Δρ_lbm, ΔP=Δρ×p_scale, p_scale
    - 채널 중심 (65,65) ρ(z_in), ρ(z_out)
    - L2 판정(PASS/FAIL), ΔP_theory vs ΔP_sim, CV, K_sim(A)

- **VTI 저장 (시각화용)**  
  ```bash
  python scripts/save_vti_l2a_diag.py 100000 2>&1 | tee logs/vti_l2a_diag_YYYYMMDD_HHMMSS.txt
  ```
  - 로그: `logs/vti_l2a_diag_20260319_055826.txt`
  - 출력 파일: **`results/l2a_vti/l2a_diag.vtr`** (생성 시점: VTI 스크립트 완료 후)

---

## 3. 완료 후 확인 방법

1. **프로세스 종료 확인**
   ```bash
   ps aux | grep -E "run_l2_ref6x6|save_vti_l2a"
   ```
   두 프로세스가 없으면 완료된 상태.

2. **L2 재검증 수치**
   - `logs/l2_rerun_plan23v_*.txt` 끝부분에서 `[plan_2.3V 진단]`, `[L2 검증 — plan_1.7V/1.91V]` 블록 확인.
   - ΔP_sim vs ΔP_theory 비율(기대: 1/3 ≈ 0.333 여전히 나올 수 있음), p_scale≈7.68, 단일 채널 (65,65) Δρ 등 확인.

3. **VTI 파일**
   - `results/l2a_vti/l2a_diag.vtr` 존재 여부 및 크기 확인.

---

## 4. ParaView 시각화 (VTI 생성 완료 후)

1. ParaView에서 **File → Open** → `taichi_lbm_ref_gyroid/results/l2a_vti/l2a_diag.vtr` 선택.
2. **Apply** 후, **Cell Data**에서:
   - **rho**: Z방향 입구→출구 밀도 구배(선형 감소 여부)
   - **vz**: XY 단면에서 36개 채널 포물선 프로파일
   - **solid**: 0=유체, 1=고체 (고체에서 ρ 변화 여부로 측정 오염 확인)
3. plan_2.3V §3.2 확인 항목:
   - Z방향 ρ 분포: 입구 높고 출구 낮은 선형 구배
   - XY 단면 ρ: 채널 내부만 ρ 변화, 고체 ~1.0
   - XY 단면 vz: 36개 채널 포물선, 비대칭/비균일 시 마스크 오류 의심
   - z_in, z_out 슬라이스 ρ: 유체 셀 ρ 차이 ≈ Δρ 예상
   - 채널 중심선 ρ(z): 직선 감소

---

## 5. Phase 2 시각화 진행 (Phase 3 Gyroid 제외)

- **시각화 스크립트:** `scripts/visualize_l2a_vti_plan23v.py`
  - plan_2.3V §3.2 항목별 matplotlib 그림 생성 (VTR 로드 → PNG 저장).
  - 사용: `python scripts/visualize_l2a_vti_plan23v.py [vtr_path]` (기본: `results/l2a_vti/l2a_diag_step7000.vtr`).
- **출력 이미지 (results/plan23v_vis/):**
  - `plan23v_vis_1_rho_vs_z_*.png` — Z방향 ρ 분포
  - `plan23v_vis_2_rho_xy_z542_*.png` — XY 단면 ρ (z_out)
  - `plan23v_vis_3_vz_xy_z275_*.png` — XY 단면 vz (중간)
  - `plan23v_vis_4_slices_rho_*.png` — z_in / z_out 슬라이스 ρ
  - `plan23v_vis_5_rho_centerline_*.png` — 채널 중심선 ρ(z)
- **Phase 3 (Gyroid 3-g 재실행):** 계획서 확인 후 사용자 지시대로 **제외**.

---

## 6. 요약

- **Gyroid 3-g:** 사용자 요청에 따라 제외 (시각화만 진행).
- **L2 재실행·VTI:** 동시에 백그라운드 실행 중.  
  - 로그는 tee로 저장되며, Python 출력 버퍼링으로 **실행 완료 후** 로그 파일에 내용이 채워짐.
  - 다음부터 실시간 로그를 보려면:  
    `PYTHONUNBUFFERED=1 python scripts/run_l2_ref6x6_plan17v.py ...`
- **재검증:** L2 스크립트 한 번 실행으로 Phase 3 수치 역산 출력 + L2 판정까지 모두 포함됨.
- **보고 갱신:** L2·VTI 완료 후 위 로그/파일을 열어 수치와 VTI 존재 여부를 확인한 뒤, 본 문서의 “상태” 열을 ✅로 갱신하면 됨.
