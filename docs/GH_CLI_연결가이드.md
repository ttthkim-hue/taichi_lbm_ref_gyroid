# GitHub CLI (`gh`) 연결 가이드

## 1. 설치 확인

이 PC(WSL)에는 **Miniconda** 환경에 `gh` 2.88+ 가 설치되어 있습니다.

```bash
# PATH에 miniconda가 없으면 전체 경로로 실행
~/miniconda3/bin/gh --version
```

쉘에서 항상 쓰려면 `~/.bashrc` 에 다음이 있는지 확인하세요 (conda init 시 보통 포함됨).

```bash
export PATH="$HOME/miniconda3/bin:$PATH"
```

---

## 2. 로그인 (반드시 **대화형 터미널**에서)

Cursor **터미널 패널** (`Ctrl+`` `)을 연 뒤:

```bash
gh auth login
```

질문이 나오면 예시 선택:

| 질문 | 권장 선택 |
|------|-----------|
| GitHub.com | **GitHub.com** |
| 프로토콜 | **HTTPS** (또는 SSH 키 이미 쓰면 **SSH**) |
| Git 자격 증명 | **Yes** (`gh`가 git credential helper로 등록) |
| 인증 방식 | **Login with a web browser** 또는 **Paste an authentication token** |

- **웹 브라우저:** 표시된 **일회용 코드**를 복사 → Enter → 브라우저에서 붙여넣기 후 승인.
- **토큰:** [GitHub → Settings → Developer settings → Personal access tokens](https://github.com/settings/tokens) 에서 `repo` 권한 포함 PAT 생성 후 붙여넣기.

완료 후 확인:

```bash
gh auth status
```

`Logged in to github.com as <username>` 이 보이면 성공입니다.

---

## 3. 저장소 만들고 푸시 (예시)

프로젝트 루트에서:

```bash
cd /mnt/h/taichi_lbm_ref_gyroid

# 원격이 없을 때: GitHub에 빈 저장소 생성 + origin 설정 + 푸시 (한 번에)
gh repo create taichi_lbm_ref_gyroid --public --source=. --remote=origin --push
```

이미 웹에서 저장소를 만들었다면:

```bash
gh repo set-default <USER>/<REPO>
git remote add origin https://github.com/<USER>/<REPO>.git   # 없을 때만
git push -u origin main
```

---

## 4. Windows `.exe` 빌드 (Actions)

푸시 후:

```bash
gh workflow run "Build GyroidGenerator (Windows exe)"
# 또는 웹: Actions → 해당 워크플로 → Run workflow
```

실행 목록·로그:

```bash
gh run list --workflow="build-gyroid-generator-windows.yml"
gh run watch
```

아티팩트는 웹 UI에서 **Artifacts** 로 다운로드하는 것이 가장 간단합니다.  
(CLI로 받으려면 `gh run download <run-id>` — run-id는 `gh run list`에서 확인)

---

## 5. 자주 나는 문제

| 증상 | 조치 |
|------|------|
| `gh: command not found` | `~/miniconda3/bin/gh` 또는 `conda activate base` |
| 비대화형 환경에서 로그인 실패 | Cursor **통합 터미널**에서 `gh auth login` 실행 |
| `HTTP 401` | `gh auth refresh` 또는 `gh auth login` 재실행 |
| SSH 사용 시 | `gh auth login` 에서 SSH 선택 + `ssh -T git@github.com` 확인 |

---

## 참고

- 공식 문서: [GitHub CLI](https://cli.github.com/manual/)
- 본 프로젝트 Windows 빌드 워크플로: `.github/workflows/build-gyroid-generator-windows.yml`
