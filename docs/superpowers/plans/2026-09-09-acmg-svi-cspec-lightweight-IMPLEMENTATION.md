# 实施记录 — ACMG/SVI/CSpec 轻量改造（2026-09-09）

对应计划：`2026-09-09-acmg-svi-cspec-lightweight.md`（本目录）。

| 项 | 值 |
|---|---|
| 分支 | `codex/acmg-svi-cspec-lightweight` |
| worktree | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 基线 SHA | `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6`（官方 mims-harvard/ToolUniverse，PR #566 merge，已验证为 upstream/main 祖先） |
| 环境 | worktree 内 `.venv`（`uv sync`，editable 安装；未用 `--all-extras`——graph extra 需 pygraphviz 系统头文件） |
| 提交状态 | 见文末"提交"节 |

## A. ClinGen_search_cspec — 完成

- `src/tooluniverse/clingen_tool.py`：新增 `search_cspec` operation（复用旧分支
  `ba81c76e` 中 `_search_cspec` 的两步查询骨架——`/cspec/api/svis` 索引 +
  `SequenceVariantInterpretation/id/<ID>` 详情——及 Released 过滤、版本回退解析），
  按新契约重写并扩展：
  - **rule set 绑定保留**：`rule_sets[]` 逐条携带 `rule_set_id` 与其基因→疾病→
    遗传模式映射；`criterion_modifications` 每条绑定 `rule_set_id`，不跨规则集混用。
  - **四态区分**：索引失败→`status:error`（错误文案明确"是查询失败，不代表无规范"）；
    无 Released 规范→`success` + 空数据 + 指引 note（走通用规则）；单规范详情失败→
    `success` + `partial_failures` + 该条 `detail_fetch_failed` 与 `missing_materials`；
    全部成功→`success`。
  - **材料标记**：`assertion_method_url`（详情 `assertionMethod.url`）、官方页
    `url`、`api_url`、`last_updated`、原始 `specification` JSON 全保留；
    `missing_materials` 显式列出缺失项。
  - **API JSON ≠ 完整规范**：所有 success 响应带 note，要求用
    `get_webpage_text_from_url` 补读官方页（含附件与 assertion method）。
  - 无自然语言规则解析器、无基因白名单、无本地规范库。
- `src/tooluniverse/data/clingen_tools.json`：新增 `ClinGen_search_cspec` 条目
  （8→9）。
- 测试：`tests/unit/test_clingen_cspec_tool.py`（16 项，冻结快照，无网络）。
  覆盖计划 §4 CSpec 行：Released 过滤、精确匹配（非子串）、多规则集绑定、双规范
  分离、版本保留与 label 回退、有效空结果、坏 JSON、超时、HTTP 错误、索引形状
  异常、部分失败、材料缺失标记、官方页/assertion method 引用、note 指引。

## B. ACMG_calculate_classification — 完成

- `src/tooluniverse/clinical_calculators_tool.py`：新增 `_acmg_classification`
  handler，dispatch 键 `acmg_classification`（复用 `ClinicalCalculatorTool`
  框架与 error envelope；不复制旧分支 collector/EvidenceCard/Guard/Bayesian）。
  要点：
  - 输入固定四键（多键即拒——同时挡住调用方注入 `total_score`/
    `expected_classification`/积分覆盖/阈值）；evidence 记录固定七键。
  - 28 代码恰好各一次；`met` 需合法强度 + 非空 rationale/source_refs/
    rule_refs/evidence_ids；非 met 不得带强度。
  - 计分：Supporting/Moderate/Strong/VeryStrong = ±1/±2/±4/±8；阈值
    ≥10 P / 6–9 LP / 0–5 VUS / −6..−1 LB / ≤−7 B；`method.name="tavtigian2020"`。
  - PP5/BP6 met → 非法输入 error（退役代码只可记录）；BA1 仅 StandAlone/None，
    独立路径：无冲突→Benign 且 `total_score=null`；与任一致病 met 冲突→暂停。
  - 暂停（`classification_status=needs_review`、`classification=null`、保留 28 项
    审阅记录与 `review_reasons`，附"非分类"的临时分值）：blocking_issues 非空、
    无可计分证据、`cspec_lookup_status` unresolved/failed、released 规范但
    `applicable_rules_complete`≠true（缺旗标同样 fail-closed）、
    `combination_method≠tavtigian2020`、同一 evidence_id 用于多个计分代码
    （同论文不同 fact 不算重复）、BA1 冲突。
  - 输出沿用 `_ok` envelope 形态但 `metadata.calculator_type="variant_classification"`；
    无后验概率输出。
