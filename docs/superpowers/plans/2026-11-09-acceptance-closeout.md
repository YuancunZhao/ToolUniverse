# ACMG 验收收尾修复计划

> 执行 agent：使用 executing-plans，按 A → B → C → D 串行实施，每批测试通过后独立提交。只执行本计划，不展开新的架构改造；本轮不 push。

**日期：** 2026-11-09。
**目标：** 补齐生成文件、CSpec 正常测试、Skill 字段说明及验收记录四项遗漏，保持已经通过验收的数值运算与病例独立性政策。
**架构：** Skill 判断证据与适用规范，确定性计算器做校验和组合；本轮不增加临床规则、输入字段或暂停状态。
**技术栈：** 现有 Python、pytest、官方生成器、现有 Skill 同步脚本；不增加依赖。
**依据：** 本计划覆盖 1ba32daf 的复查发现；与此前落盘计划冲突的收尾操作，以本计划为准，不能沿用其中失效命令或错误归因。

## 1. 起点、工作区与边界

- 唯一工作目录：`/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`。
- 继续使用分支 `codex/acmg-svi-cspec-lightweight`，预期 HEAD 为 `1ba32daf3aae8e61602beca487442e868b614669`。计划交付时，允许本计划文件未跟踪；其他变更先只读核对，不重置或覆盖。
- 官方 upstream：`https://github.com/mims-harvard/ToolUniverse`；对照基线为 `2128ff57`，本轮不更新 upstream。
- 使用该目录内 `.venv/bin/python`，确认 `tooluniverse.__file__` 指向本 worktree 的 `src/tooluniverse`。
- 命令统一清除 PYTHONPATH，使用 `PATH=/usr/bin:/bin:/usr/sbin:/sbin` 和 `PYTHONDONTWRITEBYTECODE=1`。
- 保留已经确定的政策：小数不做展示舍入；Benign ≤ −7；正向位点预算；PP4/PS4 独立性由 Skill 核实；查询一般 HGNC 基因并保留未决 CSpec 候选。
- 不修改计算器运算、工具 Schema、CSpec/ClinVar 生产逻辑、依赖、锁文件、MCP 默认模式或用户配置。允许纠正计算器 docstring 和测试注释中的错误历史描述。
- 不操作 `ToolUniverse-fork`，不新建分支/worktree，不更换生成器实现，不安装宿主。
- 本计划保存于 `docs/superpowers/plans/2026-11-09-acceptance-closeout.md`。现有两份运行记录继续使用，不建立另一套实施记录。

## 2. A 批：按实际构建入口同步 ACMG 生成产物

### 修改与校验范围

- `src/tooluniverse/tools/ACMG_calculate_classification.py`
- `src/tooluniverse/tools/.tool_metadata.json`，只允许 ACMG 对应项变化。
- `tests/unit/test_generator_invariants.py`，追加两个有针对性的检查。

实际 `cli.cmd_build` 调用的是 `tooluniverse.generate_tools`；当前 ACMG 包装器来自另一个模块 `generate_coding_api`。本批以实际构建入口为准，不修改任何生成器。

- [ ] 先加两个测试并分别运行，确认当前包装器与 metadata 的问题都能被捕获：
  1. 从现有计算器工具 JSON 读出 ACMG 配置，调用 `generate_tools.generate_tool_file(name, config, tmp_path)`，比较临时产物与仓库包装器的 AST（忽略位置、格式和注释；保留签名、docstring 和调用体比较）。
  2. 使用 `build_optimizer.calculate_tool_hash(config)` 验证仓库 metadata 中该工具的 hash。不要写死当前 hash。
- [ ] 仅在临时目录调用上述单工具生成函数和现有 `validate_generated_code`。不要直接运行 `tu build`：其 lazy-registry 阶段仍可能修改安装目录，即使 wrapper output 指向临时目录。
- [ ] 将单工具包装器回填至仓库，保持四个业务参数、三个控制参数及现有 SDK 调用协议；以生成结果为准，不手工保留另一生成器的模板。
- [ ] 读取完整原 metadata，复制为字典，只替换 `ACMG_calculate_classification` 的 hash；使用官方 `calculate_tool_hash` 和 `save_metadata` 在临时文件生成后回填。
- [ ] 不得将 `get_changed_tools({单工具配置}, ...)` 写出的单项 metadata 覆盖仓库完整文件；该函数会保存传入集合并丢弃集合外条目。
- [ ] 在临时 metadata 副本上验证 `get_changed_tools`：ACMG 应进入 unchanged，不能再返回 hash_mismatch。核对仓库 metadata 的其他键和值全部保持原样。
- [ ] 再生成一次单工具包装器，确认 AST 一致；跑生成器检查、ACMG 单测及真实 stdio/compact MCP 测试。新检查不能写仓库产物，所有生成副作用限制在 pytest tmp_path。
- [ ] 提交前确认没有其他工具包装器、包导出、lazy registry 或全局配置变化。
- [ ] A 批提交一并纳入本计划文件，避免后续遗留未跟踪计划。

