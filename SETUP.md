# Setup ToolUniverse ACMG Enhanced

> Fork of [mims-harvard/ToolUniverse](https://github.com/mims-harvard/ToolUniverse) with ACMG/AMP variant pathogenicity classification system.

## What's Different from Official ToolUniverse

- **ACMG/AMP variant classification system**: triple-gate validation (policy validator + semantic combiner + final-answer guard)
- **22 criterion-specific overlay skills**: PVS1, PS1-PS4, PM1-PM6, PP1-PP5, BA1, BS1-BS4, BP1-BP7
- **Chinese + English pathogenicity intent detection**: auto-detects questions like "这个变异可能致病吗？"
- **Automated evidence collection**: ClinVar, gnomAD, SpliceAI, GeneBe, InterVar, PubMed in one call
- **Safety guardrails**: source labels are leads only; unvalidated classifications auto-downgrade to draft

## Step 1: Install uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen terminal. Verify: `uv --version`

## Step 2: Install MCP Server

### Option A: Chat Mode (Cursor / Claude Desktop / Windsurf / etc.)

Add to your MCP config file:

```json
{
  "mcpServers": {
    "tooluniverse": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/YuancunZhao/ToolUniverse.git@codex/skills-overlay",
        "tooluniverse"
      ],
      "env": {
        "PYTHONIOENCODING": "utf-8"
      }
    }
  }
}
```

**Config file locations by client:**

| Client | File | How to Access |
|---|---|---|
| Cursor | `~/.cursor/mcp.json` | Settings → MCP → Add new global MCP server |
| Claude Desktop | `~/Library/Application Support/Claude/claude_desktop_config.json` | Settings → Developer → Edit Config |
| Claude Code | `~/.claude.json` or `.mcp.json` | `claude mcp add` or edit directly |
| Windsurf | `~/.codeium/windsurf/mcp_config.json` | MCP hammer icon → Configure |
| Codex | `.codex/mcp.json` | Settings → MCP |
| Gemini CLI | `~/.gemini/settings.json` | `gemini mcp add` or edit directly |

### Option B: Command Line

```bash
uvx --from git+https://github.com/YuancunZhao/ToolUniverse.git@codex/skills-overlay tu status
```

## Step 3: Install ACMG Overlay Skills

```bash
git clone --depth 1 --branch codex/skills-overlay https://github.com/YuancunZhao/ToolUniverse.git /tmp/tu-acmg

# Install ACMG-specific skills (22 criterion overlays)
cp -r /tmp/tu-acmg/skills/tooluniverse-acmg-* ~/.cursor/skills/

# Install enhanced variant interpretation and classification skills
cp -r /tmp/tu-acmg/skills/tooluniverse-variant-interpretation ~/.cursor/skills/
cp -r /tmp/tu-acmg/skills/tooluniverse-acmg-variant-classification ~/.cursor/skills/
cp -r /tmp/tu-acmg/skills/tooluniverse-acmg-overlay-routing-core ~/.cursor/skills/

rm -rf /tmp/tu-acmg
```

> **Note**: `~/.cursor/skills/` is Cursor's skill directory. Replace with your client's path:
> - Claude Code: `~/.claude/skills/`
> - Codex: `~/.agents/skills/`
> - Windsurf: `~/.windsurf/skills/`

## Step 4: Restart Your Client

Close and reopen your AI client to load the MCP server and skills.

## Step 5: Test

Try any of these in Chat:

- "BRCA2 c.5946delT 这个变异可能致病吗？"
- "Is this variant likely pathogenic? NM_000059.4:c.7397T>C"
- "TP53 R248W 的致病性评级"
- "根据 ACMG 规则分类 rs28897743"

The system will automatically:
1. Detect pathogenicity intent
2. Call `ACMG_overlay_gate_assess_variant` to collect ClinVar/gnomAD/SpliceAI evidence
3. Route each criterion through its specific overlay
4. Run triple-gate validation before outputting final classification

## Optional: API Keys

Free API keys improve tool performance:

| Key | Purpose | Registration |
|---|---|---|
| `NCBI_API_KEY` | Faster PubMed access | https://account.ncbi.nlm.nih.gov/settings/ |
| `NVIDIA_API_KEY` | AlphaFold2, protein structure | https://build.nvidia.com |

Add to MCP config `env` block:
```json
"env": {
  "PYTHONIOENCODING": "utf-8",
  "NCBI_API_KEY": "your_key_here"
}
```

## Troubleshooting

| Issue | Fix |
|---|---|
| `uvx: command not found` | Re-run Step 1 install script, restart terminal |
| Skills not loading | Check skill directory path, restart client |
| MCP server won't start | Test in terminal: `uvx --from git+https://github.com/YuancunZhao/ToolUniverse.git@codex/skills-overlay tooluniverse` |
| Upgrade | `uv cache clean tooluniverse` then restart client |

Issues? [GitHub Issues](https://github.com/YuancunZhao/ToolUniverse/issues)
