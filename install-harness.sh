#!/bin/bash
# analyze-trust-suite 스킬을 타깃 레포에 설치하는 스크립트
#
# 사용법:
#   ./install-harness.sh /path/to/target-repo
#   ./install-harness.sh .   (현재 디렉토리에 설치)

set -e

HARNESS_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"

if [ ! -d "$TARGET" ]; then
  echo "오류: 타깃 디렉토리가 없습니다: $TARGET"
  exit 1
fi

TARGET="$(cd "$TARGET" && pwd)"

echo "하네스 소스: $HARNESS_DIR"
echo "설치 대상:   $TARGET"
echo ""

# skills/ 복사 (24개 모두)
mkdir -p "$TARGET/.claude/skills"
cp -r "$HARNESS_DIR/skills/"* "$TARGET/.claude/skills/"
echo "✓ skills 복사 완료 (24개)"

# scratch/, docs/plans/, docs/reports/, scripts/ 디렉토리 생성
mkdir -p "$TARGET/scratch"
mkdir -p "$TARGET/docs/plans"
mkdir -p "$TARGET/docs/reports"
mkdir -p "$TARGET/scripts"
mkdir -p "$TARGET/data/raw"
echo "✓ 디렉토리 생성 완료"

# .gitignore 생성 또는 추가
GITIGNORE="$TARGET/.gitignore"
ENTRIES="scratch/
data/raw/
scripts/__pycache__/
*.pyc"

if [ -f "$GITIGNORE" ]; then
  # 이미 있는 항목은 건너뜀
  while IFS= read -r entry; do
    if ! grep -qF "$entry" "$GITIGNORE"; then
      echo "$entry" >> "$GITIGNORE"
    fi
  done <<< "$ENTRIES"
  echo "✓ .gitignore 업데이트"
else
  echo "$ENTRIES" > "$GITIGNORE"
  echo "✓ .gitignore 생성"
fi

# settings.json 병합 (없는 경우에만 생성)
SETTINGS="$TARGET/.claude/settings.json"
if [ ! -f "$SETTINGS" ]; then
  mkdir -p "$TARGET/.claude"
  cp "$HARNESS_DIR/.claude/settings.json" "$SETTINGS"
  echo "✓ settings.json 생성"
else
  echo "⚠ settings.json 이미 존재 — 수동 병합 필요: $SETTINGS"
fi

echo ""
echo "설치 완료!"
echo ""
echo "다음 단계:"
echo "  1. $TARGET 에서 Claude Code 열기"
echo "  2. /define-analysis 로 분석 시작"