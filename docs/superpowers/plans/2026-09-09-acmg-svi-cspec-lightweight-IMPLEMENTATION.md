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

## 交付后修正（2026-09-09，用户质询触发）

用户问及 PS2/PM6 计数表的来源后，对 SVI_REFERENCE.md 中凭记忆撰写的数值表
逐张回核原始文件，发现三张与原文不符（方向一致：整体低估一档或沿用旧约定），
已按原文修正并同步两份发布副本：

| 条目 | 原文实际规则（已核） | 修正前错误 |
|---|---|---|
| PS2/PM6 de novo | SVI v1.1（2018-03-18 批准，2021-05-05 修订）：每先证者按"表型特异性 × 亲缘确认"计 2/1/0.5/0.25 点（表型不一致=0，父母未检测=0）；合计 0.5/1/2/4 → Supporting/Moderate/Strong/VeryStrong；AR 无第二击降一级、种系嵌合需确认亲缘、X 连锁携带母亲特例 | 写成"1 个确认→Moderate、2 个→Strong、≥3→VeryStrong、未确认最多 Supporting" |
| PM3 in trans | SVI PM3 v1.0（Oza et al. 2018 Table 6a）：每先证者按"相位 × 另一变异分级"计 1.0/0.5/0.25/0；合计 0.5/1/2/4 → 同上阶梯；单个完全确认先证者= Moderate | 写成"1 个确认→Supporting、2→Moderate、3–4→Strong、≥5→VeryStrong" |
| PP1/BS4/PP4 | Biesecker et al. AJHG 2023（PMC10806742）：共分离按个体计点（AD 1.0、AR 患者 2.0/非患者 0.4、XLR 男 1.0），1/2/4/8 → S/M/S/VS；PP4 按诊断产出计点（≥20% 起步 +1.0）；PP1+PP4 合计上限 +5.0；BS4 不分离= −4.0（AD/AR 纯合/X 连锁；AR 复合杂合几乎不计） | PP1 写成旧的"meioses 阶梯"（≥2→Supporting…≥7→VS）；PP4 未接产出点表；BS4 未接 −4.0 规则 |

核验来源（均为原文，非二手摘要）：

- PS2/PM6：官方 PDF 全文提取（clinicalgenome.org docs 页，Version 1.1，含
  Table 1/Table 2 与全部附加规则）；并用 MYOC GN019 的疾病特化表反验（
  "1 confirmed JOAG→Moderate"等条目与 SVI 通用表逐条吻合）。
- PM3：Genome Medicine 2020 SVI 综述（PMC6885382）Table 4A/4C + ClinGen
  curation SOP 的 0.5/1/2/4 阶梯 + ATM Clin Chem 2021 用例（score 2.0–3.75
  → Strong）三方一致。
- PP1/BS4/PP4：AJHG 全文（PMC10806742）Table 2/3/4 原文数值。

同时核实为正确的条目（未改）：PM2_Supporting（SVI PM2 v1.0）、PS3/BS3
（Brnich et al.，MYOC 规范同引）、PP3/BP4（Pejaver et al. 2022 校准）、
PVS1 决策树结构、PP5/BP6 停用；并确认 **PS4/PM1/BP5 无 SVI 专项建议**
（guidance 索引核对），文档中"规范依赖、不造阈值"的写法正确。

教训已吸收：SVI_REFERENCE.md 头部现列出各计数表的原始文件与版本；
后续任何数值表修改都应先取原文，不以记忆或搜索摘要为准（本次搜索摘要
曾给出 PM3 2/4/6/8 的错误阶梯，被原文否决）。

## 交付后修正二（2026-09-09，用户指令：所有 SVI 规则对齐 recommendation 原文）

应用户要求，对**全部**有 SVI recommendation 的规则逐一取原文核验并重写
SVI_REFERENCE.md；同时查出并删除了四个**不存在的"SVI 建议"引用**：

