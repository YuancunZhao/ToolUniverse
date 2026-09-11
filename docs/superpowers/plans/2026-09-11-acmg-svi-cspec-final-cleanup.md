# ACMG/CSpec 剩余清理与副本同步计划

> **执行 agent：** 使用 executing-plans，按 A→B→C 实施并分别提交。本计划只处理剩余遗漏，不重做已完成的科学修正、JSON 格式恢复或历史文档归并。

## 1. 起点与边界

| 项目 | 固定值 |
|---|---|
| 官方 upstream | **https://github.com/mims-harvard/ToolUniverse** |
| 官方基线 | `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6` |
| 本轮起点 | `b53396ba872305949227dc837f9fae78173a818d` |
| 工作区 | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 分支 | `codex/acmg-svi-cspec-lightweight`，继续使用 |
| 执行时保存计划 | `docs/superpowers/plans/2026-09-11-acmg-svi-cspec-final-cleanup.md` |

- 核对 HEAD、工作区和远程地址；若起点变化，先检查新增差异，不覆盖其他工作。
- **生产 API、Schema、计算器、CSpec 查询逻辑、生成包装、metadata、两个工具 JSON、依赖与锁文件均不修改。**
- 根目录 ACMG `SVI_REFERENCE.md` 的三处科学修正已经正确，只补分发同步。
- 不改旧工作区、用户 MCP 配置，不安装宿主、不推送。
- 每次修改一个完整小节，立即检查实际 diff。不要用一个跨多个小节的原子替换脚本处理所有任务，也不要仅依据脚本成功或测试通过宣称内容已清理。

## 2. A：清除旧入口剩余的独立评估规则

只修改 `skills/tooluniverse-variant-interpretation/` 下三个源文件；分发副本统一在任务 B 处理。

### A1. 工具参考：只解释返回数据

修改 `TOOLS_REFERENCE.md`。

| 当前残留 | 确定的修改 |
|---|---|
| COSMIC 表：热点→PS3，次数→PM1 | 删除整张赋码表。保留查询示例与复发次数等原始信息，补一句"这些材料由统一 ACMG Skill 评估"。 |
| DisGeNET 表：分数→PP4／Supporting | 删除 ACMG 代码和证据强度映射；仅说明返回的是关联分数及来源。 |
| 调控预测说明中的 `PS3_supporting / PP3` | 删除代码映射，说明输出为预测效应量，不能在资料收集阶段决定证据代码。 |
| SAE 表的 `ACMG line` 列及"加强 PP3"说明 | 表格统一为"类别／预测的机制变化"两列；无可解释变化只记录为观察结果。 |
| ClinGen 表已删单元格但仍保留 `ACMG Impact` 表头 | 整理为"Classification／Meaning"两列，逐行对齐。 |
| SpliceAI 说明重复列出 PP3/BP4 数值阈值 | 改为统一 `SVI_REFERENCE.md` 链接，保留工具原始分数说明。 |

不要新增另一套"简化规则"，也不要为了避免赋码而删除查询参数或真实返回字段。

### A2. 收集示例：删除正文中的赋码与状态判定

修改 `EXAMPLES.md`。

- `Supports PM2 (absent from controls)` 改为仅记录数据库版本、未检出结果与覆盖信息。
- `PM1 applies (moderate)` 改为"Collected structural observations"，保留位置、结构和热点观察，不预判 PM1 或强度。
- `PS3: Not directly applicable` 改为"本示例未收集到该具体变异的直接功能实验"。
- `PS1: Not applicable` 改为"待评估变异与比较变异的氨基酸改变不同"。
- 检查四个案例的标题、摘要、表格、正文和交接段，不能只检查结尾。
- 保留明确归属的 ClinVar/VCEP 分类、外部 review stars 和原始预测标签；这些不属于本流程自行评级。

### A3. 入口 Skill：只记录冲突，不决定权重

修改同目录 `SKILL.md`。

- 删除"流行病学证据优先于体外实验"的原则及报告模板中的相同结论。
- 冲突小节只保留：分别记录研究对象、样本量、统计结果、实验验证质量，以及两类结果的具体冲突；由统一 ACMG Skill 按适用规范评估。
- 删除 `Predictor Weighting` 小节中的 AUC 排名、`weight highest` 和 `lean toward REVEL`。替换为一句：记录原始结果，工具选择与校准规则遵循统一参考，不在看到结果后改变评估方案。
- 删除调控预测段落中"这是 ACMG PS3/PP3 所需证据"的映射。
- 不再复制 CSpec 裁决流程；保留统一流程的链接和入口处的交接要求。

### A4. 针对遗漏补一个小型回归检查

在现有 `tests/unit/test_variant_interpretation_code_patterns.py` 增加一个测试，扫描上述三个文件，检查已确认的旧捷径是否残留。测试应汇总全部命中位置，便于一次看到遗漏。

检查标记至少包含：

