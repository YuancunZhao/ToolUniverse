# ACMG/CSpec 遗漏修复与冗余清理计划

> **交给执行 agent：** 使用 executing-plans，按 A→B→C→D 顺序实施，每项独立提交。先保存本计划，再修改代码或文档。不要重复执行历史计划。

**目标：** 补齐三处科学规则，移除旧入口中残留的独立赋码和分类逻辑，缩小相对官方 upstream 的差异，并压缩历史文档。

**方案：** 保留现有"Skill 评估证据、计算器校验并组合"的架构。清理重点是重复规则、旧示例、无关格式变化和历史过程记录；不重写运行时校验。

## 1. 起点、边界与交接约定

| 项目 | 固定值 |
|---|---|
| 官方 upstream | **https://github.com/mims-harvard/ToolUniverse** |
| 官方固定基线 | `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6` |
| 本轮起点 | `77f9aa9ce658c088cd6b67f9bce408895c1c9cc8` |
| 工作区 | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 分支 | `codex/acmg-svi-cspec-lightweight`，继续使用，不再新建 |
| 本计划保存位置 | `docs/superpowers/plans/2026-09-10-acmg-svi-cspec-cleanup.md` |

- 核对 HEAD、工作区状态、远程地址与 worktree 列表。起点有变化时先检查新增差异，不得 reset 或覆盖已有工作。
- 仅清理本次 ACMG/CSpec 改造涉及的内容，不扩展为整个 ToolUniverse 的重构。
- 保留现有工具名称、输入输出 Schema、错误类型、暂停原因、28 项记录契约、来源追踪和组合规则。
- 保留官方锁文件；不修改 `pyproject.toml`、不重装现有 `.venv`。测试直接使用 `.venv/bin/python`，涉及 uv 的命令必须带 `--frozen`。
- 不修改旧工作区 `/Users/zhaoyuancun/Documents/ToolUniverse-fork`、用户 MCP 配置或依赖；不推送。
- 不新增规则引擎、通用校验框架、插件层或文档生成系统。三处 Skill 副本是 upstream 的分发方式，继续保留。

**接口变化：** 无生产 API 变化。只删除文档中的两个独立示例函数；已确认它们没有仓库内调用者。

## 2. A：补齐科学规则，明确唯一维护位置

主要修改 `skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md`。

### A1. 落实三项遗漏

| 条目 | 必须写入的规则 | 验收反例 |
|---|---|---|
| PP3 | 同义变异不适用氨基酸改变预测，但可以通过非 canonical ±1/2 的剪接预测进入 PP3。保留 canonical 位点走 PVS1、RNA 结果替代相应预测证据的规定。 | 非 canonical 同义变异、SpliceAI 0.8、没有 RNA 结果：不能仅因"同义"排除 PP3。 |
| BP2 | 分开描述两条路径：与致病变异处于 trans 时，限定完全外显的显性基因／疾病；处于 cis 时按原始规则适用于任意遗传方式。删除以"未发病"替代 trans 适用条件的标题。继续要求相位证据。 | 低外显率疾病中的未发病携带者：不能据此自动赋 BP2；未知相位不能当作已确认 cis/trans。 |
| BP3 | 框内插入缺失必须位于**无已知功能的重复区域**。重复或低复杂度注释本身不足以支持 BP3。 | 功能性重复区域中的框内缺失：不得仅凭 repeat 注释赋 BP3。 |

依据：Walker 2023（PMC10357475）、ACMG/AMP 2015 Table 4（PMC4544753）。

- 保留已经正确的 PM3 算术修正，不重新改动其阈值。
- 对照上述反例检查实际文件差异，记录修正后的段落位置和来源。不能用 pytest 通过代替科学内容核对。

### A2. 减少规则在多个文件中的重复维护

- ACMG `SKILL.md` 保留完整工作流、CSpec 候选裁决、优先级表、计算器调用和结果报告要求。
- `SVI_REFERENCE.md` 保留逐项证据规则；开头的重复优先级表、状态表改为指向同目录 `SKILL.md` 的链接，并保留简短的 CSpec 优先提示。
- 将 `SKILL.md` 中连续两段"特殊组合暂停"的说明合并为一段，保留 `combination_method` 的填写要求与 `needs_review` 行为。
- 不删除候选裁决、材料完整性、禁止通用规则绕行、证据材料中指令不可信等必要要求。

**交付：** 三项科学修正实际落盘；工作流与逐项规则各有明确维护位置。

## 3. B：删除旧入口的重复赋码和分类逻辑

