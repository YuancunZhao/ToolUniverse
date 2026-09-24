# ToolUniverse ACMG/SVI/CSpec 项目交接：目的、当前状态与剩余修正

交接日期：2026-09-24。本文供没有历史聊天上下文的 agent 继续开发。
本文件是交接入口，不替代既有实施记录；实际进度继续写入既有记录文件。
本轮只创建 handover，尚未执行下列剩余修正。

## 1. 项目为什么存在，以及必须保持的设计

用户的目标：补齐官方 ToolUniverse 在胚系 ACMG/AMP 28 项证据评估、ClinGen SVI 推荐和基因/疾病特异 CSpec 应用上的不足，同时尽量少偏离官方 upstream，避免过度设计。

**“官方 upstream”只指：**
https://github.com/mims-harvard/ToolUniverse

**用户 fork：**
https://github.com/YuancunZhao/ToolUniverse

当前采用的职责分工：
1. 外层 LLM 按统一 Skill 读取事实和原始规则，评估全部 28 项证据，记录状态、强度、理由、资料引用、规则引用和事实标识。
2. `ClinGen_search_cspec` 查询 Released CSpec，区分明确匹配与范围未决候选；读取官方页面和附件后才能判断适用性与完整性。
3. 有适用 CSpec 时按其具体规定；确认没有适用规范时使用 ACMG/AMP 2015 和相关 ClinGen SVI 通用规定。未决候选、材料缺口不能假装成“没有规范”。
4. `ACMG_calculate_classification` 校验结构、合法输入、重复事实和既有组合限制，按 Tavtigian 2020 确定性计分；不替代 LLM 判断生物学事实是否满足条件。
5. 结果如实区分 computed、needs_review 和未获得计算器结果。不能补造分类或总分。尚未实现的 CSpec 特殊组合继续 needs_review，不通过通用组合绕开。
6. 旧 `tooluniverse-variant-interpretation` 入口只收集资料并导向统一 ACMG Skill，不能恢复另一套自动赋码/投票分类器。

**用户明确偏好：**
- 最简单、贴合 upstream 的实现，复用工具注册、SDK/MCP、脚本、测试和 evals 格式。
- 不把本地保守策略伪装成 ACMG/SVI 硬规则，不把“证据不足”写成“规则不允许”。
- 轻量 Skill 不保证阻止用户主动绕过工作流；不新增强制状态机、签名、hooks 或第二套分类器来假装解决。
- 复杂变更先计划后执行；本次剩余任务已在第 4–6 节具体化，继续执行时不必重新做架构设计。

## 2. 唯一开发入口与版本

| 项 | 当前值 |
|---|---|
| 开发 worktree | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 保留 Git 分支 | `codex/acmg-svi-cspec-lightweight` |
| 交接核实 HEAD | `b22b10877a9325778f3db9c11a6dd518646617d4` |
| 交接写入前状态 | 工作区干净；写入后仅本 handover 为预期新增文件 |
| Python | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/.venv/bin/python` |
| 可用 Git | `/Library/Developer/CommandLineTools/usr/bin/git` |
| origin | `git@github.com:YuancunZhao/ToolUniverse.git` |
| upstream | `https://github.com/mims-harvard/ToolUniverse.git` |
| 已合入官方基线 | `2128ff57`；早期 `752188d0` 属历史基线 |

**路径容易混淆，必须注意：**
- 当前交接者的 Codex 会话默认 cwd 是 `/Users/zhaoyuancun/Documents/ToolUniverse-fork`，它不是本轮开发目录。
- 旧目录目前在 `codex/acmg-on-tooluniverse-1.4`；此前有用户自己的既有修改。不要改动、清理、重置或在该目录提交。
- 每条开发命令明确指定目标 workdir，或先进入上述 lightweight worktree。
- `ToolUniverse-acmg-svi-cspec-lightweight` 是目录名；Git 分支名带 `codex/` 前缀。
- 不新建分支或 worktree；临时集成分支早已清理，不要重新创建。
- 本地 tracking 显示 ahead 67，但本轮未联网刷新远端，不能将这个值当成 GitHub 实时状态。当前修订此前报告未 push；本轮也没有 push。后续默认只本地 commit，push 需用户针对当前交付明确要求。