| 文件 | 已确认的旧标记 |
|---|---|
| TOOLS_REFERENCE | `COSMIC Evidence for ACMG`、`DisGeNET Score for ACMG`、`Mapping SAE categories → ACMG support`、`(PS3_supporting / PP3)` |
| EXAMPLES | `PM1 applies (moderate)`、`Supports PM2 (absent from controls)`、`**PS3**: Not directly applicable`、`**PS1**: Not applicable` |
| SKILL | `Epidemiological data generally trumps`、`epidemiological evidence is weighted more heavily`、`lean toward REVEL`、`the mechanistic evidence ACMG PS3/PP3 actually needs` |

- 修改前确认检查失败，修改后通过。
- 保留既有示例编译、假返回和独立分类器删除检查。
- 人工逐段复核修改后的含义，不能仅更换措辞以绕过字符串检查。
- 测试明确标注为文档契约检查，不代表 LLM 行为验收。

**提交 A：** 旧入口残留评估规则清理及针对性回归检查。

## 3. B：同步两个 Skill，并补内容一致性检查

必须同时覆盖：

1. `tooluniverse-acmg-variant-classification`
2. `tooluniverse-variant-interpretation`

目标为 `plugin/skills/` 和 `plugins/tooluniverse/skills/` 下的对应目录。

### B1. 先补一个会失败的同步检查

仍使用现有文档测试文件，不新增同步框架：

- 对上述两个 Skill 的全部 Markdown 文件检查目标文件存在。
- Claude 副本与根目录源文件全文一致。
- Codex 普通 Markdown 文件与源文件全文一致。
- Codex `SKILL.md` 的 frontmatter 之后正文与源文件一致；frontmatter 的合法性继续交给已有 `test_codex_plugin.py` 检查，允许正式脚本改写描述及移除 Claude 标记。
- 修改前确认测试能抓到 ACMG `SKILL.md`、`SVI_REFERENCE.md` 未同步的问题。

核心比较逻辑（见计划原文，`repo` 使用当前测试已有的仓库根目录定位方式）。

### B2. 执行同步

- Claude 只同步这两个目录，排除缓存与测试产物。
- Codex 使用现有 `scripts/sync-codex-plugin-skills.sh`：
  - `CODEX_PLUGIN_SKILLS_DEST` 指向新建临时目录；
  - `CODEX_PLUGIN_PYTHON` 指向目标工作区 `.venv/bin/python`；
  - 脚本成功后，只回填两个目标 Skill。
- 不裸复制 canonical `SKILL.md` 覆盖 Codex frontmatter。
- 运行新增同步检查与 Codex 插件测试。
- 在三个版本中直接核对：PP3 同义变异剪接路径、BP2 trans 限制、BP3 无已知功能条件，以及任务 A 的清理结果。
- 检查未改动其他 Skill。

**提交 B：** 两个 Skill 完整同步及内容一致性检查。

## 4. C：修正当前状态记录并完成验收

只更新现有当前状态记录，不再增加逐轮流水账。

- 将"13 个测试文件"改为命令展开后的实际文件数；当前命令是 **22 个**。
- 环境说明改为："观察到 `.pth` 的 `UF_HIDDEN` 标记清除后再次出现，具体来源未确定。"删除 iCloud 已被确认为原因的表述。
- 修正仍指向"第 5 节验收结果／失败清单"的引用；当前内容位于第 6 节。
- 明确记录本轮补齐了 ACMG 分发同步和旧入口残留；列出实际实现提交、测试命令与结果。
- 真实 LLM 工作流继续标为未验收，不新增宿主安装或配置工作。

### 验证顺序

1. 先运行修改后的文档测试与 `tests/unit/test_codex_plugin.py`。
2. 再运行当前实施记录第 3 节的完整回归命令，保留 `--maxfail=0 --no-cov -p no:cacheprovider`。起点为 **673 passed、8 skipped、1 deselected**；本轮数字以实测为准。
3. 在临时快照完成 Claude 插件构建与测试；补入对应提交的 `tests/conftest.py`、插件测试文件和 `pytest.ini`，显式关闭 maxfail。与官方固定基线比较完整失败集合。
4. 修改的测试文件通过现有 ruff 检查；两个范围的 `git diff --check` 均通过。
5. 确认生产代码、两个工具 JSON、生成文件及依赖文件相对本轮起点无变化，`uv.lock` 仍与官方基线一致。

Claude 插件既有基线为 **82 passed、6 failed、1 deselected**。六项是 `uvx_refresh_flag`、两个 `example_params_match_schema`、`slash_commands_documented`、两个 `mentions_tu_run_cli`；不在本轮修复，只要求无新增失败。

**提交 C：** 当前状态记录与实际验收结果。

## 5. 完成标准

- 旧入口不再自行决定证据代码、强度、适用状态或证据优先级。
- 两个 Skill 的源文件、Claude 副本、Codex 副本全部通过内容一致性检查。
- 三处科学修正在全部分发副本中可见。
- 新增检查证明能检出本轮遗漏；完整回归无新增失败。
- 当前状态记录与真实文件、命令、统计一致。
- 工作区干净，旧工作区保持原状，未推送。

最终交接按 **修改位置 → 实际差异 → 验证结果 → 剩余限制** 报告；测试通过不能代替内容核对，也不能代替真实 LLM 调用轨迹。
