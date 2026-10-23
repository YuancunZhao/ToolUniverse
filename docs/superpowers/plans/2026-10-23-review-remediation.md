# ToolUniverse 本轮审查问题修复与交付计划

## 1. 目标、起点与边界

> **执行 Agent：** 使用 executing-plans 按 A→B→C→D→E→F→G 串行实施。每批先复现、补失败测试，再修改、回归和独立提交。多个批次会修改同一生产文件，不并行编辑。

**项目目的：** 在官方 [mims-harvard/ToolUniverse](https://github.com/mims-harvard/ToolUniverse) 基础上，完善 ACMG/ClinGen SVI/CSpec 工作流。由 Skill 理解证据和适用规则，现有确定性计算器负责组合与计分；保持改动简单，减少与官方 upstream 的分叉。

**本轮目标：** 关闭本次审查的 10 项问题，补齐真正覆盖缺陷的测试，并修正其他 Agent 的启动说明。

| 项目 | 固定要求 |
|---|---|
| 工作目录 | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 开发分支 | `codex/acmg-svi-cspec-lightweight` |
| 已核实起点 | `e121726dedd251ca4b19ad379e517e2485784bd6`，工作区干净 |
| 已合入官方基线 | `2128ff57`；本轮不再次同步 upstream |
| Python | 使用上述 worktree 的 `.venv/bin/python` |
| 本轮基线测试 | 986 passed、1 skipped；这是起点实测，不是修复后的预测 |
| 本轮提交 | 每批独立 commit；不 push、不发包 |
| 禁止改动 | `ToolUniverse-fork`、用户已安装 Skill、全局 MCP 配置、依赖和锁文件 |

本轮不增加状态机、证据签名、第二套分类器、通用校验框架，也不改变计算器的打分规则。

审查辅助材料：

- `/private/tmp/ToolUniverse-review-20261023-probes.json`（13 个反例的结果）
- `/private/tmp/ToolUniverse-review-20261023-probes.py`（反例脚本）

这些临时文件可能消失；执行者必须能按下文重新构造反例，不能将临时文件缺失作为跳过验证的理由。

## 2. 分批实施

### A．区域查询：详情不完整时整次明确报错

**对应问题：** 区域搜索把请求失败报告为"成功、零重叠、完整扫描"。

修改：

- `src/tooluniverse/clinvar_tool.py`
- `tests/unit/test_clinvar_region_scan_completeness.py`
- `src/tooluniverse/data/clinvar_submitted_tools.json`

**已选定策略：整次明确报错，不新增部分结果字段。**

- [ ] 先复现：eSearch 返回一个 ID，esummary 返回 `{"error":"service unavailable"}`，当前错误输出为 `success / n_overlapping=0 / truncated=false`。
- [ ] 保持 `clinvar_variants_overlapping` 的现有参数签名，补 HTTP 状态检查；eSearch JSON 复用 `_validate_esearch_payload`。
- [ ] 区域查询固定使用正数 retmax，因此 `count>0` 却无 ID、或 `count<len(idlist)` 均视为坏响应。`count>len(idlist)` 仍是合法截断。
- [ ] 每个已返回 ID 必须具有可用于当前 assembly 判断重叠的详情。缺记录、记录内 API 错误、损坏容器、无可用当前 assembly 坐标，均不得跳过后计为"已检查"。
- [ ] 坐标仅接受可解析的整数，拒绝布尔值、非整数和倒置区间。明确属于其他 assembly 的位置不要求其坐标可用。
- [ ] 发生上述错误时抛出带请求阶段、UID 或字段路径的异常，由现有 `ClinVarSearchByRegion.run` 转为 `status:"error"`；不附带成功扫描结论。
- [ ] 保留健康路径的查询构造、候选上限、排序、重叠判断和返回字段。

成功返回继续使用：

```text
term / total_available / n_candidates / truncated /
truncation_note（必要时）/ n_overlapping / variants / note
```

只更新区域工具描述，明确"请求或详情不完整时报错"。不新增参数、字段或收紧现有 Schema 类型。该工具当前没有专用的已跟踪 SDK 包装，本轮不新增包装、不全量重生成工具。

**必须覆盖的测试：**

| 输入／场景 | 预期 |
|---|---|
| eSearch HTTP 错误、API error、坏 JSON、缺 count／translation | 明确 error |
| 正 count＋空 ID；count 小于 ID 数 | 明确 error |
| 健康 count=0、ID=[] | 正常空结果，`truncated=false`，不请求详情 |
| esummary HTTP/API 错误、缺 UID、空记录 | 明确 error |
| 部分批次成功、后续批次失败 | 整次 error，不能返回完整阴性 |
| 没有可用当前 assembly 坐标 | 明确 error |
| 全部候选健康、均不重叠 | 正常零重叠 |
| 健康候选数超过上限 | 原有截断披露不变 |
| 重叠数超过 max_results | 完整重叠计数与结果列表上限保持原义 |

更新健康 `_FakeEntrez`：加入真实 `querytranslation` 和 `raise_for_status` 行为，不能削弱生产校验迁就旧夹具。再通过真实 SMCP 注册、HTTP 全部 mock 的调用验证错误能传到调用方。

**提交：**

```text
fix(clinvar): reject incomplete region scans
```

### B．科学与工具参考：修正 PS1/PM5、ClinVar 星级和参数名

**对应问题：** 同一参考变异被允许支持两项比较证据；ClinVar 星级高估；详情参数表写错。

修改 canonical 的：

- `skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md`
- `skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md`
- `skills/tooluniverse-variant-interpretation/EXAMPLES.md`
- `tests/unit/test_variant_interpretation_code_patterns.py`

**PS1／PM5：**

- [ ] 删除正文和末尾表格中无条件"可同时计分"的许可。
- [ ] 明确：同一个参考变化不能同时证明"相同氨基酸变化"和"不同氨基酸变化"；按事实使用相应准则。
- [ ] 不同参考变异、不同 `evidence_ids` 不能自动证明证据独立；仍需检查适用规范和组合指导。
- [ ] 不将上述修正扩大成"所有基因、所有场景均禁止组合"的新通用规则，不冒称存在 SVI 的全面禁令。
- [ ] 不修改计算器。两个结构合法的 met 记录会被算术相加，这是现有职责边界。

**ClinVar：** 按 [NCBI 官方定义](https://www.ncbi.nlm.nih.gov/clinvar/docs/review_status/) 修正：

| 审查状态 | 星级 |
|---|---:|
| Practice guideline | 4 |
| Reviewed by expert panel | 3 |
| Multiple submitters, criteria provided, no conflicts | 2 |
| Conflicting classifications, criteria provided | 1 |
| Single submitter, criteria provided | 1 |
| No assertion criteria provided／no classification | 0 |

- [ ] 将案例中明确标注为 expert panel 的四星改为三星。
- [ ] 只有星号、没有足够 review-status 依据的案例，删除星号；不猜测其真实审查等级。
- [ ] 保留固定案例的外部分类归属，不用当前在线数值批量覆盖历史示例。
- [ ] 工具表将详情参数 `variation_id` 改为 `variant_id`，说明使用数字 Variation ID；删除搜索响应包含 submitters 的错误承诺。

**补一个中性合成验收案例 17：**

在现有 canonical evals 中新增 `files/case17-single-reference-facts.md`，追加 ID 17，更新 `tests/unit/test_acmg_skill_evals.py`。

固定事实：

- 合成转录本 `NM_999995.1`，第 334 位参考密码子 `GGA`。
- 待评 `c.1000G>A → p.Gly334Arg`。
- 唯一参考 `c.1000G>C → p.Gly334Arg`，其致病性已独立建立。
- 两者无剪接机制影响；没有其他不同氨基酸的致病参考。
- 明确属于合成练习，不能查询虚构标识补造事实。

预期仅写在 eval 断言中：PS1 Strong；PM5 不满足；没有其他计分项时计算器为 VUS／4。事实附件不写预期赋码、总分或分类。

**测试：**

- 原错误文案和星级映射在修改前能被守卫抓到。
- 同时检查正文与末尾表格，避免只改一处。
- 案例 17 密码子一致、附件存在，ID 保持 1–17。
- 文档测试不宣称证明 LLM 行为。

同步仓库两处分发后提交：

```text
docs(acmg): correct reference evidence and ClinVar review levels
```

### C．单详情接口：补齐校验顺序与可选容器处理

**对应问题：** 校验前 `.get()` 崩溃，以及空列表索引错误。

修改 `src/tooluniverse/clinvar_tool.py`，扩展现有 malformed-summary 与 details 测试。

- [ ] `_fetch_variant` 在任何嵌套 `.get()` 前确认顶层 data、result、UID 记录的类型。
- [ ] 继续复用 `_parse_variant_summary`；保留其已有的 `genes`、`germline_classification` 校验，不用笼统 `or {}` 隐藏已定义的损坏输入。
- [ ] 详情的 `variation_set`／`variation_loc` 缺省、null 或空列表视为未提供可选定位信息，输出原有空字段；非空但容器或元素类型损坏则明确报错。
- [ ] 保持原有首条记录选择语义，不新增位置推断或 assembly 自动选择。
- [ ] `clinical_impact_classification`、`oncogenicity_classification` 缺省或 null 时显示空信息；非 null 且非对象时报错。
- [ ] `trait_set` 缺省、null 或空列表返回空 traits；其他错误容器、非对象元素明确报错。
- [ ] 详情自身有结构错误时，不继续请求引文。引文请求失败仍保留健康详情和现有不完整告警。
- [ ] 保持公开字段、`variant_summary` 内部契约、单份 `raw_data` 及引文归属不变。

**失败反例和兼容控制：**

- 顶层 `[]`、`result=null`、UID 对应非空列表。
- `variation_set=[]/null`，以及错误字典、非对象元素。
- `variation_loc=[]/null` 与错误容器。
- 临床影响／肿瘤分类的 null 和错误标量。
- traits 的空值与损坏元素。
- 健康详情内容、引文回填、无原始数据重复。

新反例必须实际运行 `_fetch_variant`；不能像部分旧测试一样 mock 掉它。至少各有一个 details／clinical-significance 的真实 SMCP 注册测试，只 mock HTTP。

**提交：**

```text
fix(clinvar): validate detail responses before field access
```

### D．搜索披露：删除无依据归因，修正 ignored_parameters

**对应问题：** 三个筛选条件的零结果被归因为基因与疾病没有交集；实际执行的 `raw_term` 被说成忽略。

- [ ] 删除 `_explain_empty_result` 中从两个单独计数推导"gene 和 condition 没有共同记录"的句子。
- [ ] 保留已验证的单独计数，以及"当前组合条件返回零"的事实；不增加一次组合归因查询。
- [ ] 修改现有 `test_zero_results_with_a_real_condition_says_gene_and_condition_dont_meet`：它包含第三个 clinical-significance 筛选，旧断言本身不成立，不能保留。
- [ ] 将已经参与查询的 `raw_term` 纳入内部识别集合；不新增公开 Schema 参数。
- [ ] 真正的未知参数仍须披露，拼错参数不能因此被静默接受。

**测试：**

- gene、condition 单独有记录，加 variant_id 或 clinical_significance 后为零：不再断言两者无交集。
- 辅助计数失败继续保持归因未知。
- `query="17[chr]"` 保留在实际查询中，且不再出现 `ignored_parameters=["raw_term"]`。
- 未知拼写参数仍出现在 ignored_parameters。
- 原有候选 OR、别名重试和条件自由词披露保持通过。

**提交：**

```text
fix(clinvar): keep search diagnostics evidence based
```

### E．收集示例：删除派生判断，原始回执直接交接

**对应问题：** GTEx 被误读成零表达；正常 OpenAlex 响应导致崩溃。

修改 `skills/tooluniverse-variant-interpretation/CODE_PATTERNS.md` 与现有文档测试。

**表达示例：**

改名为：

```python
collect_expression_context(tu, gene_symbol)
```

保留 CELLxGENE 和 GTEx 两次调用，输出固定为：

```python
{"single_cell": sc_expression, "gtex": gtex}
```

删除组织名顶层读取、默认零、TPM 阈值和 `expressed_in_phenotype_tissue`。不修改 GTEx/CELLxGENE 生产工具。

**文献示例：**

改名为：

```python
collect_literature_context(tu, gene, variant)
```

保留一次 PubMed 查询；OpenAlex 改为一次 `query=f"{gene} {variant}", limit=5` 查询。输出固定为：

```python
{"pubmed": pubmed, "openalex": openalex}
```

删除逐篇引用次数查询、`citations[0]`、`citation_count` 和 `key_papers_with_citations`。不新增排序或文献质量评级。

**测试必须使用真实返回形状：**

| 工具 | 健康 | 健康空 | 失败 |
|---|---|---|---|
| GTEx | `status/data` 中含 TPM=25 的组织记录 | data=[] | status=error |
| OpenAlex | `status/data.results` 含一篇文章 | results=[] | status=error |
| PubMed | 文章列表 | 空列表 | 错误回执 |

断言原始状态和内容保留，不被替换成零、false 或成功空结果。继续保留现有参数 Schema／动态 CELLxGENE filter 测试。

这是文档辅助函数改名，不是 SDK API 变更；全仓确认没有其他实际调用者，不增加兼容包装。同步仓库分发。

**提交：**

```text
docs(variants): preserve raw collection receipts
```

### F．MCP 使用说明：默认示例启用 compact，补真实链路测试

**对应问题：** 工作区运行文档的推荐启动配置仍暴露全量工具。

修改 `docs/acmg_svi_cspec_local_run.md` 和 `tests/integration/test_acmg_mcp_stdio.py`。

推荐配置保留 worktree 入口，仅补：

```json
"args": ["--compact-mode"]
```

- [ ] 说明 compact 的五个发现／执行工具，以及 `get_tool_info → execute_tool` 的使用方式。
- [ ] 保留现有 `--include-tools ClinGen_search_cspec ACMG_calculate_classification` 的定向测试方式，不给它盲目追加 compact。
- [ ] 说明宿主需重启 MCP 并新开会话，单纯压缩聊天不能移除已注入的静态工具定义。
- [ ] 不修改服务器默认行为、hooks、用户全局配置，不增加 `--full-mode` 等选项。

新增真实 stdio 会话测试：

1. 通过当前测试解释器 `sys.prefix/bin` 的入口启动 compact。
2. 发现五个预期工具，不暴露全量目录。
3. `get_tool_info` 能找到两个 ACMG/CSpec 工具。
4. `execute_tool` 提交已有合成 golden payload，得到 LP／9。
5. 提交 `applicable_rules_complete=false` 的载荷，得到 needs_review／null，无 total_score。

不写固定 token 数或字节数断言；这些随序列化和版本变化。该测试也不称为真实 LLM 验收。

**提交：**

```text
docs(mcp): use compact mode for local agent setup
```

## 3. 同步、回归与独立验收

### 仓库分发同步

B、E 批修改 canonical 后立即同步相关两个 Skill：

- Claude 分发按现有过滤规则同步。
- Codex 必须使用正式脚本，设置 `CODEX_PLUGIN_SKILLS_DEST` 到新建临时目录，再只回填目标 Skill。
- 指定 `CODEX_PLUGIN_PYTHON` 为 worktree Python，并使用干净 PATH，避开本机损坏的 rsync。
- 不把 evals、测试或缓存带入分发。
- Codex frontmatter 不得恢复 `disable-model-invocation`。
- 不同步其他 Skill，不覆盖用户已安装副本。

### 完整定向回归

从固定 worktree 运行：

```bash
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -B -m pytest \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_acmg_skill_evals.py \
  tests/unit/test_clingen_cspec_tool.py \
  tests/unit/test_clinvar_*.py \
  tests/unit/test_spliceai_tool.py \
  tests/unit/test_variant_interpretation_code_patterns.py \
  tests/unit/test_codex_plugin.py \
  tests/unit/test_smcp_strict_field_constraints.py \
  tests/unit/test_run_parameters.py \
  tests/unit/test_parameter_validation.py \
  tests/unit/test_tools_package_imports.py \
  tests/unit/test_packaging_dependencies.py \
  tests/unit/test_generator_invariants.py \
  tests/unit/test_smcp_server_cli.py \
  tests/unit/test_compound_variant_tool.py \
  tests/unit/test_compound_gene_disease_clinvar_gene_names.py \
  tests/integration/test_acmg_mcp_stdio.py \
  tests/integration/test_smcp_schema_passthrough.py \
  --no-cov --maxfail=0 -p no:cacheprovider
```

要求：

- 新增缺陷测试先在未修版本失败；原本通过的兼容控制如实标注。
- 最终报告实际 passed／skipped／deselected／failed 和退出码，不预测数量。
- 修改的 Python 文件通过 Ruff，只检查、不自动扩大格式化范围。
- 对本轮起点与官方基线执行 `git diff --check`。
- `uv.lock`、`pyproject.toml`、计算器、CSpec 实现、SDK 包装和 metadata 相对起点零改动。
- 工具 JSON 仅允许 A 批区域工具的描述变更，其他 JSON 对象和 Schema 保持原样。

### 在线及真实宿主验证

在线工具链路分别验证：

- `ClinVar_get_variant_details(variant_id="2737810")`：详情和引文路径健康。
- 区域查询 `chr7:155593770-155593780`、GRCh37：确认健康扫描、重叠坐标和完整性含义。

在线记录数是时点观察，不写进断言；网络失败记为未完成，不伪装成通过。

若执行环境已有可用的独立宿主，使用修订 Skill 的临时副本，在新会话运行案例 **17、3、4**。仅提供提示词和事实附件，不提供计划、断言或预期答案，保存完整调用轨迹与最终答复。

没有独立宿主时，自动化交付可以完成，但该栏保持"未验收"；不安装新宿主、不改全局配置、不用同一实施会话的演练替代独立验收。

## 4. G 批：记录、提交与交接

继续更新既有运行文档及 `docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`，不新建平行记录体系。

- [ ] 按 10 项审查问题逐项列出解决提交和证据。
- [ ] 说明区域失败采用整次 error；健康返回结构未变。
- [ ] 说明 PS1／PM5 修正发生在判断文档，计算器算法未改。
- [ ] 说明收集示例已删除派生判断，宿主全局配置未改。
- [ ] 分开报告代码完成、自动化完成、在线工具验证、独立 LLM 验收。
- [ ] 保存命令、stdout／stderr、退出码、实际 SHA、解释器及 Skill 哈希；长日志进入 gitignored 验收目录。
- [ ] 最终工作区干净；所有提交仍在原开发分支；不 push、不清理旧 worktree、不重装环境。

记录提交：

```text
docs(acmg): record review remediation evidence
```

每批交接只需报告：提交 SHA、实际改动、测试结果、未完成项。额度中断时记录最后完成批次和下一条命令，恢复后从该处继续。

**未纳入本轮：** 官方 upstream 再同步、全仓串行测试的机器级问题修复、全部上游工具审查，以及真实临床变异和跨模型稳定性保证。独立宿主尚未执行时，最终交付不得标为"整体验收完成"。