| 条目 | 核验结果与修正 |
|---|---|
| PVS1 | 按 Abou Tayoun et al. 2018（PMC6185798）决策树原文重写强度档：VeryStrong（NMD 预测/全基因缺失）；Strong（NMD 逃逸+C 端关键证据 或 去除>10% 蛋白；插入位点未知的重复）；Moderate（NMD 逃逸<10% 蛋白；起始密码子丢失+下游框内起始上游有致病变异）；Supporting（起始密码子丢失+无上游致病变异）；任意强度均不适用（LoF 非机制、外显子在相关可变转录本缺失、外显子富集高频 LoF、±20nt 内有可重建框内剪接的强共有序列）。补 Walker 2023 RNA 规则：RNA 证实剪接异常 → PVS1_Strength(RNA)，**不是 PS3**，并替代预测性 PP3/BP4 |
| PS3/BS3 | 按 Brnich et al. 2020（PMC6938631）重写：强度**从零起**、按验证升级（≤10 个验证对照 → 最多 Supporting；≥11 个（≤1 个不确定读出）→ Moderate；OddsPath 阶梯 >2.1/>4.3/>18.7/>350；良性 <0.48/<0.23/<0.053 且**封顶 Strong**）；多实验一致取最验证者、冲突时更验证/更贴机制者优先、同级冲突不用；跨实验类别合并无共识。原"默认 Strong"写法有误 |
| PP3/BP4 | 按 Pejaver et al. 2022（PMC9748256）替换为精确校准区间表（REVEL 0.644–0.773/0.773–0.932/≥0.932；BP4 0.183–0.290/0.016–0.183/0.003–0.016；CADD 25.3–28.1/≥28.1 与 17.3–22.7/0.15–17.3/≤0.15 等）；"单一工具、全基因组、见结果前预指定"；**PP3+PM1 合计强度 ≤ Strong**；REVEL/BayesDel 可与 PM2/BS1 无限组合；SpliceAI 剪接阈值 ≥0.2→PP3 / ≤0.1→BP4 / 0.1–0.2 无证据（Walker 2023）。原"REVEL≥0.7"近似值删除 |
| BA1 | 按 Ghosh et al. 2018（PMC6188666）+ SVI 例外清单（2018-07，PDF 原文核对）：初始九个豁免变体（HFE C282Y/H63D、GJB2 V37I、MEFV P369S/R408Q、BTD D444H、ACAD9、ACADS、PIBF1）逐名列出；确认存在按既定标准设置**更低**基因阈值与修订申请机制 |
| PP5/BP6 | 核实原始建议（Biesecker & Harrison, Genet Med 2018, PMC6709533）：**完全停用**（"discontinue the use of criteria PP5 and BP6"），已录入原文引文 |
| PM2 | 核实 v1.0（2020-09-04 批准，PDF 原文）：降为 Supporting；其配套新组合规则（VeryStrong+Supporting→LP）与 Tavtigian 点制（8+1=9→LP）算术一致，已注明 |
| PS4/PM1/BP5/PS1/PM5 | **原引用的"SVI 建议"不存在**（guidance 索引核对），全部改为诚实标注"无 SVI 专项建议"：PS4 给出 ClinGen SOP 默认（OR>5.0 且 CI 不含 1）与 PS4-LRCalc（Rowlands 2024, PMC11503184）定量路线；PM1 仅规范定义区域 + Pejaver 组合上限；BP5 回归 2015 原文+规范条件；PS1/PM5 回归 2015 原文+Walker 剪接比较+规范（MYOC 的 PM5_Strong 路径为规范层） |

**计算器硬化**（SVI 组合上限，代码可按代码标识强制）：

- `locus_evidence_cap_exceeded`：PP1+PP4 合计 > +5 分 → needs_review
  （Biesecker 2023 位点证据上限）
- `pp3_pm1_strength_cap_exceeded`：PP3+PM1 合计 > 4 分（Strong）→
  needs_review（Pejaver 2022）

新增 5 项测试（含边界允许值：PP1+PP4=5 可计、PP3+PM1=4 可计），
`tests/unit/test_acmg_calculate_classification.py` + MCP 集成共 58 项全部
通过；SKILL.md 常设规则与工具描述同步更新；三处副本已同步。

核验中同时确认（未改动）：PP1/BS4/PP4 与 PS2/PM6、PM3 三张表已在修正一中
对齐原文；PS4/PM1/BP5/PS1/PM5 索引上确无专项建议。



## 提交

实现以 git 提交固化在本分支（见 `git log codex/acmg-svi-cspec-lightweight`）。
未推送远端；未改任何发布版本或远程 pin。

## 交付后修正三（2026-09-09，补齐一手来源）

在用户提供 PDF 前的自查补漏，新核验/充实：

