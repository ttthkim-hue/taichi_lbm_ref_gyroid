# 작업지시서 — Gyroid STEP Generator GUI + EXE 패키징

**작성일:** 2026-03-19  
**대상:** 기존 `gyroid_stl_generator.py`를 GUI 앱 + STEP 출력 + EXE로 확장  
**최종 산출물:** `GyroidGenerator.exe` (단일 파일, 더블클릭 실행)

---

## 0. 전체 구조

```
gyroid_generator/
├── gyroid_gui.py              ← 메인 (GUI + 생성 로직 + STEP 변환)
├── requirements.txt
├── build_exe.py               ← PyInstaller 빌드 스크립트
└── dist/
    └── GyroidGenerator.exe    ← 최종 배포 파일
```

---

## 1. GUI 설계 (tkinter)

> **tkinter를 사용한다.** 추가 설치 없이 Python 내장. PyInstaller 호환성 최고.

### 1.1 레이아웃

```
┌─────────────────────────────────────────────┐
│  Gyroid Catalyst Support — STEP Generator    │
├─────────────────────────────────────────────┤
│                                             │
│  ── 파라미터 설정 ──                         │
│                                             │
│  단위셀 크기 a [mm]:  [  5.0  ] ← Entry     │
│    권장 범위: 3.0 ~ 8.0 mm                   │
│                                             │
│  두께 파라미터 t:     [  0.3  ] ← Entry     │
│    권장 범위: 0.05 ~ 0.50                    │
│                                             │
│  해상도 (res):        [  60   ] ← Entry     │
│    30=빠름, 60=기본, 120=고품질              │
│                                             │
│  ☑ 외벽 포함 (1.0mm)          ← Checkbox   │
│                                             │
│  ── 출력 설정 ──                             │
│  ☑ STL 저장                                 │
│  ☑ STEP 저장                                │
│                                             │
│  [    생성 시작    ] ← Button               │
│                                             │
│  ── 상태 ──                                  │
│  ┌─────────────────────────────────────┐    │
│  │ 로그 출력 (ScrolledText)             │    │
│  │ ✅ 파라미터: a=5.0mm, t=0.3         │    │
│  │ 🏗️ Gyroid 생성 중...                │    │
│  │ ✅ STL 저장: gyroid_a50_t30.stl     │    │
│  │ 🔄 STEP 변환 중...                  │    │
│  │ ✅ STEP 저장: gyroid_a50_t30.step   │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ── 수식 참고 ──                             │
│  φ = sin(2πx/a)cos(2πy/a) + ...            │
│  Solid: φ > -t  /  Fluid: φ ≤ -t           │
│  도메인: 25.4×25.4×110mm (1인치 관체)        │
├─────────────────────────────────────────────┤
│  파라미터 가이드                              │
│  ┌───────────┬──────────┬─────────────────┐ │
│  │ 파라미터   │ 범위     │ 효과            │ │
│  ├───────────┼──────────┼─────────────────┤ │
│  │ a (단위셀) │ 3~8 mm  │ 작을수록 촘촘   │ │
│  │           │          │ 표면적↑ 압손↑   │ │
│  │ t (두께)   │ 0.05~0.5│ 클수록 벽 두꺼움│ │
│  │           │          │ 공극률↓         │ │
│  └───────────┴──────────┴─────────────────┘ │
└─────────────────────────────────────────────┘
```

### 1.2 GUI 핵심 코드 구조 (참고용)