范围限定为 `skills/tooluniverse-variant-interpretation/`，随后同步镜像。

### B1. 清除仍可绕开统一流程的示例代码

在 `TOOLS_REFERENCE.md`：

- 删除 `calculate_acmg_classification(evidence_codes)` 整个示例。它仍自行应用旧组合表并返回终判。
- 删除 `get_multi_predictor_evidence(tu, variant_info)` 整个示例。它仍通过投票生成 `acmg_pp3`、`acmg_bp4`。
- 分别替换为统一 ACMG Skill、现有 `CODE_PATTERNS.md` 原始预测收集示例的链接。不要保留转发包装函数。
- 删除 `ACMG Code Quick Reference`、`Concordance for PP3/BP4` 和重复的预测阈值总表。保留各工具章节中的原始分数、供应商标签、参数与查询示例。

### B2. 清除说明文字里的第二套规则

| 文件／位置 | 修改 |
|---|---|
| 旧入口 `SKILL.md` 的基因频率阈值小节 | 删除固定 BS1 阈值、近似公式和"超过已知致病变异最高 AF 即可"的建议；转到统一参考。 |
| `SKILL.md` 的冲突处理、预测器权重和特殊场景 | 保留事实收集与冲突记录；删除自行决定证据优先级、强度或直接赋码的说明。 |
| `SKILL.md` 与 `TOOLS_REFERENCE.md` 的调控预测、表达语境 | 保留预测输出含义；删除"预测即 PS3/PP3""近零即 BP4""表达受限即 PP4"等直接映射。 |
| `TOOLS_REFERENCE.md` 的频率、ClinGen、COSMIC、DisGeNET 表 | 删除 ACMG 赋码列和固定触发规则；保留查询、返回字段和数据库背景。 |
| `ACMG_CLASSIFICATION.md` | 缩为导航页：统一流程、逐项参考、工具资料三个链接及简短说明，不再维护另一份算法、证据阈值或分类置信度表。 |
| `CHECKLIST.md` 与各文件引用 | 检查项改为核对统一流程的评估与计算器输出；更新仍指向已删除算法或阈值表的引用。 |

不禁止出现 ACMG 代码名称；禁止旧入口自行作出代码、强度和终判决定。

### B3. 压缩旧示例，保留资料收集价值

- `EXAMPLES.md` 的四个案例改为**资料收集示例**，明确内容是固定示例，不能视为当前数据库查询结果。
- 保留变异资料、查询方法、原始分数和明确归属的外部数据库分类。
- 删除案例自行生成的证据计分表、组合表、终判、星级置信度、自动升级规则，以及依赖这些模拟终判的处置建议。
- 同时清理摘要、标题、正文中的相同结论，不能只删除末尾分类章节。
- 文件末尾只保留一次交接说明：进入统一 ACMG Skill，读取适用规范，完成 28 项评估，调用计算器。

尤其核对目前仍存在的 PM2 Moderate、四预测器一致赋 PP3、三 Moderate 加一 Supporting 给终判，以及"RNA 显示跳跃即升级"等内容。

### B4. 使用现有测试防止已删除代码返回

在 `tests/unit/test_variant_interpretation_code_patterns.py` 增加一个小型回归检查，先确认旧文件下失败，再删除：

```python
def test_tool_reference_has_no_alternative_acmg_evaluator():
    text = (SKILL_DIR / "TOOLS_REFERENCE.md").read_text()
    forbidden = (
        "def calculate_acmg_classification(",
        "def get_multi_predictor_evidence(",
        "'acmg_pp3'",
        "'acmg_bp4'",
    )
    for marker in forbidden:
        assert marker not in text
```

- 保留现有示例编译和假返回验证，不新建文档检查框架。
- 人工复核六个入口文件的全部 ACMG 相关段落，防止仅消除测试匹配的字符串。
- 明确该测试验证文档契约，不代表真实 LLM 已遵守流程。

### B5. 同步分发副本

- 修改以根目录 `skills/` 为准，仅同步本轮涉及的两个 Skill。
- Claude 副本同步到 `plugin/skills/`，排除缓存与测试产物。
- Codex 使用现有 `scripts/sync-codex-plugin-skills.sh`，通过 `CODEX_PLUGIN_SKILLS_DEST` 指向临时目录、`CODEX_PLUGIN_PYTHON` 指向本工作区 Python，再回填两个目标 Skill。
- Codex frontmatter 必须保留正式同步脚本的归一化结果；不得裸复制 canonical `SKILL.md` 覆盖。
- 核对无其他 Skill 被同步改动，分发包内的相对链接有效。