- **BA1**：补 Ghosh 2018 全文操作细节（精确定义 "any general continental
  population dataset of at least 2,000 observed alleles…"；ExAC 大陆亚群
  不含芬兰；无需地理匹配；更低基因阈值的四条既定标准；修订申请机制；
  九个豁免变体全表含 MAF）。
- **PS4**：补 PS4-LRCalc 全文（Rowlands 2024, PMC11503184）：LR→以 2.08 为
  底的对数点（与 Tavtigian 点值恒等：2.08/4.33/18.72/350.4 ↔ 1/2/4/8）；
  仅配置 AD 杂合；n=1 病例禁用；CI 保守选项；独立系列点数可加。SOP 的
  OR>5.0/CI 不含 1 规则由 49 页 curation SOP PDF 原文核验。
- **PM3**：Table 6a/6b 由 Oza et al. 2018（PMC6188673）原文核验（P/LP
  确认 1.0 / 相位未知 0.5；纯合 0.5 上限 1.0；VUS/近亲纯合 0.25 上限 0.5；
  阈值 0.5/1/2/4）。**发现一处来源分歧**：Genome Medicine 2020 Table 4C
  称相位未知区分 P(0.5)/LP(0.25)，Table 6a 为 P/LP 统一 0.5——暂按
  Table 6a 执行并在条目中标注，待 SVI PM3 v1.0 原始 PDF 裁决。
- **PVS1**：决策树 PPTX（clinicalgenome 可编辑版）下载解析，树结构与重写
  条目逐档吻合（NMD→PVS1；逃逸+关键区/>10%→Strong；<10%+功能未知→
  Moderate；外显子缺失于相关转录本/人群高频 LoF→N/A）。

仍缺的一手文档（已请用户提供）：SVI PM3 v1.0 原始 PDF（裁决上述分歧）、
BA1 例外清单 2018-07 之后的最新版、（次要）Pejaver 2022 补充阈值表边界值。

## 验收修复轮（2026-09-09，计划：2026-09-09-acmg-svi-cspec-repair.md）

起点 `a397a0c2`；四个提交：`6480b8db`（PM3/PM4 指导）、`2680cdce`（CSpec 异常）、
`6bc71457`（计算器契约/Schema/SDK 测试）、第四个（CSpec 空范围修正 + MCP 三场景
+ 文档 + 副本 + 本记录）。

### 原报告中的错误（本轮修复）

1. **PM3 用错表**：轻量改造轮按 Oza 2018 Table 6a 把"相位未知 P/LP 统一 0.5"
   当作裁决。官方 SVI PM3 v1.0 PDF（2019-05-02 批准，计划提供链接，已全文核验）
   实际区分 P(0.5)/LP(0.25)；且补齐受累患者、双变异 PM2 罕见性、反循环分类、
   单亲验证相位等前提。已按官方表重写并移除"待提供 PDF"占位。
2. **PM4 定义错误**：原文把 frameshift 自动纳入 PM4 并加"LoF 必须不是机制"前提。
   按 SVI Q&A（2021-09-23，第 35 页区段原文核验）恢复通用定义（非重复区
   in-frame del/ins 或 stop-loss；机制不确定降强度不排除；PVS1 任意强度不与
   PM4 并用；PVS1 不适用不自动转 PM4 满足）。补 BP4 独立条目（共用 PP3 校准表）。
3. **"MYOC 无 CSpec、PVS1 满足"的错误示例**：测试与本地运行文档中 MYOC+
   no_released_spec+PVS1 的组合与事实矛盾（MYOC 有 GN019 且其 PVS1 不适用）。
   已全部改为明确标注的 synthetic fixture（TESTGENE/NM_999999.1），文档示例改用
   真实 GN019 查询结果。
4. **CSpec 索引损坏被静默过滤**：损坏记录原先被跳过，可能被读成"没有规范"。
   现非对象记录、缺/非法 status、Released 缺 @id、ruleSets/genes/label 损坏、
   命中规则集缺 @id → `status:error`（指明字段位置与"不能据此认定没有规范"）。
   详情非对象/规则集损坏 → 保留候选规范 + `detail_structure_failed` +
   partial_failures。在线实测中发现 GN015（Released，索引与详情都不含 genes）
   属"确定空基因范围"（JSON-LD 缺省=未绑定，覆盖任何基因都不可能），按空集
   跳过而非报错——修复后在线 MYOC 查询恢复 GN019 v2.1，未知基因仍为有效空结果。
