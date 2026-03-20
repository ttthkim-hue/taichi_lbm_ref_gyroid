#!/usr/bin/env bash
# GitHub에 푸시 → Actions가 Windows .exe 빌드 → Artifacts 에서 다운로드
# 사전: GitHub에서 빈 저장소 생성 후 URL을 아래 REMOTE_URL에 넣거나 인자로 전달
set -euo pipefail
cd "$(dirname "$0")/.."
REMOTE_URL="${1:-}"
BRANCH="${GITHUB_DEFAULT_BRANCH:-main}"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "[오류] git 저장소가 아닙니다. 먼저: git init && git add -A && git commit -m 'initial'"
  exit 1
fi

if [[ -z "$REMOTE_URL" ]]; then
  echo "사용법: $0 <git@github.com:USER/REPO.git>"
  echo "   또는: $0 https://github.com/USER/REPO.git"
  echo ""
  echo "GitHub 웹에서 New repository(빈 저장소) 만든 뒤 위 URL을 붙여 넣으세요."
  exit 1
fi

git branch -M "$BRANCH" 2>/dev/null || true
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "$REMOTE_URL"
else
  git remote set-url origin "$REMOTE_URL"
fi

echo "푸시 중: origin $BRANCH ..."
git push -u origin "$BRANCH"

echo ""
echo "다음: GitHub → Actions → 'Build GyroidGenerator (Windows exe)' → 완료 후"
echo "      Artifacts → GyroidGenerator-windows.zip → GyroidGenerator.exe"
