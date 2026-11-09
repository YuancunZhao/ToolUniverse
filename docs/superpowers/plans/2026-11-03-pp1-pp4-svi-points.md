# 2026-11-03 修复计划：计算器承载 Biesecker PP1/PP4 原始 SVI 分值

Worktree：`/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`
分支：`codex/acmg-svi-cspec-lightweight`；起点 HEAD `86c2fc07`（工作区干净）。
官方基线 `2128ff57`。不 push；每批独立提交。

## 0. 问题（已逐条核实）

TYR `c.1247C>A p.Ala416Glu`（OCA1，AR）：PM2 Supporting(1) + PP3 Moderate(2)
+ PP4（白化病队列诊断率 58.9%，向下取整到 Table 2 的 50.6% 行 → 3.0 分）。
PP4 编码 Moderate(2) → 5 → VUS；Strong(4) → 7 → LP。同一证据两种结论——
计算器契约无法承载 Biesecker 原始小数分。PP4 5.5（86.4% 行）、PP1 0.4
（AR unaffected Table 3）同样无合法编码。

缺陷行号核实（起点 HEAD）：P0-1 `SVI_REFERENCE.md` PP4 节无 Table 2 档位；
P0-2 无 Table 4；P0-3 `clinical_calculators_tool.py:825-830`/`1134` 整数
strength 表；P1-1 无 points→strength 映射说明；P1-2 "<20%" 与最低档
19.1%→1.0 冲突；P1-3 缺原文脚注；P1-4 PP4/PS4 互斥只靠 evidence_ids
约定；P2-1/P2-2 PP1 小数与 +5.0 cap 无合法编码。

## 1. 来源事实（AJHG 2024;111(1):24-38，在线 2023-12，
doi:10.1016/j.ajhg.2023.11.009，PMID 38103548，PMC10806742）

Table 2（PP4，诊断率 → 分，行间向下取整）：
99.9→12；99.8→11.5；99.7→11；99.6→10.5；99.4→10；99.2→9.5；98.8→9；
98.3→8.5；97.5→8；96.5→7.5；95.0→7；93.0→6.5；90.2→6；86.4→5.5；
81.6→5；75.4→4.5；68.0→4；59.6→3.5；50.6→3；41.5→2.5；33.0→2；
25.4→1.5；19.1→1。最低档 19.1%→1.0（故 <19.1% 不适用）。

Table 3（PP1，每名共分离个体）：AD 受累/未受累各 1.0；AR 受累 2.0、
未受累 0.4（超过五名每名再加 0.4）；XLR 男性受累/未受累各 1.0（肯定
杂合女性可计）。未受累仅在完全外显假设下计；父母建立相位不计；
分值属单倍型，多变异在同一单倍型上需分摊。

Table 4（PP1+PP4 合并 → 最大强度标签）：0–0.9 不适用；1–1.9
PP1_Sup 或 PP4_Sup；2–2.9 单 Mod 或 Sup+Sup；3–3.9 仅
Sup+Mod 组合（无单一标签）；4–4.9 单 Strong 或 Mod+Mod；≥5 仅
Strong+Sup 组合。**3.0–3.9 与 ≥5 档没有单一 PP4/PP1 标签** → 必须用
points 承载。

诊断率脚注（原文）："Diagnostic yield is the historical demonstrated
yield of pathogenic variants from molecular testing that is similar to the
methodology used for the case under current analysis. It is wholly
dependent upon the phenotype criteria matching as well."

cap 语义（原文）："evidence is capped at +5.0 points for all locus
evidence (PP1 and PP4)"——**钳制**，不是 pause。理由：变异可能仅与真
致病变异处于连锁不平衡，LP/P 判定需要其他证据类型。

## 2. 契约决策（由来源与既有守护推出的默认，均可在评审中纠正）

1. evidence record 新增**可选** `svi_points`（数值）。仅允许
   criterion ∈ {PP1, PP4} 且 status == "met"；否则报错。必须为实数
   （拒 bool）、有限、> 0；**不设上限**（Table 3 未受累延伸无上限；
   +5.0 cap 会约束生效贡献；异常值在 raw 披露中可见）。
2. `strength` 仍必填、仍须合法——它是展示标签；该记录的**算术由
   svi_points 接管**（无 svi_points 时不变）。不强制 strength 与
   svi_points 的一致性：Table 4 的 3–3.9 与 ≥5 档本无单一标签，任何
   一致性规则都会与原文冲突。分类不再依赖标签选择——歧义由此消除。