提交：`fix(acmg): align generated wrapper and metadata with the active build`

## 3. B 批：让多基因 CSpec 测试真正覆盖完整正常详情

仅修改 `tests/unit/test_clingen_cspec_tool.py`，保留现有 `_patch` 的默认行为，避免影响其他失败场景。

- [ ] 先增强五个参数化正常案例的断言，在原夹具上确认失败。不能通过放宽材料校验使其通过。
- [ ] 对每个参数化案例构造匹配详情并显式传入 `detail_payloads`。规范 ID、规则集 ID、gene、version、Released 状态必须与索引一致。例如：

```python
rule_set_id = "9" + spec_id[-2:]
detail = _detail_payload(spec_id=spec_id, rule_set_id=rule_set_id)
detail["label"] = f"Synthetic {gene} specification Version 2.1"
detail["ruleSets"][0]["genes"] = [{"@type": "Gene", "label": gene}]
record["affiliation"]["label"] = "Synthetic VCEP"
detail["affiliation"]["label"] = "Synthetic VCEP"
_patch(monkeypatch, _index(record), detail_payloads={spec_id: detail})
```

- [ ] 正常案例必须同时验证：返回正确 gene/spec/rule-set 及疾病和遗传方式绑定；`criterion_modifications` 非空；`missing_materials == []`；`detail_fetch_failed` 和 `detail_structure_failed` 不为真；顶层 `partial_failures` 为空或缺省；assertion method URL 存在。
- [ ] CSpec 详情不要求固定 28 条：本批使用 helper 的有效准则即可，不引入错误的数量硬约束。
- [ ] 同步修复“明确匹配＋通用未知范围候选”的测试：为 GNTST005/rule-set 992 提供匹配详情，并对明确匹配断言无损坏和无缺口；GNTST099/rule-set 991 仍为候选、不计 total，且不被自动拉取详情。
- [ ] 保留无匹配案例及现有损坏详情反例；记录请求 URL，正常案例只请求索引及应匹配的详情，无匹配时不请求详情。
- [ ] 注释只将这些绑定称为 synthetic bindings；测试只验证绑定原样保存，不宣称合成疾病/遗传方式组合是临床事实，不宣称真实 TSC2 已有规范。
- [ ] 跑整个 CSpec 单测文件，确认正常、候选、无匹配、结构损坏与部分失败路径全部维持正确区分。生产查询代码零修改。

提交：`test(cspec): use consistent details for gene-wide success cases`

## 4. C 批：明确 Skill 主流程中的可选原始分值

修改 canonical ACMG `SKILL.md`，并只同步它的 Claude/Codex 两份副本。SVI_REFERENCE 无需因这项措辞修复重写。

- [ ] 在现有 `test_skill_documents_svi_points_and_independence_workflow` 中分别提取第 4 步和第 6 步内容，检查两步均明确提到 PP1、PP4 和可选 svi_points，不能仅靠 Standing Rules 中出现该词通过。先确认当前文档失败。
- [ ] 第 4 步将 “record exactly” 七字段改为七个 required fields，并补入以下英文条款，保留全部状态语义：

> Only a `met` PP1 or PP4 record may additionally include the optional `svi_points` field: a positive finite number representing the sourced raw SVI points. The seven required fields remain required; `strength` stays a descriptive label when `svi_points` supplies the arithmetic. No other evidence-record keys are accepted.

- [ ] 第 6 步将无例外的 point-overrides 拒绝句改为：

> The calculator derives the combined score. The sole permitted point-valued input is the optional `svi_points` on a `met` PP1/PP4 record, as described in step 4. Caller-supplied totals, expected classifications, arbitrary point overrides, and thresholds are rejected.

- [ ] 保留已经确定的 PP4/PS4 三态流程，不新增确认参数，不改变计算器边界。
- [ ] Claude 定向同步该 SKILL.md；Codex 使用官方同步脚本、临时 `CODEX_PLUGIN_SKILLS_DEST` 和本 venv Python，回填仅该文件，保持 frontmatter 归一化。
- [ ] 跑现有文档契约、published-copy 一致性和 Codex 插件检查；evals 不进分发，其他 Skill 零变化。