5. **计算器输入校验缺口**：`str()` 强转使对象/数值冒充字符串通过；specification
   结构不校验；no_released_spec 与 specification 矛盾不查；疾病/遗传模式 null
   可拿到正式分类。已全部收紧（见 6bc71457）：严格类型、四键齐全、布尔真伪、
   http(s) source_url、矛盾=输入错误、`incomplete_variant_context`/
   `missing_specification_identity` 两个新暂停原因；公开 JSON Schema 补全
   （additionalProperties:false、枚举、28 定长、引用元素 minLength 1），由
   upstream jsonschema 在 SDK/MCP 层强制。
6. **MCP 测试的服务器选择与覆盖**：原先 `shutil.which` 优先全局 PATH 且可 skip。
   现仅取 `sys.prefix/bin` 入口，缺失即失败（不 skip）；覆盖两工具发现 + 计算、
   非法输入拒绝、needs_review 暂停三场景。
7. **过时的"全部通过"结论**：本记录原实施记录宣称全绿时，环境实际已因隐藏
   .pth 损坏（历史上出现 73 过/1 MCP 启动失败）。已如实重录。

### 环境修复（非 Git 提交）

iCloud fileprovider 守护进程持续把 `.venv`/.../site-packages 下**所有** `.pth`
（及 410+ 文件）标记 `UF_HIDDEN`，chflags 后 3 秒内被回写，`brctl download` 无效；
CPython site 跳过 hidden `.pth`，而普通模块导入不受影响（hidden 目录下 PIL 正常
导入）。修复：`chflags nohidden`（计划要求步骤，已执行但非持久）+
`.venv/.../sitecustomize.py`（把本工作区 `src` 加回 sys.path，等价于被隐藏的
.pth；对 python/pytest/入口脚本统一生效）。验证：`env -u PYTHONPATH
.venv/bin/python -c 'import tooluniverse'` 与 `.venv/bin/tooluniverse-smcp-stdio
--help` 均指向本工作区。已写入本地运行文档的诊断节。

### 实际测试命令与结果（本轮验收，2026-09-09）

```
env -u PYTHONPATH .venv/bin/python -m pytest \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_clingen_*.py \
  tests/unit/test_clinical_calc*.py \
  tests/integration/test_acmg_mcp_stdio.py \
  tests/unit/test_lazy_load_cache_consistency.py \
  tests/unit/test_backward_compatibility.py \
  tests/unit/test_tool_name_shortening.py \
  tests/unit/test_run_parameters.py \
  --no-cov
→ 全部通过（含新增：计算器契约 30+、CSpec 结构 11、SDK 入口 3、MCP 2；
  既有 7 项环境性 skip 不变）
ruff check（改动文件）→ 通过；git diff --check → 干净
tests/test_claude_code_plugin.py → 与修复前基线逐项一致
  （5 项上游既有失败，无新增）
在线 smoke（另行记录）：ClinGen_search_cspec MYOC→GN019 v2.1 成功；
  未知基因→有效空结果；MCP tools/list 含两工具。
```

### 科学规则场景验收状态

- PM3 四个固定场景（2×LP 相位未知=0.5→Supporting；1×P 相位未知=0.5→Supporting；
  1×LP 确认=1→Moderate；相位未知 VUS=0）：**文档层已按官方表覆盖**（SVI_REFERENCE
  PM3 表格与前提）；计算器不实现 PM3 内部计点（计划禁止硬编码评估器），场景由
  外层 LLM 按文档执行——**LLM 实际执行未验收**（见下）。
- PM4/PVS1 场景（LoF 机制不排除 PM4、frameshift 不自动 PM4、PVS1/PM4 不并用）：
  文档层已修正并同步 quick table。
- MYOC/GN019：PVS1 不适用（在线核实）；其 PP3+PM5≤5、PP3+PS1≤6 联合上限仍走
  `unsupported_combination_method` 暂停路径（单测覆盖模拟场景）。
- **未验收（如实标注）**：真实宿主 LLM 工作流验收——"跳过计算器"请求与来源
  嵌入指令的实际调用轨迹记录，本轮环境无外层模型可用，未执行。静态文档检查
  与算术单测不能替代该项。

## 剩余问题修复轮（2026-09-09，计划：2026-09-09-acmg-svi-cspec-remaining-fixes.md）

起点 `f11c6351`；三个提交：`22f4048f`（材料完整性检查）、`a3cae1c7`（未知范围
保留+详情损坏披露）、第三个（接口/生成文件/文档/记录）。

