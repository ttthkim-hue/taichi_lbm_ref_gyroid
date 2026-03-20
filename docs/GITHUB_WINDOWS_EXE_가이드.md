# GitHub 연결 없이는 자동 완료가 불가능한 이유

이 PC(WSL) 환경에서는 다음이 **없습니다**.

- `taichi_lbm_ref_gyroid`가 **Git 저장소로 초기화되지 않음**
- **GitHub 원격(remote)** 미설정
- **`gh` CLI 미설치** 및 **`GITHUB_TOKEN` / PAT 없음** → 제3자가 대신 `git push` 불가

**Windows용 `.exe`는 GitHub Actions의 `windows-latest` 러너에서만 안정적으로 생성**됩니다.  
연결은 **본인 계정으로 1회** 하셔야 합니다.

---

## 이미 해둔 작업 (저장소에 포함됨)

- `.github/workflows/build-gyroid-generator-windows.yml`  
  → 푸시되면 Windows에서 PyInstaller로 `dist/GyroidGenerator.exe` 빌드 후 **Artifact** 업로드

---

## 최소 절차 (5~10분)

### 1) GitHub에서 빈 저장소 만들기

- [github.com/new](https://github.com/new) → 이름 예: `taichi_lbm_ref_gyroid` → **Create** (README 추가 안 해도 됨)

### 2) 이 폴더에서 푸시 (처음 한 번)

터미널에서:

```bash
cd /mnt/h/taichi_lbm_ref_gyroid

# 아직 안 했다면 (이 저장소에서 이미 실행했다면 생략)
git init
git add -A
git commit -m "chore: initial + GyroidGenerator Windows CI"

# 본인 저장소 URL로 변경
git branch -M main
git remote add origin https://github.com/<USER>/<REPO>.git
git push -u origin main
```

HTTPS 푸시 시 **Personal Access Token(PAT)** 이 비밀번호 자리에 필요합니다.  
([GitHub → Settings → Developer settings → PAT](https://github.com/settings/tokens))

또는 스크립트:

```bash
chmod +x scripts/push_github_for_windows_exe.sh
./scripts/push_github_for_windows_exe.sh https://github.com/<USER>/<REPO>.git
```

### 3) Actions에서 `.exe` 받기

1. GitHub 저장소 → **Actions**
2. **Build GyroidGenerator (Windows exe)** 워크플로 선택
3. 최신 실행이 **초록색**이면 → 해당 run 클릭
4. 하단 **Artifacts** → **GyroidGenerator-windows.zip** 다운로드
5. 압축 해제 → **`GyroidGenerator.exe`** 가 Windows용 실행 파일

수동으로 다시 돌리려면: **Run workflow** (STEP 포함 시 `install_cadquery` 체크).

---

## `.gitignore`와 대용량 폴더

`results/`, `logs/`, 레거시 `Results_*` 등은 **푸시에서 제외**해 두었습니다 (용량·한도).  
Gyroid **exe 빌드 CI**에는 `geometry_exchange_ansys/exe_file_final/gyroid_generator` 소스만 있으면 됩니다.

---

## 요약

| 단계 | 누가 | 내용 |
|------|------|------|
| Git 초기화·커밋 | 로컬 | 아래 자동화 스크립트 또는 수동 |
| `git push` | **본인** | PAT 또는 SSH 키 필요 |
| `.exe` 생성 | GitHub Actions | 푸시 후 자동 또는 Run workflow |
| 다운로드 | **본인** | Artifacts ZIP |

**제가 대신 GitHub에 로그인하거나 토큰 없이 푸시할 수는 없습니다.**  
위 순서대로 한 번만 푸시하면 이후에는 Actions만으로 Windows exe를 반복 받을 수 있습니다.
