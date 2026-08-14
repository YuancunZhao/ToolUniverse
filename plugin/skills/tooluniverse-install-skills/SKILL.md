---
name: tooluniverse-install-skills
description: Install, repair, or verify ToolUniverse research Skills. Use when Skills are missing, a client migration needs the correct Skill directory, a plugin installation is incomplete, or the enhanced ACMG fork must be installed from its exact validated commit.
---

# Install ToolUniverse Skills

Use the upstream installation path by default. Use the fork installer only when
the user explicitly needs the enhanced ACMG runtime.

## 1. Prefer plugin-managed Skills

Codex and Claude Code plugins already bundle the appropriate generated Skill
mirror. Do not install a second global copy because duplicate Skills can cause
stale routing.

Codex:

```bash
codex plugin marketplace add mims-harvard/ToolUniverse
codex plugin add tooluniverse -m tooluniverse
```

Claude Code:

```bash
claude plugin marketplace add mims-harvard/ToolUniverse
claude plugin install tooluniverse@tooluniverse
```

Use the client's plugin update command to repair an existing plugin
installation.

## 2. Standard upstream installation

For clients that consume standalone Skills, use the upstream installer:

```bash
npx skills add mims-harvard/ToolUniverse --all
```

Follow the destination reported by the installer. Do not copy the repository's
unfiltered development tree by hand.

## 3. Enhanced ACMG fork

When the user explicitly requests this branch's enhanced germline small-variant
ACMG workflow, read:

`https://raw.githubusercontent.com/YuancunZhao/ToolUniverse/codex/acmg-on-tooluniverse-1.4/SETUP.md`

Resolve the full 40-character commit under **Validated release**, fetch that
exact checkout, and run:

```bash
bash "$CHECKOUT/scripts/install_tooluniverse_skills.sh" \
  --client "$SKILLS_PROFILE" \
  --dest "$SKILLS_DIR" \
  --project-root "$PROJECT_ROOT"
```

Profiles:

| Client | Profile |
|---|---|
| Codex | `codex` |
| Claude Code/Desktop | `claude` |
| Cursor, Windsurf, and other standalone-Skill clients | `generic` |

This branch-only installer:

- copies the same filtered client mirrors used by upstream packaging;
- uses canonical filtered Skills for the generic profile;
- adds the consolidated ACMG evidence-only Skill;
- removes retired ACMG routing/refinement Skills;
- checks the known global Skill roots and the supplied project's
  `.reasonix/skills`, `.agents/skills`, and `.claude/skills` roots;
- replaces a content-hash-known legacy ACMG template and updates only blocks
  carrying ToolUniverse ACMG managed markers;
- preserves unrelated user Skills.

`PROJECT_ROOT` is the project in which the agent will use ToolUniverse. Unknown
or user-edited ACMG instructions in `AGENTS.md`, `CLAUDE.md`, or
`reasonix.toml` are not overwritten; the installer reports their exact lines
and exits nonzero so the user can merge them deliberately. Unrelated project
instructions are never changed.

Do not combine an upstream marketplace plugin with global fork Skill copies.
The fork's exact-SHA MCP runtime and its Skills must be installed as one
validated set.

## 4. Verify

Confirm representative general and ACMG Skills:

```bash
test -f "$SKILLS_DIR/tooluniverse/SKILL.md"
test -f "$SKILLS_DIR/tooluniverse-drug-research/SKILL.md"
test -f "$SKILLS_DIR/tooluniverse-protein-structure-retrieval/SKILL.md"
test -f "$SKILLS_DIR/tooluniverse-literature-deep-research/SKILL.md"
test -f "$SKILLS_DIR/tooluniverse-acmg-variant-classification/SKILL.md"
test ! -e "$SKILLS_DIR/tooluniverse-acmg-overlay-routing-core"
```

The compact MCP server exposes only its discovery/execution surface directly;
the complete scientific tool collection remains available through
`find_tools`, `get_tool_info`, and `execute_tool`.