3. locus cap 双语义：
   - 纯整数路径（PP1/PP4 均无 svi_points）：维持既有 pause
     （`locus_evidence_cap_exceeded`，Table 4 的合法整数组合不会 >5，
     >5 即误编码——现有测试锚定，不改）。
   - 任一 PP1/PP4 带 svi_points：按原文**钳制**——raw 总和
     min(raw, 5.0) 生效，不 pause；`locus_evidence` 披露块（仅此新
     场景出现）：pp1_points/pp4_points（raw）、raw_total、cap 5.0、
     applied_total、capped。不为钳制发明单码分摊规则；恒等式
     total = 非位点分之和 + locus_evidence.applied_total。
4. `point_contributions` 条目在带 svi_points 的记录上增加
   `"svi_points": <raw>` 键（`points` 为生效贡献）；不含 svi_points 的
   回执保持旧接口语义与整数类型兼容。
   （2026-11-09 勘误：原文写"逐字节不变"，但 2026-11-09 A 批移除了
   一位小数展示舍入并恢复贡献分整数类型后，"逐字节"措辞超出可兑现
   范围——旧整数回执的语义与类型不变，字节级序列化不再承诺。）
5. 总分可为小数：`_acmg_classify` 边界比较本就连续（≥10/≥6/≥0/≥-6）
   ；`total_score`/`pathogenic_points`/`benign_points` 整数值时输出
   int、否则保留一位小数。`method` 块仅在出现 svi_points 时附加说明
   子块（既有回执不动）。
   （2026-11-09 勘误：本条"否则保留一位小数"已被 A 批移除——
   5.99 被舍成 6 跨越阈值是本轮修复的验收缺陷，非目标行为。）
6. P1-4：PP4 与 PS4 同时 met → `needs_review`，reason
   `pp4_ps4_proban_exclusivity`（同一 proband 只计 PP4 或 PS4 之一，
   Biesecker 2024；确认两 proband 集合不相交，重叠则其一改 not_met；
   共享 evidence_ids 另行触发 duplicate_scoring_facts）。已核实无既有
   夹具/eval 双 met（不破坏任何锚定回执）。
7. Schema：`src/tooluniverse/data/clinical_calculators_tools.json` 该
   工具 items.properties 增 svi_points；description 的"拒绝点数覆盖"
   改为"唯一 sanctioned 例外：met 的 PP1/PP4 记录可选 svi_points
   （Biesecker Table 2/3 原始分）"；needs_review reason 清单加
   pp4_ps4_proban_exclusivity。包装器 `tools/ACMG_calculate_classification.py`
   不改（schema 在 JSON）。

## 3. 冻结清单（本轮零改动）