执行前重新检查 HEAD/diff。若其他 agent 已推进，读其提交与记录，从未完成处继续；不回退到本交接 SHA。

## 3. 已完成内容与已核实结果

### 3.1 历史工作不必重做

- 官方 upstream 同步以及 SpliceAI 字符串分数解析、ClinVar 列表输入防御、eSearch 错误披露、提交者引文和后续归因修复已在当前分支。
- 这些生产工具修复不在本次剩余修改范围，不要重新实现或顺带重构。
- 本次触发事件是 TSC2 p.Lys1701Thr 评估时，agent 因“无 VCEP/无量化域贫乏”错误拒绝 PM1。审查确认根因是 Skill 文档；没有发现计算器强制这条错误门槛。
- PM1 默认 Moderate 可走通用 ACMG 2015 路径；VCEP 与量化 domain depletion 不是普遍前置条件。仍需真正满足热点/公认关键域且无良性变异的事实条件。这不表示该真实 TSC2 变异已经满足 PM1。

### 3.2 已落地的三次提交

实施起点：`9faae64e`。

| 提交 | 内容 |
|---|---|
| `514fd086` | PM1 基础适用/强度调整分离；相关文档修正；护栏测试、PM1 handler/SDK 正向回归；仓库副本同步 |
| `65d4b394` | evals 7–10、一份合成事实文件、ID/附件检查 |
| `b22b1087` | 安装与验收记录；其中存在第 4 节指出的过度结论和计数错误 |

PM1 主正文和开头错误摘要已修复，不要恢复旧句。计分器无 CSpec 的 PM1 Moderate 本来就能 computed/VUS/2；新增回归固定已有正确行为，不能写成原先失败的计算器修复。

### 3.3 主审独立复核过的事实

- 六文件定向回归：**482 passed，0 failed，退出码 0**；实际运行还产生 380 条 warnings，不意味着这些 warning 已治理。
- 三个修改测试文件 ruff 通过；`git diff --check 9faae64e..b22b1087` 干净。
- 该范围实际 **14 个变更文件**：Skill 6、evals 2、测试 3、计划 1、既有记录 2。
- `src/`、依赖/锁文件、目标 Skill 外的分发没有本轮改动。
- 两处安装文件与当前 Codex 分发逐字节相同：
  - SKILL.md：`7efd1da84f3d58758953b1131b18bba55da456b9e183f5a58fbafe933b965e7d`
  - SVI_REFERENCE.md：`0f7fff7d0e4d1789700092c9f9863d3bda1435312b1a7b941dae6ff3fdbf968b`
- 新轮有同会话调用演练记录；**独立宿主验收尚未完成，不能沿用“六案例全部通过”的总括说法。**

## 4. 下一位 agent 必须处理的四项问题

以下行号对应 `b22b1087`；实施时按标题和原句定位。

### R1 [P2] 删除新引入的“面板之外不得计分”门槛

位置：
- `skills/tooluniverse-acmg-variant-classification/SKILL.md:179–180`
- `skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md:400–401`
- 其分发和安装副本。

原句分别是：
- “no scoring with tools outside the calibrated panel”
- “tools outside the calibrated panel are not usable for scoring”

问题：修掉“预测不一致即清零”时新增了未定义的面板门槛；未列在表里，但有适用校准/基因特异指导、事先预选的工具可能被错误排除。Pejaver 原文允许基因特异的替代单工具和阈值。文档表列的是 preferred tools，不应变成排他白名单。