**纠正上一轮的错误解释**：上一轮把"索引（及详情）不含 `genes` 键"推断为
"确定空基因范围、不可能覆盖任何基因"。该推断错误：GN015 官方页面明确提供
线粒体基因规则，API 未逐一列举 `genes` 不构成任何适用性结论。本轮删除该
断言（代码注释、测试、本记录旧行仅留档不再作为依据），改为把此类规范保留
为 `unresolved_scope_specs` 范围待判定候选，由 Skill 依官方材料逐个裁决。

三项遗漏的修复：

1. **通用规则材料不完整仍分类**：`applicable_rules_complete=false` 原只在
   `released_spec_found` 下生效；现为任意 CSpec 状态均暂停
   （`incomplete_specification_material`），BA1 不再提前返回 Benign，错误说明
   不再建议"改用通用规则分类"。先写 3 个失败反例再修复。
2. **未列出基因的规范被误判**：见上；候选含 id/version/vcep（缺失保留
   null）/url/api_url/rule_set_ids/scope_reason，不计入 total，不自动拉详情；
   "无匹配但有候选"的说明明确"范围待确认、勿默认通用规则"；Skill 要求
   data 与 unresolved_scope_specs **同时为空**才可 no_released_spec，旧工具
   响应缺字段不得当空列表。
3. **详情内部损坏未披露**：`_cspec_criteria_for_rule_sets` 返回
   （有效结果＋错误路径列表），路径定位到元素
   （如 `detail.ruleSets[0].criteriaCodes[2].evidenceStrengths[1]`）；有效
   部分保留、损坏标记进 missing_materials/partial_failures/
   detail_structure_failed；可选文字缺失、集合缺省、非 28 项不计为损坏；
   无法归属的损坏规则集报结构问题，明确无关的损坏不混入所选规则。

同步：两工具 JSON 描述与 Schema（新增 unresolved_scope_specs、
detail_structure_failed 声明；计算器四个顶层参数补简短说明——同时消除包装
生成中的三处行尾空白）；两个包装与 metadata 经临时目录生成流程更新；
Skill 三处副本同步；本地运行文档改为检查 data+候选+失败标记，环境说明按
"观察事实/归因未证实"改写（隐藏标志的具体来源未经进程级证据确认）。

**自动化验收（实际结果）**：全量回归命令（见计划）exit 0——collect 总数
345 = **338 通过、7 项既有环境性跳过、0 失败**（其中 CSpec 44、计算器 111
含 SDK 4、MCP 2；较参考值 317/7 的差异为本轮及上轮实际新增测试，未隐藏
跳过项）；修改文件 ruff 通过；`git diff --check f11c6351..HEAD` 与
`git diff --check 752188d0..HEAD` 干净；插件测试失败集与基线一致
（5 项上游既有）。

**在线验收（2026-09-09，另行记录）**：MYOC → data 含 GN019 v2.1，
`unresolved_scope_specs` 含 GN015 等未列基因候选；GN015 官方页面确认其
线粒体适用范围（核基因场景可据此排除）；无明确匹配基因的查询在有候选时
不再宣称完成"无规范"判断。

**未验收（如实标注）**：真实宿主 LLM 工作流验收（含"跳过计算器"请求与
材料内嵌指令的实际调用轨迹）仍未执行——本环境无外层模型。固定资料的
Skill 流程仅完成工具链路演练（CSpec 查询→候选裁决依据→材料完整性→
计算器调用），LLM 判断层未运行。

GN015 官方页面证据（2026-09-09 抓取）：规范标题为 "ClinGen Mitochondrial
Disease Nuclear and Mitochondrial Expert Panel Specifications..."，页面
正文明确以线粒体基因组为规范对象（"the mitochondrial genome would best
fit with Table 1 'phenotypic consistency'..."）。核基因场景可据此排除该
候选并记录来源；不能仅凭 API 缺少 `genes` 排除。

## 收尾修复轮（2026-09-09，计划：2026-09-09-acmg-svi-cspec-final-fixes.md）

起点 `559002a1`；两个提交：`897c1d34`（ID 校验）、`6513b17a`（候选裁决前置+
优先级表+三处同步）。