```python
import tkinter as tk
from tkinter import ttk, scrolledtext, filedialog, messagebox
import threading

class GyroidApp:
    def __init__(self, root):
        root.title("Gyroid Catalyst Support — STEP Generator")
        root.geometry("550x750")
        root.resizable(False, False)
        
        # ── 파라미터 프레임 ──
        param_frame = ttk.LabelFrame(root, text="파라미터 설정", padding=10)
        param_frame.pack(fill='x', padx=10, pady=5)
        
        # a
        ttk.Label(param_frame, text="단위셀 크기 a [mm]:").grid(row=0, column=0, sticky='w')
        self.a_var = tk.DoubleVar(value=5.0)
        ttk.Entry(param_frame, textvariable=self.a_var, width=10).grid(row=0, column=1)
        ttk.Label(param_frame, text="권장: 3.0 ~ 8.0", foreground='gray').grid(row=1, column=0, columnspan=2, sticky='w')
        
        # t
        ttk.Label(param_frame, text="두께 파라미터 t:").grid(row=2, column=0, sticky='w', pady=(10,0))
        self.t_var = tk.DoubleVar(value=0.3)
        ttk.Entry(param_frame, textvariable=self.t_var, width=10).grid(row=2, column=1, pady=(10,0))
        ttk.Label(param_frame, text="권장: 0.05 ~ 0.50", foreground='gray').grid(row=3, column=0, columnspan=2, sticky='w')
        
        # res
        ttk.Label(param_frame, text="해상도 (res):").grid(row=4, column=0, sticky='w', pady=(10,0))
        self.res_var = tk.IntVar(value=60)
        ttk.Entry(param_frame, textvariable=self.res_var, width=10).grid(row=4, column=1, pady=(10,0))
        ttk.Label(param_frame, text="30=빠름, 60=기본, 120=고품질", foreground='gray').grid(row=5, column=0, columnspan=2, sticky='w')
        
        # 체크박스
        self.duct_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(param_frame, text="외벽 포함 (1.0mm)", variable=self.duct_var).grid(row=6, column=0, columnspan=2, sticky='w', pady=(10,0))
        
        # ── 출력 설정 ──
        out_frame = ttk.LabelFrame(root, text="출력 설정", padding=10)
        out_frame.pack(fill='x', padx=10, pady=5)
        
        self.stl_var = tk.BooleanVar(value=True)
        self.step_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(out_frame, text="STL 저장", variable=self.stl_var).pack(anchor='w')
        ttk.Checkbutton(out_frame, text="STEP 저장", variable=self.step_var).pack(anchor='w')
        
        # ── 생성 버튼 ──
        self.btn = ttk.Button(root, text="생성 시작", command=self.on_generate)
        self.btn.pack(pady=10)
        
        # ── 로그 ──
        log_frame = ttk.LabelFrame(root, text="상태", padding=5)
        log_frame.pack(fill='both', expand=True, padx=10, pady=5)
        self.log = scrolledtext.ScrolledText(log_frame, height=12, state='disabled', font=('Consolas', 9))
        self.log.pack(fill='both', expand=True)
        
        # ── 하단 수식 안내 ──
        info = ttk.LabelFrame(root, text="수식 / 파라미터 가이드", padding=5)
        info.pack(fill='x', padx=10, pady=5)
        ttk.Label(info, text="φ = sin(2πx/a)·cos(2πy/a) + sin(2πy/a)·cos(2πz/a) + sin(2πz/a)·cos(2πx/a)", font=('Consolas', 8)).pack(anchor='w')
        ttk.Label(info, text="Solid: φ > -t  /  Fluid: φ ≤ -t  /  도메인: 25.4×25.4×110mm", font=('Consolas', 8)).pack(anchor='w')
        ttk.Label(info, text="a ↓ → 촘촘, 표면적↑, 압손↑  |  t ↑ → 벽 두꺼움, 공극률↓", font=('Consolas', 8), foreground='gray').pack(anchor='w')

    def log_msg(self, msg):
        self.log.config(state='normal')
        self.log.insert('end', msg + '\n')
        self.log.see('end')
        self.log.config(state='disabled')
        self.log.update()

    def on_generate(self):
        # 버튼 비활성화 후 별도 스레드 실행 (GUI 멈춤 방지)
        self.btn.config(state='disabled')
        threading.Thread(target=self.run_generation, daemon=True).start()

    def run_generation(self):
        try:
            self.do_generate()
        except Exception as e:
            self.log_msg(f"❌ 오류: {e}")
        finally:
            self.btn.config(state='normal')

    def do_generate(self):
        # 여기에 기존 생성 로직 + STEP 변환 (§2, §3 참조)
        pass

if __name__ == '__main__':
    root = tk.Tk()
    app = GyroidApp(root)
    root.mainloop()
```

