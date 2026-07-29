#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install_tooluniverse_skills.sh --client codex|claude|generic --dest PATH

Install the full user-facing ToolUniverse Skill bundle from this exact checkout.
Existing unrelated Skills are preserved. Current ToolUniverse Skills are
replaced, and retired ACMG routing/refinement Skills are removed.
EOF
}

client=""
dest=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    --client)
      client="${2:-}"
      shift 2
      ;;
    --dest)
      dest="${2:-}"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

case "$client" in
  codex|claude|generic) ;;
  *)
    echo "--client must be codex, claude, or generic" >&2
    exit 2
    ;;
esac

if [ -z "$dest" ]; then
  echo "--dest is required" >&2
  exit 2
fi

repo_root="$(cd "$(dirname "$0")/.." && pwd)"
home_dir="${HOME:-}"
if [ "$dest" = "/" ] || [ "$dest" = "$repo_root" ] \
  || { [ -n "$home_dir" ] && [ "$dest" = "$home_dir" ]; }; then
  echo "Refusing unsafe destination: $dest" >&2
  exit 2
fi
dest_parent="$(dirname "$dest")"
mkdir -p "$dest_parent"
dest="$(cd "$dest_parent" && pwd)/$(basename "$dest")"

case "$dest" in
  /|"")
    echo "Refusing unsafe destination: ${dest:-<empty>}" >&2
    exit 2
    ;;
esac

mkdir -p "$dest"

declare -a source_dirs=()
if [ "$client" = "codex" ]; then
  source_root="$repo_root/plugins/tooluniverse/skills"
  for skill_dir in "$source_root"/*; do
    [ -f "$skill_dir/SKILL.md" ] && source_dirs+=("$skill_dir")
  done
elif [ "$client" = "claude" ]; then
  source_root="$repo_root/plugin/skills"
  for skill_dir in "$source_root"/*; do
    [ -f "$skill_dir/SKILL.md" ] && source_dirs+=("$skill_dir")
  done
else
  source_root="$repo_root/skills"
  for skill_dir in \
    "$source_root/tooluniverse" \
    "$source_root"/tooluniverse-* \
    "$source_root/setup-tooluniverse"; do
    [ -f "$skill_dir/SKILL.md" ] || continue
    source_dirs+=("$skill_dir")
  done
fi

if [ "${#source_dirs[@]}" -eq 0 ]; then
  echo "No user-facing ToolUniverse Skills found for client profile: $client" >&2
  exit 1
fi

for skill_dir in "${source_dirs[@]}"; do
  skill_name="$(basename "$skill_dir")"
  rm -rf "$dest/$skill_name"
  if [ "$client" = "generic" ]; then
    mkdir -p "$dest/$skill_name"
    rsync -a \
      --exclude='test_*.py' \
      --exclude='*_test.py' \
      --exclude='evals/' \
      --exclude='__pycache__/' \
      --exclude='*.pyc' \
      --exclude='.pytest_cache/' \
      --exclude='.coverage' \
      --exclude='.coverage.*' \
      --exclude='coverage.xml' \
      --exclude='htmlcov/' \
      --exclude='.mypy_cache/' \
      --exclude='.ruff_cache/' \
      --exclude='.DS_Store' \
      "$skill_dir"/ "$dest/$skill_name/"
  else
    cp -R "$skill_dir" "$dest/$skill_name"
  fi
done

rm -rf "$dest/tooluniverse-acmg-overlay-routing-core"
for retired_dir in "$dest"/tooluniverse-acmg-*refinement; do
  [ -e "$retired_dir" ] || continue
  rm -rf "$retired_dir"
done

printf 'Installed %d ToolUniverse Skills for %s into %s\n' \
  "${#source_dirs[@]}" "$client" "$dest"