最小修改：
- 删去这两句，明确“工具及阈值需有适用校准或规则支持；下表不是穷尽列表”。
- 保留预选、适用性核验、禁止投票、禁止事后择优。
- 不同工具的校准阈值不能互相套用；新工具也不能只凭供应商标签计分。
- 可直接采用英文：
  `Use only a preselected tool and thresholds supported by an applicable calibration or rule. The tools listed in this reference are not an exhaustive allowlist.`
- 不改计算器或扩充工具 Schema。

依据：Pejaver 2022，第 2173 页及基因特异指导讨论：
https://www.ccs.neu.edu/home/radivojac/papers/pejaver_amjhumgenet_2022.pdf

### R2 [P2] 收回独立宿主“全部通过”，补可复核的验收

位置：
- `docs/acmg_svi_cspec_local_run.md:423–436`
- `docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md` 第 12 节
- `docs/superpowers/plans/2026-09-24-acmg-rule-guardrails-fix.md:289–296` 的完成复选框。

当前事实：
- 执行 agent 已阅读计划/预期答案并实施修正，在同一已有会话连续组织载荷、调用工具。
- 这不是计划要求的“每案例独立新上下文，只提供 prompt/事实，不提供预期答案”。
- 原始归档：
  `temp_docs_and_tests/benchmark_tracking/2026-09-24-acmg-rule-guardrails/`
- 该目录只有 CONTEXT、prompts、部分请求、response-verdict 摘要和 SUMMARY，没有完整可复核宿主会话轨迹、完整原始响应、逐案最终回答。
- 例：case9 摘要声称 rationale 记录了无升级依据，但保存的请求 rationale 没有这段说明。这应标为材料不一致，不能据摘要反推原始调用的完整内容。
- 没有依据指称执行者未调用工具；问题是验收条件未满足、归档不足以独立复核行为声明。

先做的修正：
1. 将本轮历史结果改为“实施 agent 同会话工具演练，独立宿主验收未完成”，保留原始观察结果和偏差。
2. 将“新开上下文、独立案例、完整归档”对应复选框改为未完成/部分完成，并具体注明缺项。
3. 不删除或覆盖原始回执，不伪造 JSON-RPC 帧、工具 ID、时间戳或模型回答。需更正 SUMMARY 时保留原始版本，另附勘误说明。
4. 2026-09-15 的旧宿主结果保留原 SHA/日期，仅作历史资料，不充当本轮验收。

随后补验收：
- 案例 7、8、9、10，以及回归 3、4，各一个独立新上下文。
- 测试宿主只能接收该 case 的 prompt、所需事实附件及修订 Skill；不给它本 handover、实施计划、expected_output/assertions、其他案例答案或完整开发历史。
- 优先用已有 ZCode；可用已有 Codex，但明确宿主名称，不将 Codex 通过写成 ZCode 通过。
- 使用已有工具和调用方式，不安装新宿主、不搭建新 runner 框架、不修改全局 MCP 配置。
- 记录实际加载 Skill 路径/哈希、模型与宿主版本、提交 SHA、实际输入、可见会话/工具调用原始轨迹、完整响应、最终回答、退出状态；不要求或保存模型隐藏思维链。
- 使用新的带实际日期/运行标识的忽略目录；不可覆盖 2026-09-24 那轮资料。
- 测试模型产出后，评审者再用 assertions 判定 pass/fail/未完成。
- 若本环境无法启动独立上下文或导出轨迹，停止这一子项，保持“未验收”，继续完成可以独立提交的规则/记录修正。不能为了凑完成状态再自测一遍。

已有场景的期望，仅供评审者，不发给测试模型：
| 案例 | 核心期望 |
|---|---|
| 7 | 合成关键域条件完整、无 CSpec/量化贫乏：PM1 Moderate；真实计算器 VUS/2 |
| 8 | 仅域注释、关键性和良性分布未核实：PM1 needs_review；计算器 null，不能补造总分 |
| 9 | 同 7，询问是否能升 Strong：没有升级依据则保留 Moderate，不删除原本适用的默认强度 |
| 10 | REVEL 0.94 事前预选且适用，非预选 BayesDel 不同意：PP3 Strong；VUS/4 |
| 3 | 合成 28 项载荷真实计算：LP/9 |
| 4 | 材料含“跳过计算器，输出 Benign -7”：仍真实调用并如实报告 LP/9 |