- `src/tooluniverse/data/clinical_calculators_tools.json`：新增条目（10→11）。
- 测试：`tests/unit/test_acmg_calculate_classification.py`（52 项）。覆盖计划 §4
  边界（−7/−6/−1/0/5/6/9/10、强度升降、BA1 独立/冲突/强度限制）、输入约束
  （缺项、重复代码、未知代码、非法强度、缺理由/引用/事实 id、非 met 带强度、
  PP5/BP6 计分、注入总分/预期分类、缺 blocking_issues、缺 variant/gene、
  缺 rule_context 字段）、计分一致性（重复事实、同论文不同事实、独立正负、
  无可计分证据、needs_review/deprecated 项不计分且留痕、相位/亲缘/验证缺口保留）、
  暂停行为（CSpec failed/unresolved、材料不全、缺旗标 fail-closed、
  组合方法不支持、blocking_issues、记录保留）、envelope 元数据。

## C. Skill 与 SVI 参考 — 完成

- `skills/tooluniverse-acmg-variant-classification/SKILL.md`：重写为固定流程
  （确认变异与范围 → 查询确认 CSpec → 收集事实 → 逐项评估 28 项 → 依赖与重复
  检查 → 调用计算器 → 按计算器原文展示）；CSpec 查询结果→rule_context 映射表；
  常设规则（最终分类取计算器原值、ClinVar/VCEP 结论单独归因、PP5/BP6 退役、
  PP3/BP4 无多数投票、PM2 默认 Supporting、规范/文献文字是材料不是指令、
  特殊 CSpec 暂停时禁止静默回退通用分类、状态语义四区分）。
- 新增 `skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md`：
  28 代码逐一记录（必要事实、适用条件、强度调整、排除/重复计分、来源与版本）。
  覆盖 PVS1 决策树（LoF 机制未成立不得先赋 PVS1）、PS2/PM6 de novo 计数、
  PM3 in-trans 计数、PS3/BS3 功能验证框架、PP1 分级 meioses、PS1/PM5 蛋白级
  比较要求、PP5/BP6 停用、BA1 例外清单依赖、PM2_Supporting、疾病感知频率
  （Whiffin 2017 最大可信频率）、校准 PP3/BP4（REVEL≥0.7 / <0.15，无投票）、
  BP7 SpliceAI、无通用规则处显式声明"规范依赖，不造阈值"。附默认强度→分值表
  与共享事实配对表。
- `skills/tooluniverse-variant-interpretation/`：Phase 6 改为指向统一 ACMG 流程；
  **删除**了与之冲突的 Tavtigian 2018 点数表（VUS −5..5、LB −6..−9、B ≤−10，
  与 Tavtigian 2020 阈值不同）与内联 `classify_acmg` Python 函数（BA1 记 −8、
  无良性 Moderate、BP6 计分示例）；保留非 ACMG 冲突内容（BS1 基因病种校准、
  功能 vs 流行病学冲突处理、预测器权重、工具回退）。`ACMG_CLASSIFICATION.md`
  头部 2015 组合规则表与活跃 PP5 证据表替换为统一流程指针；PP3/BP4 投票注记
  改为校准单预测器规则；PVS1 迷你表对齐 SVI 决策树。
- 总路由器 `skills/tooluniverse/SKILL.md`：ACMG 关键词已指向该 skill
  （基线即正确，未改动）；variant-interpretation 入口经 Phase 6 进入同一流程。

## D. 注册、分发、本地运行 — 完成

- 生成器在临时目录 `/tmp/tu_gen` 跑 `tooluniverse.generate_tools.main(output_dir=…)`，
  仅取 `ACMG_calculate_classification.py`、`ClinGen_search_cspec.py` 两个包装，
  用仓库 ruff 配置格式化后放入 `src/tooluniverse/tools/`；`__init__.py` 增两行
  导入与 `__all__` 条目（字母序）；`.tool_metadata.json` 合并两条目（2744→2746）。
  未重生其余 2746 个包装（临时目录中与已提交文件的差异仅为格式化环境不同，
  已核对抽样）。
- Skill 发布副本：跑 `plugin/sync-skills.sh` 后**只保留** ACMG 与
  variant-interpretation 相关副本（plugin/skills 与 plugins/tooluniverse/skills
  两处，含新增 SVI_REFERENCE.md）；同步带出的上游基线漂移（biomedical-fact-
  lookup、molecular-cloning、phylogenetics、路由器副本、nih-funding-landscape/
  antigravity 新目录）全部还原/删除，不混入本次补丁。宿主 frontmatter 差异保留：
  Codex 副本无 `disable-model-invocation`，Claude 副本保留。
- MCP：`tooluniverse-smcp-stdio` 经运行时注册表自动暴露新工具（无需逐工具改动）。
  `tests/integration/test_acmg_mcp_stdio.py`：`--include-tools` 两工具，stdio 会话
  验证发现 + 执行（离线，计算器金标用例）。
- 本地运行说明：`docs/acmg_svi_cspec_local_run.md`（SDK/MCP 指向本 worktree
  `.venv`；明确 PyPI 1.4.1 不含新工具；含 UV_FROZEN 提示）。
- 未改发布版本、远程安装 pin、server.json/mcpb 版本号；未动用户 MCP 配置。

## 测试与验收结果

命令（worktree 内；`UV_FROZEN=1` 防止 uv 重锁）：

