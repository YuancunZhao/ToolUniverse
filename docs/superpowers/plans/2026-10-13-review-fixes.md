# ToolUniverse 审查问题修复计划

> **交接要求：** 执行 agent 使用 executing-plans 按批实施；每批先复现、补反例、修复、验证，再独立提交。不要一次性实施全部改动。

**目标：** 修复本轮确认的 11 项问题，保留“Skill 判断证据、计算器校验和组合”的轻量架构。

**依据：** [完整审查报告](/private/tmp/ToolUniverse-acmg-code-review-2026-10-13.md)。下文 F01–F11 与报告编号一致。

## 1. 起点、边界与接口约定

- 工作目录固定为 `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`；分支固定为 `codex/acmg-svi-cspec-lightweight`。
- 预期起点为 `4f2d91965ffc7ec4eb6a45353ea6c1b3598692c7`，工作区干净。若已推进，先核对差异，不能 reset 或覆盖其他 agent 的工作。
- 官方 upstream 仅指 [mims-harvard/ToolUniverse](https://github.com/mims-harvard/ToolUniverse)，对照提交为 `2128ff57`。本轮不顺带同步新的 upstream。
- 不新建分支，不修改 `ToolUniverse-fork`、依赖、锁文件、全局 MCP 配置或已安装 Skill。
- 实施开始后，将本计划保存为 `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/docs/superpowers/plans/2026-10-13-review-fixes.md`。
- 分批 commit；本计划不包含 push。

**ClinVar 详情缺失采用已确认的策略：保留真实命中，明确披露不完整。**

搜索成功响应的 `data` 增加：

| 字段 | 契约 |
|---|---|
| `details_complete` | 布尔值；返回的 `variant_ids` 均有可解析详情时为 true |
| `missing_variant_ids` | 缺失或解析失败的 UID 列表，保持原顺序、去重 |
| `warnings` | 沿用现有告警数组，说明整体或逐记录详情失败原因 |

健康空查询返回 `details_complete=true、missing_variant_ids=[]`。完整性针对本次返回的 ID，不能因为 `total_count` 大于分页数量就判为不完整。eSearch 本身失败仍返回错误。

## 2. 五个修复批次

### A：补齐 ClinVar 引文解析——F01，优先处理

修改共享解析器 [clinvar_submitted_tool.py](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/src/tooluniverse/clinvar_submitted_tool.py)，同步两工具的引文 Schema 描述。

- 在已有两种路径之外，加入：
  - `ObservedInList/ObservedIn/ObservedData/Citation`
  - ClinicalAssertion 下直接的 `Citation`
- 保留 `(PMID, source_path)` 去重规则、不同 SCV 的归属和一次批量标题回填。
- 发现已知路径之外的 Citation 时，保留解析告警，使 `citations_complete=false`；不要无来源地递归收集所有 ID。
- 健康的无引文记录仍可完整；不得以“空列表一律不完整”掩盖解析缺陷。
- 新夹具必须真实构造目标 XML 路径，不能继续使用现有 helper 的“其他路径都写成 AttributeSet”兜底。

**反例与回归：**

1. ObservedData 引文能返回 PMID、标题、准确 `source_path`。
2. 直接 Citation 能被提取。
3. 同 PMID 不同路径、不同 SCV 保留归属；同一位置重复项去重。
4. 未处理路径、非 PubMed 来源、标题失败均披露不完整。
5. submitted-records 与 details 两条入口得到一致结果。

复用现有 submitted-citations、details-citations 测试文件。提交建议：`fix(clinvar): capture observed and direct submitter citations`。

### B：修正规则文档及对应场景——F02、F08、F09

修改 [SVI_REFERENCE.md](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md)，不修改计算器计分逻辑。

**PVS1：**

- 删除“附近可能恢复框内剪接，因此任何强度均不可用”的排除条件。
- 明确评估隐匿位点、外显子跳跃、关键区域和蛋白损失；维持阅读框不等于恢复功能。
- 多个合理结果按决策树采用相应最低强度；功能救援充分成立时才据此排除。
- 保留其他有来源支持的 PVS1 条件。[Abou Tayoun 2018](https://pmc.ncbi.nlm.nih.gov/articles/pmid/30192042/)、[Walker 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10357475/)。

**BayesDel：**

- 将当前校准行明确命名为 `BayesDel_noAF`。
- 注明 MyVariant 对应字段为 `dbnsfp.bayesdel.no_af.score`，不得套用到 `add_af.score`。
- 频率独立性的组合说明同步限定 noAF 版本。
- 不新增预测器 allowlist，不顺带改其他工具阈值。[Pejaver 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9748256/)。

**PS1 / PM5：**

- 补上蛋白比较路径的剪接机制核查，避免把通过剪接致病的对照用于单纯氨基酸比较。
- 澄清相同氨基酸改变可由预测确定，不增加蛋白功能实验的硬性前提。
- 适用专门剪接 PS1 规则时，按对应规则判断。
- 修正“PS1 没有 SVI 相关建议”的笼统来源表述。[Walker 2023](https://pmc.ncbi.nlm.nih.gov/articles/pmid/37352859/)、[ACMG/AMP 2015](https://pmc.ncbi.nlm.nih.gov/articles/PMC4544753/)。

**新增 evals 11–15，保留旧 ID：**

| 案例 | 中性事实与验收目标 |
|---|---|
| 11 | 框内剪接损害已确认关键区域；应保留树支持的 PVS1 Strong |
| 12 | 已确认功能救援；不得仅因 canonical 位点就赋 PVS1 |
| 13 | 预选 noAF，附件同时含 noAF=0.60、addAF=0.10；应使用 noAF 对应校准 |
| 14 | PS1 对照通过剪接致病，待评变异无对应剪接影响；不得仅凭相同蛋白注释赋 PS1 |
| 15 | PM5 同类机制边界；不得借不同错义注释跳过剪接核查 |

每案独立事实附件，不放预期答案。更新 ID、附件存在性检查；增加针对已确认错误文案的文档守卫，明确这些检查不能证明 LLM 行为。

通过后同步 canonical、Claude、Codex 分发。Codex 使用正式同步脚本重定向临时目录，只回填目标 Skill，保留 frontmatter 归一化。提交建议：`docs(acmg): correct splice eligibility and predictor calibration`。

### C：披露 CSpec 元数据矛盾——F03

修改 [clingen_tool.py](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/src/tooluniverse/clingen_tool.py)。

- 合并索引与详情前，对详情实际提供的 `@id`、版本、发布状态进行核对。
- ID 使用现有归一化方法；版本去空白后比较，不自行推断版本等价；状态比较忽略大小写。
- 缺少可选元数据不新增硬性失败条件。
- 矛盾进入已有 `detail_structure_failed`、`missing_materials`、`partial_failures` 通道，消息包含字段与两侧值。
- 保留原始详情及可用规则，但不能继续声称材料完整；不新增状态机或自动切换规范版本。

**回归：** 分别模拟不同 ID、不同版本、Retired 详情；断言三处披露齐全。另验证一致、可选字段缺省、既有部分规则损坏场景。提交建议：`fix(clingen): disclose inconsistent specification metadata`。

### D：修复 ClinVar 查询、详情完整性与 SDK——F04–F07

修改 [clinvar_tool.py](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/src/tooluniverse/clinvar_tool.py) 及搜索工具定义。

- **候选 OR：** rsID 与普通名称形成同一个 OR 子句，再与 gene、condition 等过滤条件 AND。
- **基因重试：** 记录 gene 条目的索引，别名和去连字符重试只替换该元素；不得覆盖原始 Entrez 查询。
- **详情完整性：** 按第 1 节契约实现；整体请求失败、结果容器损坏、缺失 UID、逐记录错误或解析失败均具名披露，保留其他可用详情。告警放 `warnings`，查询告警仍放 `query_warnings`。
- **SDK 兼容：** 保留旧九个位置参数顺序：
  `gene, condition, variant_id, max_results, limit, clinical_significance, gene_symbol, significance, query`。
  将 `variant_name` 放到它们之后；新调用统一推荐关键词参数。
- 调整 JSON 参数顺序后，使用已有生成器在临时目录**强制生成**目标 wrapper，再定向回填和更新目标 metadata。配置哈希忽略键顺序，不能依赖普通增量生成自动识别这次签名调整。
- 搜索返回 Schema 补充实际规范化输出及完整性字段；保留兼容字段，不整文件重排，不修改通用生成器。

**必须先失败的反例：**

| 输入或故障 | 修复后要求 |
|---|---|
| 两 rsID、rsID+HGVS | 同一候选 OR 组 |
| GBA + `1[chr]`，解析为 GBA1 | 重试为 `1[chr] AND GBA1[gene]` |
| BRCA-2 + `13[chr]` | 保留染色体条件，仅替换基因 |
| eSearch 命中、esummary 503 | 保留 count/IDs，完整性 false、缺失 IDs 和告警 |
| 部分记录损坏 | 有效记录保留，失败 UID 具名 |
| 健康命中、健康空、分页查询 | 完整性语义正确 |
| `ClinVar_search_variants("BRCA1", None, None, 10)` | 仍提交 `max_results=10` |
| `variant_name=` 字符串或数组 | 正常透传，既有字符串化数组兼容不退化 |

增加默认 MCP 注册路径的接口检查，确认数组保类型、新字段可返回；不以 handler 直调替代公开入口验证。提交建议：`fix(clinvar): preserve query semantics and disclose missing details`。

### E：删除重复分类表，修复收集示例——F10、F11

修改 [CHECKLIST.md](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/skills/tooluniverse-variant-interpretation/CHECKLIST.md)、[TOOLS_REFERENCE.md](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md) 和相关 CODE_PATTERNS。

- 删除 Minimum Evidence 组合表，改为核对计算器状态、分类、总分、重复事实和全部暂停原因。
- MyVariant、gnomAD 查询使用 `query=`；ClinVar 使用 `variant_name=`；InterPro 使用 `protein_id=`。
- UniProt 到结构列表使用现有 `PDBeSIFTS_get_best_structures(uniprot_accession=...)`。
- 删除不存在的 `PDB_get_structure` 调用及依赖未定义分析 helper 的完整流程，不新增结构分析实现。
- BioRxiv 日期列表、MedRxiv DOI 详情不得伪装为关键词搜索；删除不符合其能力的示例。
- 在现有文档测试中增加小型 AST 检查：静态工具调用的工具名存在、关键词合法、必需参数齐全。复用现有配置，不另建测试框架。

先确认检查能抓到旧示例，再修文档。同步两个目标 Skill 的分发副本并验证一致性。提交建议：`docs(variants): remove duplicate rules and repair collection examples`。

## 3. 自动化与真实链路验收

统一使用：

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONDONTWRITEBYTECODE=1 \
  /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/.venv/bin/python \
  -B -m pytest --no-cov --maxfail=0 -p no:cacheprovider <测试文件>
```

- 各批运行直接相关测试；最终重跑审查报告中两组回归命令，并追加 `test_generate_tools_types.py` 和新增接口测试。
- **893 passed / 1 skipped 是起点记录，不是预计交付数字。** 保存实际命令、退出码、通过/跳过/失败数及跳过原因。
- 修改文件 ruff 通过；对本轮起点和官方基线运行 `git diff --check`；确认锁文件、依赖和无关生成文件零变化。
- CLI 与真实 stdio 均使用本 worktree 入口、临时配置和明确工具列表：验证正常搜索、详情、引文和数组参数。
- 在线引文检查包含 2737810 回归与 13961 的 ObservedData 来源；不固定引文数量，不要求含其他来源告警的响应一定 complete=true。

独立宿主验收运行新案例 11–15，再回归旧案例 3/4。每案独立会话，只提供当前 Skill 和该案事实，不提供计划、断言或预期答案。保存版本、模型、Skill 哈希、完整工具轨迹、退出码和最终答复。

额度中断使用原生续接；未取得最终答复标为 PARTIAL，不得将计算器调用成功写成完整工作流 PASS。

## 4. 收尾与交接

最后单独提交记录更新，继续使用既有[运行文档](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/docs/acmg_svi_cspec_local_run.md)和[实施记录](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md)，不建立第二套记录系统。

交付必须列出：F01–F11 对应提交、实际回归结果、接口变化、真实链路回执，以及代码／自动化／独立宿主三种完成状态。长日志落盘，每批只汇报关键结果；中断后从计划复选框和 Git 状态恢复。

不包含全量 upstream 在线审计、依赖重装、全局安装或 push；串行全量仍受本机段错误限制。两项 P1 和独立宿主边界验收完成前，不能宣称全面验收通过。
