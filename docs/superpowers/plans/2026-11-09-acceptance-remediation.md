# ACMG 小数计分、证据独立性与 CSpec 验收修复计划

日期：2026-11-09
基线：`ec3507108765f83621c03da78c8a0cb53f7b307a`（工作区干净）
执行方式：A→B→C 三批串行，每批独立提交，不 push。

## Batch A：数值契约修复与旧客户端兼容

1. 移除 `_acmg_num` 的一位小数展示舍入。整数值输出为 int，非整数值保留计算精度（5.99 不得写成 6）。分类与返回总分使用同一个未作舍入的数值。求和复用标准库 `math.fsum`。
2. 修复大数相减：`applied_total = min(raw_locus_total, 5.0)`。若 capped，采用正向预算分配：预算 5.0，逐码分配 `applied = min(raw_points_for_code, budget); budget -= applied`，顺序 PP1→PP4。保留现有“优先保留 PP1、再分配 PP4”的账务顺序，但不得通过大数相减实现。
3. 溢出与非有限值：对不可表示的输入、求和溢出及非有限汇总值返回明确 `status:"error"`，不得输出 Infinity/NaN，不得静默清零后继续。
4. 一致性验证（加测试）：所有贡献分之和 == pathogenic+benign 之和 == total_score；locus applied == min(raw_locus_total, 5)。
5. 不含 `svi_points` 的记录继续使用整数强度分，不再强制转换为浮点数，恢复旧贡献项的整数类型。
6. 分类区间（仅小数路径新增连续区间；旧整数回执语义不变）：
   - Pathogenic：total ≥ 10
   - Likely Pathogenic：6 ≤ total < 10
   - VUS：0 ≤ total < 6
   - Likely Benign：−7 < total < 0
   - Benign：total ≤ −7
   Benign 保留 `≤−7` 边界；`−7 < total < 0` 为 Likely Benign。所有旧整数分类不变。这是项目针对小数输入明确的区间延伸，不称为新的 SVI 推荐。
7. 保留任意正有限 `svi_points` 的结构契约，不新增一位小数限制；生物学赋值依据仍由 Skill 核实。仅小数扩展路径更新 `method.thresholds` 为上述连续区间；旧整数路径保留原有回执描述。工具 JSON description 说明两种路径。
8. 保留整数位点上限 pause、PP3+PM1 cap、BA1、重复计分等所有既有行为。
9. 测试矩阵（先写失败反例再修复）：
   - 2.99 → total ≈ 5.99 → VUS（不得进位为 6）
   - PP4 3.0 配其余 3 分证据 → LP/6
   - 9.99 → LP；10 → P
   - PP1 0.4 + 良性 −7 → LB −6.6
   - −7 / −6.999 / −6 / −0.4 / 0 → 按区间表（−7 → Benign；−6.999/−6/−0.4 → Likely Benign；0 → VUS）
   - 单项 1e20 分别落在 PP1 与 PP4 → 位点生效分与总分均为 5
   - PP1 与 PP4 各 1e308 → 明确 error，回执可严格 JSON 序列化
   - 既有 5.5→5 钳制、混合钳制、PP1 0.4 等场景不回归
   - 不含 svi_points 的 LP/9、VUS/4 回执贡献分保持整数类型
   - 布尔、NaN、无穷、字符串、null、非 PP1/PP4 携带 svi_points 仍被拒绝
10. 当前 ACMG metadata hash 已与配置不一致。使用官方生成逻辑在临时目录核对，只回填 ACMG 包装器的实际变化及 metadata 对应项。
11. SDK/compact MCP stdio 测试补充精度、极值与负值边界用例。

提交信息：`fix(acmg): preserve fractional scores and stabilize locus caps`

## Batch B：PP4/PS4 证据独立性与 CSpec 一般基因文档

1. 删除“PP4 与 PS4 同时 met 必停”分支及 `pp4_ps4_proban_exclusivity` 暂停理由。PP4/PS4 病例独立性由 Skill 确认，复用 `evidence_ids`、`blocking_issues`，不增加确认字段。保留 `duplicate_scoring_facts`：同一 fact id 双码送审。Skill 文档更新：
   - 确认独立（病例、家族或事实标识可区分）→ 两者 met，正常计分
   - 未知 → blocking_issues → needs_review
   - 确认重叠（同一病例既算 PP4 又算 PS4）→ 将重复病例分配给一码，另一码基于剩余独立病例重新评估；无独立支持时另一码记 not_met 并说明
   不解析 rationale 来自动判断“已确认”，不增加顶层字段或病例状态机。