> ⚠️ 위는 구조 참고용. 기존 `gyroid_stl_generator.py`의 생성 로직을 `do_generate()` 안에 넣을 것.

---

## 2. 형상 생성 로직 (기존 코드 그대로)

기존 `gyroid_stl_generator.py`의 셀 4(형상 생성) + 셀 5(STL 저장) 코드를 `do_generate()` 메서드 안에 배치.

**변경 사항:**
- `print()` → `self.log_msg()`로 교체
- `a`, `t`, `res` → `self.a_var.get()` 등으로 교체
- 파일 저장 경로: `filedialog.asksaveasfilename()` 또는 현재 디렉터리

---

## 3. STEP 변환 추가

STL 저장 후, STEP 체크박스가 켜져 있으면 변환 수행.

### 3.1 STEP 변환 코드

```python
def convert_to_step(self, stl_path, step_path):
    """STL → STEP 변환 (cadquery/OCC)"""
    self.log_msg("🔄 STEP 변환 중...")
    
    try:
        from OCP.StlAPI import StlAPI_Reader
        from OCP.TopoDS import TopoDS_Shape, TopoDS
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
        from OCP.STEPControl import STEPControl_Writer, STEPControl_AsIs
        from OCP.TopExp import TopExp_Explorer
        from OCP.TopAbs import TopAbs_SHELL
        from OCP.Interface import Interface_Static
    except ImportError:
        self.log_msg("⚠️ cadquery 미설치. STEP 변환 건너뜀.")
        self.log_msg("   pip install cadquery 후 재실행하세요.")
        return False

    # 1. STL 읽기
    reader = StlAPI_Reader()
    shape = TopoDS_Shape()
    if not reader.Read(shape, stl_path):
        self.log_msg("❌ STL 읽기 실패")
        return False

    # 2. Sewing
    sewing = BRepBuilderAPI_Sewing(0.1)
    sewing.Add(shape)
    sewing.Perform()
    sewn = sewing.SewedShape()

    # 3. Solid 시도
    result = sewn
    try:
        explorer = TopExp_Explorer(sewn, TopAbs_SHELL)
        if explorer.More():
            shell = TopoDS.Shell_s(explorer.Current())
            maker = BRepBuilderAPI_MakeSolid(shell)
            if maker.IsDone():
                result = maker.Solid()
    except:
        pass

    # 4. STEP 저장
    writer = STEPControl_Writer()
    Interface_Static.SetCVal_s("write.step.schema", "AP214")
    writer.Transfer(result, STEPControl_AsIs)
    status = writer.Write(step_path)

    if status == 1:
        size_mb = os.path.getsize(step_path) / 1024 / 1024
        self.log_msg(f"✅ STEP 저장: {step_path} ({size_mb:.1f} MB)")
        return True
    else:
        self.log_msg("❌ STEP 저장 실패")
        return False
```

### 3.2 do_generate() 흐름

```python
def do_generate(self):
    a = self.a_var.get()
    t = self.t_var.get()
    res = self.res_var.get()
    
    # 파라미터 검증
    a = max(3.0, min(8.0, a))
    t = max(0.05, min(0.5, t))
    self.log_msg(f"✅ 파라미터: a={a}mm, t={t}, res={res}")
    
    # 파일명
    a_str = f"{a:.1f}".replace('.', '')
    t_str = f"{t:.2f}"[2:]
    base_name = f"gyroid_a{a_str}_t{t_str}"
    
    # ── 형상 생성 (기존 코드) ──
    self.log_msg("🏗️ Gyroid 생성 중...")
    # ... (기존 셀 4 코드, print→self.log_msg) ...
    
    # ── STL 저장 ──
    if self.stl_var.get():
        stl_path = base_name + ".stl"
        combined.export(stl_path, file_type='stl')
        self.log_msg(f"✅ STL: {stl_path} ({os.path.getsize(stl_path)/1024/1024:.1f} MB)")
    
    # ── STEP 변환 ──
    if self.step_var.get():
        stl_path = base_name + ".stl"
        if not os.path.exists(stl_path):
            combined.export(stl_path, file_type='stl')
        step_path = base_name + ".step"
        self.convert_to_step(stl_path, step_path)
    
    self.log_msg("\n🎉 완료!")
```

