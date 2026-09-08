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