uv.lock、pyproject.toml、`clinvar_tool.py`、`clingen_cspec_tool.py`、
`tools.py`、`tools_registry.py`、包装器 `tools/ACMG_calculate_classification.py`、
其余 data/*.json（除 clinical_calculators_tools.json）、evals.json。
计算器本体内除本计划列明的修改外不动。

## 4. 批次

**A 批 `feat(acmg): carry raw SVI points for PP1 and PP4`**：先在
`tests/unit/test_acmg_calculate_classification.py` 追加失败反例（TYR 两例
回执、3.5/标签无关性、5.5→钳 5.0、混合 5.2→5.0、PP1 0.4、PS4 拒绝、
非 met 拒绝、0/负/bool/NaN/inf 拒绝、PP4+PS4 pause、共享 fact 双
reason），确认起点失败；再改计算器 + schema JSON；
`tests/integration/test_acmg_mcp_stdio.py` 增 svi_points 成功用例与
拒绝用例。

**B 批 `docs(acmg): document SVI PP1/PP4 point tables and svi_points
encoding`**：SVI_REFERENCE PP4 节重写（23 行 Table 2、<19.1% 边界、
脚注、Table 4 及"无单一标签→用 svi_points"、cap 钳制语义）；PP1 节补
svi_points 编码与引用精确化（AJHG 2024;111:24–38, doi）；SKILL.md
条目 6 更新；`test_acmg_skill_evals.py` 增文档守卫（Table 2 锚点行、
边界、无单一标签注记、svi_points 契约在两文档中存在）；跑
`scripts/sync-codex-plugin-skills.sh` 与 `scripts/build-plugin.sh` 同步
三处副本，evals/ 不进分发。

**C 批 `docs(acmg): record svi-points verification`**：定向回归（上轮
18 入口参数/40 文件命令）+ ruff（仅检查）+ 对 `86c2fc07` 与 `2128ff57`
的 git diff --check + 冻结清单核验；证据目录
`temp_docs_and_tests/benchmark_tracking/2026-11-03-pp1-pp4-svi-points/`
保存完整回执；本变更为纯离线计算器契约扩展，无网络面，在线检查不适用
（如实注明）；无独立宿主，不标整体验收。记录文档补记。

测试命令沿用：
`env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest --no-cov --maxfail=0 -p no:cacheprovider <files>`

---

## 5. 执行记录（2026-11-03，随 C 批提交回填）

- **A 批** `fa6284ef` `feat(acmg): carry raw SVI points for PP1 and PP4`：计算器新增可选 `svi_points`（仅 PP1/PP4、仅 met、正有限数；拒 bool/NaN/inf/0/负/字符串/null）；`strength` 保留为必填描述标签，算术由 svi_points 接管——分数不再依赖标签选择；svi_points 路径的 PP1+PP4 位点总和按原文钳制 +5.0 并在 `locus_evidence` 披露 raw/applied/capped（钳制超额先从 PP4 扣除、再 PP1——原文未规定分摊，此为已文档化的确定性规则），纯整数路径维持 fail-closed pause；PP4+PS4 双 met 新增 `pp4_ps4_proban_exclusivity` pause；输出数值整数值保持 int、小数保留一位（`_acmg_num`）；schema JSON 增 svi_points 属性并改写 description。9 项行为反例先在起点 `86c2fc07` 确认失败后修复；bad-value 参数化在旧代码上因未知键而通过（错误原因不同），如实标注为契约钉定而非首败。测试过程修正两处测试自身错误：MCP svi 用例误用了含 PVS1(8 分) 的 golden 基底（期望值应为纯 PM2+PP3+PP4 算术）、钳制分摊循环 `next()` 缺省值在单码场景会 StopIteration。
- **B 批** `29dd09d3` `docs(acmg): document SVI PP1/PP4 point tables and svi_points encoding`：PP4 节载入 Table 2 全部 23 行（19.1%→1.0 … 99.9%→12.0，行间向下取整）并将 "<20% 不适用" 更正为 "<19.1% 不适用"（旧表述与最低档自相矛盾，旧句仅保留于更正说明内）；补原文诊断率定义（含方法学相似与表型标准匹配两个限定）；PP1 节补 Table 4 合并档与 "3–3.9 与 ≥5 无单一标签" 的显式声明（即 TYR 歧义根因）及等位基因分摊/超五名未受累/meiosis 脚注；两节文档化 svi_points 计算器契约（含钳制披露与 PP4/PS4 pause）；引用精确化为 AJHG 2024;111:24–38, doi:10.1016/j.ajhg.2023.11.009（SVI_REFERENCE 内 5 处 "AJHG 2023" 引用同步更正）；SKILL.md 规则 6 更新；新增 5 个文档守卫（Table 2 逐行、边界、定义引文、无单一标签、契约短语——空白归一化防跨行漏配；守卫开发中修正两处守卫自身缺陷：`<20%` 禁令误伤更正说明改为禁旧整句、proband 拼写）；canonical 字节一致同步 plugin/ 与 plugins/ 两分发，evals/ 未进。
- **C 批**（本提交）：完整定向回归（同 18 入口参数/40 文件命令）**1080 passed, 1 skipped**（同一 PyMuPDF 既有 skip），exit 0——较上轮 1055/1 净增 25（20 计算器单测 + 5 文档守卫；stdio 三用例并入既有会话测试不加计数）。Ruff（仅检查）通过；对 `86c2fc07` 与 `2128ff57` 的 `git diff --check` 干净；冻结清单（uv.lock、pyproject.toml、clinvar_tool.py、clingen_cspec_tool.py、tools.py、tools_registry.py、包装器）全部零变化。证据目录 `temp_docs_and_tests/benchmark_tracking/2026-11-03-pp1-pp4-svi-points/`（gitignored）保存完整原始回执。本变更为纯离线计算器契约扩展，无网络面，在线检查不适用；无独立 LLM 宿主，技能级验收继续未执行，不标整体验收。