---

## 4. EXE 빌드 (PyInstaller)

### 4.1 requirements.txt

```
numpy
scipy
scikit-image
trimesh
manifold3d
cadquery
pyinstaller
```

### 4.2 빌드 명령

```bash
pip install -r requirements.txt
pyinstaller --onefile --windowed --name GyroidGenerator gyroid_gui.py
```

| 옵션 | 의미 |
|------|------|
| `--onefile` | 단일 EXE로 패키징 |
| `--windowed` | 콘솔 창 숨김 (GUI만 표시) |
| `--name` | 출력 파일명 |

### 4.3 빌드 결과

```
dist/
└── GyroidGenerator.exe    ← 이것만 배포
```

### 4.4 주의사항

- **cadquery(OCC) 포함 시 EXE 크기가 300~500MB**가 될 수 있음
- cadquery 포함이 안 되면 **STL만 출력하는 경량 버전**으로 빌드:

```bash
# 경량 버전 (STL만, cadquery 없이)
pyinstaller --onefile --windowed --name GyroidGenerator_STL gyroid_gui.py
# → EXE ~50MB
```

- **cadquery 포함 빌드가 실패하면:**
  - hidden-imports 추가 필요할 수 있음:
  ```bash
  pyinstaller --onefile --windowed \
    --hidden-import=OCP \
    --hidden-import=cadquery \
    --collect-all=OCP \
    --name GyroidGenerator gyroid_gui.py
  ```

### 4.5 테스트

```bash
# 빌드 후 dist 폴더에서:
cd dist
./GyroidGenerator.exe
# GUI 뜨는지 확인
# a=5, t=0.3 기본값으로 생성 → STL + STEP 파일 확인
# bounding box: 25.4 × 25.4 × 110 mm 확인
```

---

## 5. 배포 패키지

타 기관에 전달:

```
전달폴더/
├── GyroidGenerator.exe        ← 더블클릭 실행
├── README.txt                 ← 간단 사용법
├── gyroid_a50_t30.step        ← 기본 형상 미리 포함
├── empty_duct_v32.step
└── reference_6x6_v32.step
```

### README.txt

```
Gyroid Catalyst Support — STEP/STL Generator
============================================

1. GyroidGenerator.exe 더블클릭
2. a (단위셀 크기)와 t (두께) 입력
3. "생성 시작" 클릭
4. 같은 폴더에 .stl / .step 파일 생성됨
5. ANSYS SpaceClaim에서 File → Open

파라미터 가이드:
  a = 3~8 mm (작을수록 촘촘, 표면적↑)
  t = 0.05~0.5 (클수록 벽 두꺼움)

기본 제공 형상:
  gyroid_a50_t30.step  — a=5mm, t=0.3 (기준)
  empty_duct_v32.step  — 빈 덕트
  reference_6x6_v32.step — 6×6 채널
```

---

## 6. cadquery 설치 불가 시 대안

타 기관 PC에서 cadquery/OCC가 안 깔리면 EXE에 포함도 안 될 수 있음.

**대안: STL 전용 EXE + SpaceClaim 변환 안내**

```
앱에서 STL 출력 → SpaceClaim에서 Open → Convert to Solid → Save as STEP
```

이 경우 GUI에서 STEP 체크박스를 비활성화하고, 로그에 "STEP이 필요하면 SpaceClaim에서 STL → Solid 변환하세요" 안내 표시.

---

## 체크리스트

| 순서 | 항목 | 상태 |
|------|------|------|
| 1 | gyroid_gui.py 작성 (tkinter GUI) | ☐ |
| 2 | 기존 생성 로직 통합 (셀 4+5) | ☐ |
| 3 | STEP 변환 추가 (cadquery/OCC) | ☐ |
| 4 | 로컬 테스트 (python gyroid_gui.py) | ☐ |
| 5 | PyInstaller 빌드 | ☐ |
| 6 | EXE 테스트 (다른 PC에서) | ☐ |
| 7 | README.txt 작성 | ☐ |
| 8 | 배포 패키지 zip | ☐ |