**交付：** 旧入口负责资料收集，统一 Skill 负责证据评估，生产计算器负责组合；不再残留第二个分类器。

## 4. C、D：缩小 upstream 差异并压缩历史

### C. 恢复两个 JSON 的原有格式

涉及：

- `src/tooluniverse/data/clingen_tools.json`
- `src/tooluniverse/data/clinical_calculators_tools.json`

已确认：相较官方基线，每个文件都只新增一个工具，原有工具的 JSON 内容完全未变。大量差异来自整文件重排。

- 使用官方基线的原文作为底稿，只插入当前新增工具对象；不要对整个文件重新 `json.dumps`，否则仍会改写原有紧凑数组。
- 保持新增对象当前的完整语义、字段顺序与描述。
- 先断言原有对象与基线逐项相等、唯一新增对象确为对应新工具，再写入。
- 核对修改前后整个 JSON 解析结果相等。
- 不重新生成包装与 metadata：本任务只改变格式，工具接口没有变化。

### D. 将历史文档归并为当前状态记录

按用户选择，同时压缩历史文档。

- 重写现有 `2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`，只保留：官方仓库、基线、当前实现提交与架构；已落实的科学修正及来源索引；可复跑的验收命令、实际结果和日志位置；特殊组合、真实 LLM 验收、锁文件及环境的现存限制；历史追溯方法。
- 从当前树删除五份已完成的旧计划（lightweight / repair / remaining-fixes / final-fixes / review-fixes），详细过程由 Git 保存。
- 保留本轮计划。历史记录注明可通过 `git show 77f9aa9c:<原路径>` 查看，删除指向已移除文件的普通链接。
- 压缩 `docs/acmg_svi_cspec_local_run.md`：保留当前环境检查、SDK/MCP 启动及测试命令；删除重复科学规则和已失败的环境试验过程。
- 修正开头裸 `uv sync` 与后文冻结锁要求的矛盾。现有环境直接使用；首次安装命令必须带 `--frozen`，不得宣称已验证恢复锁后的重装。
- 保留隐藏 `.pth` 的已观察事实及当前应对方法；删除未经证实的具体进程归因。
- 修正"五项插件失败"记录，记录完整失败集合，不再以 conftest 解释漏项。

**本轮不清理的内容：** 生产输入校验、CSpec 损坏披露、材料缺口、重复事实检查、暂停原因和跨接口测试。

## 5. 验收、提交与完成标准

### 自动化回归

在目标工作区执行计划所列 13 个测试文件（`--maxfail=0 --no-cov -p no:cacheprovider`）。

- 起点实测是 **672 passed、8 skipped、1 deselected**；新增检查后以实际输出计数，不能复制旧数字。
- 修改的测试文件通过现有 ruff 检查。
- 三个科学反例、旧示例删除、所有镜像与链接分别人工核对。
- 两个 JSON 与本轮起点解析结果完全相同；`uv.lock` 与官方固定基线一致。
- `git diff --check` 对本轮起点和官方固定基线两个范围均通过。

### Claude 插件对照

- 在临时目录分别构建官方基线和当前实现提交的快照；`git show` 补入 `tests/conftest.py` 和 `tests/test_claude_code_plugin.py`。
- 双侧使用同一个现有 Python 执行 `tests/test_claude_code_plugin.py --maxfail=0 --no-cov -p no:cacheprovider --tb=short`。
- 保存完整命令、退出码和输出，不能只保存前五项失败。
- 上轮完整对照为双方 **82 passed、6 failed、1 deselected**；六项既有失败为 uvx_refresh_flag、example_params_match_schema[research/researcher]、slash_commands_documented、mentions_tu_run_cli[research/researcher]。验收要求是无新增失败；不在本轮修复这六项上游问题。

### 提交与交接

四个独立提交：A 科学规则与职责归并 → B 旧入口清理及回归检查 → C JSON 格式恢复 → D 文档压缩与验收记录。

最终交付必须列明：三处科学规则的最终位置和反例核对结果；删除了哪些重复实现、哪些必要校验保留；实际测试结果与完整插件失败集合；清理前后的差异统计（文档、JSON、生产代码）；当前 HEAD、干净工作区、旧工作区未变及未推送状态；真实 LLM 工作流仍未验收。

**完成标准：** 三处遗漏修正落盘；旧入口不再自行赋码或分类；两个 JSON 无无关格式变化；历史文档完成归并；公共接口和已有安全行为保持不变；相关验证无新增失败。