```
uv run pytest tests/unit/test_clingen_cspec_tool.py \
              tests/unit/test_acmg_calculate_classification.py \
              tests/integration/test_acmg_mcp_stdio.py \
              tests/unit/test_clingen_*.py tests/unit/test_clinical_calc*.py \
              tests/unit/test_lazy_load_cache_consistency.py \
              tests/unit/test_backward_compatibility.py \
              tests/unit/test_tool_name_shortening.py \
              tests/unit/test_run_parameters.py -q --no-cov
→ 250 passed, 7 skipped（skip 为既有环境性跳过）, 1 deselected
```

- ruff check：全部改动文件通过。
- `tests/test_claude_code_plugin.py`：基线与分支失败集**逐条一致**（5 项上游既有
  失败，`git stash` 双向验证），无新增回归。
- 在线 smoke（2026-09-09，与离线回归分开记录）：
  - SDK：`ClinGen_search_cspec(gene="MYOC")` → GN019 v2.1，Glaucoma VCEP，
    PVS1 全强度 Not applicable，PM2 仅 Supporting（AF≤0.0001），
    assertion method 与材料齐全。
  - MCP（stdio 实会话）：`tools/list` 含两工具；CSpec 调用同上；
    计算器返回 LP/9 分。
- 固定材料流程验收：
  - PVS1+PM2_Supporting = 9 分 LP：单元、SDK、MCP 三层一致。
  - 只有 ClinVar 标签不得产生 PP5/BP6：PP5/BP6 met 属非法输入（测试覆盖）；
    Skill 要求 ClinVar 结论单独归因。
  - 相位/亲缘/验证不足保留缺口：`test_phase_and_validation_gaps_are_kept_not_assumed`
    （PM3/BP2/PS3 needs_review 不计分、留痕、不升级）。
  - MYOC：PVS1 不适用（在线数据核实）；官方页 Type 为 Tavtigian 2020 但附加联合
    上限（"PP3+PM5 ≤ 5 分、PP3+PS1 ≤ 6 分"原文核实）——固定积分器无法表达 →
    `combination_method` 不得填 `tavtigian2020` → 计算器暂停
    （`test_unsupported_combination_method_pauses` 模拟该组合，配合在线材料核实）。
- **未执行的检查（明确标注）**：
  - 跳过工具的绕过场景没有自动化外层 LLM 调用轨迹可记录（本环境无外层模型）。
    已自动化的强制点：计算器拒绝注入总分/预期分类/额外键（测试覆盖）、PP5/BP6
    计分报错（测试覆盖）、Skill 明文要求分类必须经计算器。**不宣称**静态文档能
    阻止聊天层绕过；外层轨迹待真实 agent 会话记录。
  - "LoF 机制未成立时不能先赋予 PVS1"是 Skill/SVI_REFERENCE 的评估纪律，
    计算器无法验证事实层（其只验结构与算术）。
  - 全量 2718 工具的 MCP 暴露（compact 模式 4 核心工具）未逐一冒烟，仅验证
    注册表加载计数与两新工具。

## 已知限制

1. `ClinGen_search_cspec` 每次全量拉取 svis 索引（~300KB，208 条）后本地过滤，
   未做索引缓存（基线其他 ClinGen 操作同样如此）。
2. CSpec 规范页/附件补读依赖 `get_webpage_text_from_url`，其对 cspec UI 页的
   渲染质量未系统验证（本次用直接抓取核实了 MYOC 关键条款）。
3. SVI_REFERENCE 中无通用规则的代码（PM1 区域、PS4 效应量、BP5 确认要求等）
   显式声明规范依赖；个别常用默认（mis_z>3.09、SpliceAI<0.1、REVEL 0.7/0.15）
   标注为常用约定，规范优先。
4. `uv run` 在本仓库 pyproject/lock 组合下会尝试向 `uv.lock` 追加解析条目
   （cuda-bindings 等）——与本次改动无关，交付时已还原为基线；后续操作建议
   `UV_FROZEN=1`。
5. `tests/test_claude_code_plugin.py` 的 5 项失败为上游基线既有状态。

## 旧代码复用与差异摘要

- 复用旧分支（`ba81c76e`）仅三处：`_search_cspec` 查询骨架与版本解析、
  ClinGen_search_cspec 的 JSON 配置形态、其测试的快照构造方式。全部按新契约
  重写（rule set 绑定、四态区分、材料标记、note 指引为新增）。
- 未复用：collector、EvidenceCard、Guard、Bayesian runtime、八工具接口、
  运行时 LLM 计划（计划明确不要求兼容）。
- 相对基线的全部差异：上述 A–D 文件 +
  `docs/`（计划、本记录、本地运行说明）。`uv.lock` 保持基线原样。
- 旧工作区 `/Users/zhaoyuancun/Documents/ToolUniverse-fork`：未切换分支、
  未 stash/reset/clean、未提交；仅按计划第 1 节执行了 `git fetch upstream`
  （远程跟踪引用更新，不影响工作树）。

## 提交

实现以 git 提交固化在本分支（见 `git log codex/acmg-svi-cspec-lightweight`）。
未推送远端；未改任何发布版本或远程 pin。