提交：`docs(acmg): clarify optional SVI points in the fixed pipeline`

## 5. D 批：纠正计划与验收材料，完成实际复验

记录修改位置为 `docs/superpowers/plans/2026-11-09-acceptance-remediation.md`、`docs/acmg_svi_cspec_local_run.md` 和 `docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`。错误反例注释位于 `src/tooluniverse/clinical_calculators_tool.py` 的 `_acmg_num` docstring，以及 `tests/unit/test_acmg_calculate_classification.py` 的 2026-11-09 反例注释块。

### 纠正内容

- [ ] 修正旧 `2026-11-09-acceptance-remediation.md` 的命令为下方可执行命令；将 `212ff57` 改为 `2128ff57`；宿主场景恢复为“确认独立／身份未知／共享病例”，不能写成 P/LP/VUS。
- [ ] 在旧计划和现有两份运行记录说明：原批准命令的 18 个入口均存在，展开 40 文件，与当时实际执行集合一致；错误出现在落盘转录，不能将原批准命令归因为姊妹 worktree 命名。保留当时真实测试数字，不重写历史回执。
- [ ] 更正 metadata 解释：配置 hash 与包装器内容是两项不同检查；此前更新了另一生成器的包装器，不代表已经修复实际构建所用 metadata。本批 A 的结果另行记录。
- [ ] 更正计算器 docstring、单测注释、运行文档和实施记录中的旧反例描述：`ec350710` 实际返回的是 **VUS / total_score 6.0**；正确计算量为 5.99。问题是回执分数与分类矛盾，不是旧计算器实际返回了 LP；这也是合成契约反例，不称为真实临床案例。
- [ ] 复核现有在线原始 JSON，修正 `03-online-cspec/summary.txt` 的字段提取：gene 读取 entry.gene，绑定读取 rule_sets[].genes[].symbol/diseases，准则读取 criterion_modifications，方法读取 assertion_method_url，原始材料读取 specification。不要再用不存在的字段得出 gene=None、assertion_method=False、raw_specification_fields=0。原始 JSON 保持字节不变。
- [ ] 保留历史 stdout/stderr/JUnit/退出码。META 中可更正说明并注明本轮勘误，但不能将旧命令和旧输出重造为新运行的记录。历史归档若不存在，明确标注缺失，不伪造补齐。
- [ ] 独立宿主三个正确场景继续标“未验收”；本轮不安装宿主或查找凭据。工具测试不代替 LLM 行为验收。

### 正确回归命令

在本计划指定的 worktree 执行；不要引用另一个检出的测试命名。执行前记录 shell 展开的文件清单及数量，文件缺失必须显式失败：

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight

env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m pytest \
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

### 新证据及交付门槛

- [ ] 使用现有证据目录下的 `closeout/` 子目录归档本轮精确命令、时间、HEAD、解释器、展开清单、stdout/stderr、退出码和 JUnit；不要覆盖前轮证据。
- [ ] 记录本轮实际 collected/passed/failed/skipped，不预测数量，也不将前轮 1107/1 写成本轮实测值。
- [ ] Ruff 仅检查本轮改动 Python 文件，禁止全库格式化；对 `1ba32daf..HEAD` 和 `2128ff57..HEAD` 运行 diff --check，提交前也检查未提交差异。
- [ ] 验证 metadata 其他条目、其他包装器/Skill、依赖、锁文件、工具 JSON 和生产查询逻辑零变化；计算器除纠正注释/docstring 外，运算实现零变化。
- [ ] 补充 A 批生成一致性证据、B 批完整正常回执及 C 批分发一致性证据。新测试都先在旧状态确认能失败；既有通过的算术/MCP 用例只称回归验证。
- [ ] 在现有运行文档与实施记录追加本轮结果，列出 A/B/C/D 提交，分别报告“代码与自动化验收”“历史在线回执复核”“独立 LLM 宿主未验收”。不能称为全仓库全量通过。
- [ ] 定向回归无新增失败、两个生成产物检查通过、正常 CSpec 夹具无损坏、三份 Skill 一致、记录可执行且来源准确后，提交 D 批；最终确认目标 worktree 干净，未 push。

提交：`docs(acmg): correct acceptance provenance and record closeout checks`

**未涵盖及风险：** 本轮不扩展全仓库审查或重新进行临床规则评估；独立 LLM 宿主仍未验收，病例独立性的真实性继续由 Skill 核实。