2. 同步修改 Canonical Skill 步骤 4–6、Standing Rules、SVI_REFERENCE、工具 description：`svi_points` 是允许的原始分值字段；其他总分/阈值覆盖仍然拒绝。
3. 独立性测试五项：
   - 双 met、事实独立 → computed
   - 双 met、未知 + blocking_issues → needs_review，无 total_score
   - 共享 evidence_id → duplicate 计分事实 pause
   - 同论文不同 fact id → 不算 duplicate
   - 既有 dedup 行为不回归
4. CSpec：不修改查询算法、返回结构、候选保留。文档主线写清：按基因查询（任意给定 HGNC 符号），结合疾病与遗传方式判断适用性；适用 CSpec 优先；无适用 CSpec → 通用规则；查询失败/未知范围 ≠ 无规范。
5. 合成参数化测试：MYOC、LDLR、BRCA1、MYH7、TSC2（测试用 spec id 需明确标注为合成，避免与真实注册表混淆）。验证：精确匹配、基因-疾病-遗传方式绑定、无匹配。再加一条通用“索引无基因绑定”合成规范：候选可与明确匹配并存，不被自动删除也不被当作匹配。
6. 既有线粒体回归用例保留，不从线粒体特例外推一般规则；合成 TSC2 命中不等于真实 TSC2 规范存在的长期断言。
7. 分发：仅同步本 ACMG Skill 的 SKILL.md 与 SVI_REFERENCE.md 两文档到 Claude/Codex 副本。Codex 走官方 `scripts/sync-codex-plugin-skills.sh`（临时 DEST 生成后定向回填），frontmatter 保持归一化，不带 evals 或其他 Skill。
8. 工具 description 变化后再次核对 ACMG metadata 对应项。

提交信息：`fix(acmg): resolve evidence independence in the skill workflow`

## Batch C：复验、归档与交付

1. 完整定向回归（先跑改动面测试，再跑全量命令），命令：

```bash
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -B -m pytest --no-cov --maxfail=0 -p no:cacheprovider \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_acmg_skill_evals.py \
  tests/unit/test_acmg_mcp_stdio_sdk.py \
  tests/integration/test_acmg_mcp_stdio.py \
  tests/unit/test_clingen_cspec_tool.py \
  tests/unit/test_clinvar_region_tool.py \
  tests/unit/test_clinvar_get_submitted_records.py \
  tests/unit/test_clinvar_search_tool.py \
  tests/unit/test_clinvar_external_api.py \
  tests/unit/test_clinvar_search_by_region.py \
  tests/unit/test_clinvar_get_variant_details.py \
  tests/unit/test_clinvar_clinical_significance.py \
  tests/unit/test_clinvar_region_base.py \
  tests/unit/test_clinvar_eutils_facets.py \
  tests/unit/test_clingen_dosage.py \
  tests/unit/test_generator_invariants.py \
  tests/unit/test_acmg_summary_contract.py \
  "tests/unit/test_clinvar_[a-z]*.py"
```

2. 记录实际执行的展开文件清单、collected 数、passed/failed/skipped 数字。不得预填通过数；回归前必须记录命令实际展开的文件数。
3. Ruff 只查本批改动文件；对 `ec350710` 与 `212ff57` 分别执行 `git diff --check`。
4. 冻结面核验：依赖与锁文件、ClinVar/CSpec 生产逻辑、MCP 默认配置、其他工具配置不变。将“不含 svi_points 回执逐字节不变”的说明改成“保持旧接口语义与整数类型兼容”。
5. 在线查询 MYOC、LDLR、BRCA1（使用本 worktree venv 的 `ClinGen_search_cspec`）：记录实际 spec id、版本、绑定疾病与遗传方式、criteria 修改点；不把当前 ID、版本、数量写成长期固定断言。再查 TSC2 与一个无匹配基因：记录空匹配与候选行为；查询失败必须明确报错，不能归为无规范。
6. 独立宿主可用则跑三个固定场景（P/LP/VUS）；宿主不可用则明确写“未验收”，不安装宿主、不改全局配置。工具链路测试不冒充 LLM 行为验收。
7. 证据归档目录：`temp_docs_and_tests/benchmark_tracking/2026-11-09-acceptance-remediation/`，保存完整工具回执（JSON 归一化，日期戳）。
8. 追加至现有运行文档和实施记录（`docs/acmg_svi_cspec_local_run.md`、`docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`），不新建平行记录体系。

提交信息：`docs(acmg): record acceptance remediation and verification`

## 全局约束

- 复用当前 worktree 和分支，不操作 `ToolUniverse-fork`，不修改依赖、全局安装或 MCP 配置，不 push。
- 本轮不进行 upstream 同步。
- 修复顺序：先写失败反例确认缺陷，再修复，再回归。
- 每批提交前运行该批定向测试；C 批运行完整回归。