1. **ID 校验**：`_cspec_id` 原把数字/对象/空白经 `str()` 转成"有效"ID，详情中
   非法 ID 的规则集因此被当作"无关规则集"过滤、绕过损坏披露。修复后非字符串
   与空白/纯斜杠返回空串，走既有错误通道：索引命中/候选规则集非法 ID →
   顶层 error；规范 @id 归一化为空（如 `///`）→ error（本轮补的守卫+反例）；
   详情非法 ID → `ruleSets[n].@id` 结构错误披露、有效规则保留。字符串数字 ID
   不受影响。失败反例先行（5 个参数化用例）。接口无变化，未重生成包装。
2. **候选裁决前置**：Skill 改为每次成功查询都检查 data 与
   unresolved_scope_specs——显式匹配不解决其他候选；同一规范同时在两处时按
   候选 rule_set_ids 核实剩余范围、不得去重丢弃；no_released_spec 仅在全部
   候选裁决后可达；旧响应缺字段时无论 data 是否为空都不得假定已检查。
   优先级表（CSpec 优先/明确允许或确认无规范才用通用规则/缺项补读不视为
   允许通用/规范标 not_applicable 不得用通用规则重启）以同一表述进入 SKILL
   与 SVI_REFERENCE。评估与组合分离：计算器仍仅支持 tavtigian2020，特殊组合
   继续 needs_review。
3. **同步修正**：Codex 副本此前被裸 cp 覆盖回 `disable-model-invocation`
   标记（Codex 校验会拒绝）——本轮经 `sync-codex-plugin-skills.sh`
   重定向临时目录重建并只回填本 skill，frontmatter 归一化恢复
   （disable-model-invocation 计数=0）。
4. **固定响应场景检查**（文档化行为，非 LLM 验收）：匹配+候选（GN019 匹配、
   GN015 候选并存，total 只计匹配）；同一规范两处（rule_set_ids 分离
   635003681/[888]）；仅候选（说明不宣称"无规范"）；两者皆空（有效空结果）；
   旧响应缺字段（按 skill 指引处理）。

**自动化验收（pytest 实际输出）**：`env -u PYTHONPATH .venv/bin/python -m
pytest <计划所列文件> --no-cov -p no:cacheprovider` → **347 passed, 7
skipped, 1 deselected, 0 failed**（上轮参考 338/7/1，增量为本轮新增 ID 校验
测试）；修改文件 ruff 通过；`git diff --check 559002a1..HEAD` 与
`752188d0..HEAD` 干净；插件测试失败集与基线逐行一致（5 项上游既有）。
SDK/MCP 的合法计算、非法输入拒绝、材料不完整暂停、特殊组合暂停用例均含于
上述回归并通过。

**真实 LLM 工作流验收：未验收**（本环境无外层宿主模型；未安装新宿主、未改
用户配置；上述场景检查是工具行为记录，不称为 LLM 验收）。四场景
（匹配+不可裁决候选、可排除候选、特殊组合、跳过计算器请求/内嵌指令）待有
真实宿主时按计划表格补记调用轨迹。

**剩余限制**：特殊组合算法（CSpec 专属组合/上限的机器可读表达）仍为
needs_review 暂停、未实现；隐藏 .pth 的具体来源仍无进程级证据（见运行文档）。

## 整体审查修复轮（2026-09-10，计划：2026-09-10-acmg-svi-cspec-review-fixes.md）

起点 `4257921e`。九项问题中问题 1–6（科学指导）在本节核对，问题 7–9（程序）
见后续各提交。**六反例来源核对清单**（B2/B3）：

| # | 反例 | 适用条件 → 预期 | 来源位置 |
|---|---|---|---|
| 1 | NMD 逃逸 + 无关键区域证据 + 缺失<10% + 其他条件满足 | PVS1 **Moderate**（不是 Strong） | PVS1 决策树（Abou Tayoun 2018, PMC6185798）：Strong 需 C 端关键区域证据或 >10% 截短；旧入口"逃逸即 Strong"简化表已删除 |
| 2 | 非 canonical ±1/2 同义变异，SpliceAI 0.8，无 RNA | 剪接 **PP3** 路径可及（不能因"同义"排除） | Walker 2023（PMC10357475）：Δ≥0.2→PP3（保守 Supporting）；氨基酸预测器不适用≠PP3 排除 |
| 3 | 功能性重复区内的框内缺失 | 不得仅凭 repeat 注释赋 **BP3** | ACMG/AMP 2015 Table 4（PMC4544753）：BP3 要求重复区无已知功能；SVI_REFERENCE BP3 已补条件 |
| 4 | 低外显率疾病中的未发病携带者（trans） | 不能自动赋 **BP2** | ACMG/AMP 2015 Table 4：trans 分支限于"完全外显的显性基因/疾病"；cis 分支另行陈述 |
| 5 | 两次合格的相位未知 LP 共现观察 | PM3 内部积分 0.5 → **PM3_Supporting**（不是 Moderate） | PM3 v1.0（2019-05-02 PDF）：相位未知 P=0.5/次（两次=1.0）、LP=0.25/次（四次=1.0）；SVI_REFERENCE 解释文字已修正 |
| 6 | 两个未校准预测器一致 | 不能自动生成 Strong **PP3/BP4** | Pejaver 2022（PMC9748256）：强度来自预先选定校准工具；旧入口"2+ 一致=Strong"投票规则与共识兜底已删除 |