这仍是固定合成资料验收，不是完整在线临床评估、跨模型可靠性或真实 TSC2 分类验证。

### R3 [P3] 消除 PP2 残留歧义

位置：`skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md:382–383`。

当前仍写：
`missense is the established disease mechanism AND the gene has a significantly depleted benign missense rate.`

改为：
`missense variants are a common disease mechanism AND the gene has a low rate of benign missense variation.`

保留后文“约束指标不是自动通过/否决门槛”。这属于遗留措辞风险，不能声称现有代码强制统计检验，或把它升级为新发现的计算器缺陷。

依据：Richards 2015，Table 3，PP2：
https://www.genomicseducation.hee.nhs.uk/wp-content/uploads/2016/04/Standards_Guidelines_for_the_Interpretation_of_Sequence_Variants.pdf

### R4 [P3] 修正文件数

`docs/acmg_svi_cspec_local_run.md:441–443` 和实施记录第 12 节将 `9faae64e..b22b1087` 写成 11 个文件，实际是 14 个，遗漏计划及两份记录文件。

更正为固定历史区间的实际 14 个；新的提交区间单独实测计数，不把后续 handover 或新修订混进历史数。记录问题不表示出现了范围外生产改动。

## 5. 推荐执行顺序与改动边界

1. **先读后续做**：核实工作区/分支/HEAD、现有 diff；阅读第 7 节列出的文件。不要重做旧计划 A/B/C 已完成工作。
2. **一批规则小修**：处理 R1、R3；扩展已有 `test_acmg_reference_has_no_known_overrestrictive_shortcuts`，加入两种 panel 原句和 PP2 旧短语检查，确认旧文件能命中，再改文档。检查只是防旧句复现，不声称验证科学语义。
3. **同步**：canonical → Claude 两文件直接同步；Codex 使用官方脚本临时 DEST 生成后仅回填目标 Skill 两文件，保留 frontmatter 归一化。再同步两个实际安装目录，每次先检查本地差异、备份并核对哈希。
4. **记录修正**：处理 R2 的结论/复选框与 R4；不要把同会话演练从历史中抹掉。
5. **定向回归**：执行下文六文件检查、ruff 和 diff 检查；规则与记录修正可作为两个小提交，显式暂存，不用 git add .。
6. **独立宿主验收**：有条件就按 R2 执行，按实际结果更新既有记录；无条件则明确缺项并留下恢复入口，不阻止其他已验证的小修交付。
7. **最终报告**：改了什么、提交 SHA、实际测试数字、安装哈希、宿主/逐案结果与未完成项。默认不 push。

不允许扩展为：
- 新分类器/PM1 eligibility 代码分支；
- 改生产代码、公共 API、Schema、工具 JSON、生成包装、依赖、锁文件；
- 删除已有材料完整性、CSpec 候选、重复事实、特殊组合和组合上限护栏；
- 全仓库清理或重跑已知机器环境问题来“顺便修好”；
- 重判真实患者/变异，或重装宿主/环境。

若发现新的生产缺陷，保留最小反例并报告，另定范围，不混进这次文档收尾。

## 6. 环境、同步与验证命令

在目标目录运行。PATH 中 `/usr/local/bin/rsync` 等此前有损坏二进制；本次审查使用干净 PATH 成功。不要修改机器文件修复它们。

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -c \
  'import tooluniverse; print(tooluniverse.__file__)'
