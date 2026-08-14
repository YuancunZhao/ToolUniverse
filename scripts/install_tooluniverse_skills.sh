#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: install_tooluniverse_skills.sh --client codex|claude|generic --dest PATH [--project-root PATH]

Install the full user-facing ToolUniverse Skill bundle from this exact checkout.
Existing unrelated Skills are preserved. Current ToolUniverse Skills are
replaced, and retired ACMG routing/refinement Skills are removed.
EOF
}

client=""
dest=""
project_root=""
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
    --project-root)
      project_root="${2:-}"
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
acmg_instruction_template="$repo_root/docs/reference/acmg_project_instructions.md"
managed_start='<!-- TOOLUNIVERSE_ACMG_INSTRUCTIONS_START -->'
managed_end='<!-- TOOLUNIVERSE_ACMG_INSTRUCTIONS_END -->'
legacy_acmg_instruction_hashes=(
  "7ee16edb16ecabbb976f72289b3973c4cae978e0fc2c56a9a03cddd57996251a"
)
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

file_sha256() {
  file_path="$1"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$file_path" | awk '{print $1}'
  else
    sha256sum "$file_path" | awk '{print $1}'
  fi
}

is_known_legacy_acmg_template() {
  digest="$(file_sha256 "$1")"
  for known_digest in "${legacy_acmg_instruction_hashes[@]}"; do
    [ "$digest" = "$known_digest" ] && return 0
  done
  return 1
}

update_managed_acmg_block() {
  instruction_path="$1"
  temp_path="$(mktemp "${TMPDIR:-/tmp}/tooluniverse-acmg-instructions.XXXXXX")"
  awk -v start="$managed_start" -v end="$managed_end" \
      -v template="$acmg_instruction_template" '
    function emit_template(line) {
      while ((getline line < template) > 0) print line
      close(template)
    }
    $0 == start { emit_template(); managed = 1; found = 1; next }
    managed && $0 == end { managed = 0; next }
    !managed { print }
    END { if (!found || managed) exit 3 }
  ' "$instruction_path" > "$temp_path" || {
    rm -f "$temp_path"
    echo "Malformed managed ACMG instruction block: $instruction_path" >&2
    return 1
  }
  mv "$temp_path" "$instruction_path"
  printf 'Updated managed ACMG instructions: %s\n' "$instruction_path"
}

migrate_project_instruction() {
  instruction_path="$1"
  if is_known_legacy_acmg_template "$instruction_path"; then
    cp "$acmg_instruction_template" "$instruction_path"
    printf 'Replaced known legacy ACMG instructions: %s\n' "$instruction_path"
    return 0
  fi
  if grep -Fq "$managed_start" "$instruction_path" \
      || grep -Fq "$managed_end" "$instruction_path"; then
    update_managed_acmg_block "$instruction_path"
    return
  fi
  if grep -nHE \
      'ACMG_route_overlays|ACMG_combine_criteria|ACMG_(finalize|finalizer)|ACMG Guard|ACMG_evidence_collector|tooluniverse-acmg-variant-classification' \
      "$instruction_path" >&2; then
    echo "Custom ACMG instructions were not modified: $instruction_path" >&2
    return 1
  fi
}

if [ -n "$project_root" ]; then
  if [ ! -d "$project_root" ]; then
    echo "--project-root must be an existing directory" >&2
    exit 2
  fi
  project_root="$(cd "$project_root" && pwd)"
  for instruction_file in AGENTS.md CLAUDE.md reasonix.toml; do
    instruction_path="$project_root/$instruction_file"
    [ -f "$instruction_path" ] || continue
    migrate_project_instruction "$instruction_path" || exit 1
  done
fi

cleanup_retired_skills() {
  skills_root="$1"
  [ -d "$skills_root" ] || return 0
  rm -rf "$skills_root/tooluniverse-acmg-overlay-routing-core"
  for retired_dir in "$skills_root"/tooluniverse-acmg-*refinement; do
    [ -e "$retired_dir" ] || continue
    rm -rf "$retired_dir"
  done
  printf 'Retired ACMG Skill cleanup checked: %s\n' "$skills_root"
}

declare -a cleanup_roots=("$dest")
if [ -n "$home_dir" ]; then
  cleanup_roots+=(
    "$home_dir/.claude/skills"
    "$home_dir/.agents/skills"
    "$home_dir/.codex/skills"
  )
fi
if [ -n "$project_root" ]; then
  cleanup_roots+=(
    "$project_root/.reasonix/skills"
    "$project_root/.agents/skills"
    "$project_root/.claude/skills"
  )
fi
for skills_root in "${cleanup_roots[@]}"; do
  cleanup_retired_skills "$skills_root"
done

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

printf 'Installed %d ToolUniverse Skills for %s into %s\n' \
  "${#source_dirs[@]}" "$client" "$dest"