反例 1–6 均为文档层修正（SVI_REFERENCE/旧入口文件）；无对应计算器逻辑变更
（按计划不新增评估器）。文档示例守卫测试
tests/unit/test_variant_interpretation_code_patterns.py 编译 CODE_PATTERNS
预测示例并以桩数据验证汇总只返回原始结果（{"predictions": ...}，无
acmg_support/acmg_recommendation/consensus）。

### 整体审查修复轮·锁文件与记录（E2，2026-09-10）

按用户选择执行 `git restore --source=752188d0 -- uv.lock`；
`git diff 752188d0 -- uv.lock` 为空（0 行）。未改 `pyproject.toml`、未重新
解析依赖、未重建 `.venv`。如实记录：**恢复的官方锁本身未同步当前 manifest
的全部内容（例如 OCR extra）**——这是保留的上游不一致，不宣称锁一致性检查
通过；现有环境不是"按恢复后的锁重新安装"，测试直接使用 `.venv/bin/python`，
任何 `uv run`/安装命令必须 `--frozen` 防止回写。运行文档同步改写。

### 整体审查修复轮·验收记录（E3–E4，2026-09-10）

本轮四个提交：`6d6249fb`（unify guidance，问题 1–6）、`04d6848c`（binding and
rule-set gaps，问题 7–8）、`d8c0629e`（deduplicate fact owners，问题 9）、
`fed3b973`（restore official dependency lock，E2）。

**程序反例修复证据（问题 7–9）**：
- 7：索引匹配两个规则集、详情缺第二规则集（整体缺失或 criteriaCodes
  缺省/空）→ `criterion_specifications (rule_set_id=…)` 具名材料缺口；完整
  响应不被误标；有效规则保留、不混用（3 个失败反例先行，修复后过）。
- 8：diseases=[有效项, null]/42/字符串/对象、inheritance 元素/标签损坏 →
  顶层 error 带全路径；TypeError 不逃逸；合法缺省不受影响；校验仅限请求
  基因条目（失败反例先行）。
- 9：单项内重复 fact（SDK 路径）→ 正常 computed（PVS1+PM2_Supporting=9 LP）；
  单项内重复+跨项共用 → 仍暂停且属主列表无重复；原始记录保留。

**自动化回归（pytest 实际输出，恢复锁文件之后执行）**：计划命令扩展至含
tools_package_imports/packaging_dependencies/smcp_schema_passthrough/
codex_plugin/code_patterns 守卫共 22 个文件 → **672 passed, 8 skipped,
1 deselected, 0 failed，exit 0**（跳过项含 1 项新增环境性跳过）。修改
Python 文件 ruff 全过。`git diff --check 4257921e..HEAD`、
`752188d0..HEAD` 均干净。

**Claude 插件构建与测试（临时快照，同环境同参数，无 maxfail）**：
`git archive` 快照 + `git show` 补入 tests/（conftest + 插件测试）；
`scripts/build-plugin.sh` 双侧 exit 0（dist 写入快照目录）；
tests/test_claude_code_plugin.py 实际失败集合逐行一致（各 5 项：
uvx_refresh_flag、example_params_match_schema[research/researcher]、
slash_commands_documented、mentions_tu_run_cli[research]），基线通过数与
当前一致——无新增失败。上轮"83 passed、6 失败"的口径与本次快照方法不同
（本次含 conftest 的完整插件测试文件、双侧一致环境），以本轮实录为准。

**LLM 工作流验收：未验收**（无真实宿主；不安装宿主、不改配置；工具链演练
不称为 LLM 验收）。