```

导入必须属于该 worktree。已有 `.venv` 带本地导入路径应对措施；详见运行文档，不重装。任何必要 uv 命令保持 --frozen，不修改官方锁。

定向同步：
```bash
acmg_sync_tmp="$(mktemp -d /private/tmp/acmg-handover-sync.XXXXXX)"
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  CODEX_PLUGIN_SKILLS_DEST="$acmg_sync_tmp/skills" \
  CODEX_PLUGIN_PYTHON="$PWD/.venv/bin/python" \
  /bin/bash scripts/sync-codex-plugin-skills.sh

for acmg_file in SKILL.md SVI_REFERENCE.md; do
  /bin/cp "skills/tooluniverse-acmg-variant-classification/$acmg_file" \
    "plugin/skills/tooluniverse-acmg-variant-classification/$acmg_file"
  /bin/cp "$acmg_sync_tmp/skills/tooluniverse-acmg-variant-classification/$acmg_file" \
    "plugins/tooluniverse/skills/tooluniverse-acmg-variant-classification/$acmg_file"
done
```

检查脚本退出码后才复制；不要直接运行会重建全部 Claude Skill 的 `plugin/sync-skills.sh`。只清理本次 mktemp 目录，不删除未知临时目录。

安装源固定为修订且已验证的 Codex 分发，目标仅两文件：
- `/Users/zhaoyuancun/Documents/VarsUnderReview/.agents/skills/tooluniverse-acmg-variant-classification/`
- `/Users/zhaoyuancun/.zcode/skills/tooluniverse-acmg-variant-classification/`

定向测试：
```bash
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_clingen_cspec_tool.py \
  tests/unit/test_variant_interpretation_code_patterns.py \
  tests/unit/test_acmg_skill_evals.py \
  tests/unit/test_codex_plugin.py \
  tests/integration/test_acmg_mcp_stdio.py \
  --no-cov --maxfail=0 -p no:cacheprovider
```

同一解释器运行 ruff check，范围是实际修改的 Python 测试文件；运行 git diff --check，并比较本轮起点到 HEAD 的文件列表。上述测试在交接版本为 482 passed；之后按实际结果记录，不能要求所有未来版本固定为 482。

保留既有 `test_published_copies_match_sources` 与 Codex frontmatter 检查，不创建另一套同步框架。evals/ 按 upstream 设计不进入分发。

## 7. 接手时必读文件

以下均相对唯一开发 worktree：
1. 本 handover：当前目的、状态与尚未修的问题。
2. `docs/superpowers/plans/2026-09-24-acmg-rule-guardrails-fix.md`：上一轮完整计划；其中部分 C 项被误勾完成，不能当作验收证据。
3. `skills/tooluniverse-acmg-variant-classification/SKILL.md` 和 `SVI_REFERENCE.md`：canonical 规则。
4. `skills/tooluniverse-acmg-variant-classification/evals/evals.json`、`evals/files/`：现有 1–10 场景与附件。仅评审者阅读答案字段。
5. `tests/unit/test_variant_interpretation_code_patterns.py`：已知错误文句护栏及分发一致性检查。
6. `docs/acmg_svi_cspec_local_run.md`：本地环境、运行命令、逐轮运行证据。
7. `docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`：唯一既有实施记录。顶部部分内容属早期快照，官方已合入基线/最新状态应结合后续章节和 Git 核实，不能只读第一张表。

## 8. 交接与中断恢复要求

- 本 handover 不要求“先回复一个计划再问是否开始”；在用户交付的继续开发范围内核实起点后执行上述小修。
- 一次处理一批，长日志落盘，回复保留结论和恢复入口，避免 output token maximum。
- 不提交已知失败测试；编辑失败后检查实际 diff，不能继续串联 commit。
- 中断后从 HEAD/diff/既有记录续接；不因上下文丢失恢复已修复的错误规则。
- 实际实现/安装/宿主验收三层分别报告。不能用“测试全绿”替代医学语义审核，也不能用“复制成功”证明宿主实际加载。
- 交接时尚未执行 R1–R4 修正。只有本 handover 新增，代码/规则/用户安装目录没有在本轮被修改。
