# ACMG／CSpec 整体审查问题修复计划

> **交接要求：** 执行 agent 使用 `executing-plans`，按 A→B→C→D→E 顺序完成。此计划修复整体审查发现的九项问题，并按用户选择恢复官方基线锁文件。

**目标：** 统一证据评估指导，修复 CSpec 材料遗漏与错误吞没，纠正重复事实判断，不扩大现有架构。

**架构：** 继续使用现有 Skill、`ClinGenTool` 和确定性计算器；不新增规则引擎、插件、MCP 服务或依赖。

## A. 固定起点与执行边界

- [ ] 官方 upstream 唯一定义为 **https://github.com/mims-harvard/ToolUniverse**，固定基线为 `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6`。
- [ ] 在现有隔离工作区继续：

  ```text
  工作区：/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
  分支：codex/acmg-svi-cspec-lightweight
  本轮起点：4257921e12637126d36a2770fbfbc0b20de21e2b
  ```

- [ ] 检查 HEAD、分支及工作区状态；若出现新增改动，先核对归属，不重置或覆盖。
- [ ] 执行时保存本计划至目标工作区的 `docs/superpowers/plans/2026-09-10-acmg-svi-cspec-review-fixes.md`。
- [ ] 旧工作区 `/Users/zhaoyuancun/Documents/ToolUniverse-fork` 保持原状；不另建分支，不改用户 MCP 配置，不推送。
- [ ] 保持现有产品约定：生殖系小变异；适用 CSpec 优先；未知适用性或材料不完整暂停；特殊组合算法仍返回 `needs_review`。
- [ ] 公共工具参数、返回结构和积分阈值不变。单项 evidence 的 `needs_review` 继续作为未计分记录；是否阻断整体分类由现有阻断机制决定。

## B. 统一科学指导，清除旧入口重复赋码（问题 1–6）

修改 canonical ACMG Skill 的 `SVI_REFERENCE.md`，以及 `tooluniverse-variant-interpretation` 的 `SKILL.md`、`ACMG_CLASSIFICATION.md`、`CODE_PATTERNS.md`。

### B1. 删除旧入口中的独立赋码规则

- [ ] 删除 `ACMG_CLASSIFICATION.md` 中重复的 PVS1 简化表、SpliceAI→ACMG 表、功能实验→固定强度表及其他直接赋码捷径，改为引用统一 ACMG Skill。
- [ ] 保留数据源、原始预测分数解释及结构／调控信息收集说明；这些内容不能直接决定 ACMG 代码和强度。
- [ ] 删除旧 Skill 中"两种预测一致即 Strong PP3/BP4"、预测器共识兜底及其他绕过统一评估流程的赋码说明。
- [ ] 检查该入口引用的 `CHECKLIST.md`、`EXAMPLES.md`、`TOOLS_REFERENCE.md`，仅清除同类冲突引用，不扩大到其他专业 Skill。
- [ ] 将 `CODE_PATTERNS.md` 中的预测查询示例改为只返回原始分数、来源返回的标签和必要元数据：
  - 删除 `acmg_support`、`acmg_recommendation` 及投票产生的 `consensus`。
  - 保留现有查询函数名称与参数。
  - `comprehensive_pathogenicity_assessment()` 保留查询汇总功能，返回 `{"predictions": predictions}`，不赋 ACMG 代码。
  - 同步修改本目录内使用这些示例返回字段的地方。
- [ ] 不修改生产工具返回的数据供应方标签；本任务删除的是文档示例自行生成的 ACMG 判断。

### B2. 修正统一参考中的明确错误

| 问题 | 修改后的要求 | 验收反例 |
|---|---|---|
| NMD 逃逸一律 Strong | 删除旧入口简化表，沿用 canonical 决策树中的关键区域、截短比例、转录本等条件 | 无关键区域证据、缺失不足 10%、其他条件满足时为 Moderate，不能直接 Strong |
| 同义变异全部排除 PP3 | 同义变异不能使用氨基酸影响预测，但仍可进入合格的剪接 PP3 路径 | 非 canonical ±1/2 的同义变异，SpliceAI 0.8、无 RNA 结果时不能因"同义"而排除 PP3 |
| BP3 条件不完整 | 必须是无已知功能的重复区域；重复／低复杂度注释本身不够 | 功能性重复区域中的框内缺失，不得仅凭 repeat 注释赋 BP3 |
| BP2 trans 条件缺失 | 恢复"完全外显的显性基因／疾病"限制；cis 分支另行陈述 | 低外显率疾病中的未发病携带者，不能据此自动赋 BP2 |
| PM3 解释文字错误 | 明确相位未知 P 每次 0.5、LP 每次 0.25；分别需要两次、四次才能达到 1.0 | 两次合格的相位未知 LP 观察得到 PM3_Supporting，不是 Moderate |
| 多预测器投票赋码 | 强度来自预先选定的校准工具及适用规则，不来自投票数量 | 两个未校准工具一致，不能自动生成 Strong PP3/BP4 |

科学依据使用已核验的 PVS1 建议、Walker 2023 剪接建议、ACMG/AMP Table 4 和 PM3 v1.0。不凭记忆补写其他阈值。

### B3. 验证与提交

- [ ] 将上述六个反例作为来源核对清单写入实施记录，记录适用条件、预期代码／强度和来源位置。
- [ ] 对修改的 Python 文档示例进行语法检查；用简单假返回验证预测汇总只返回原始结果，不再生成 ACMG 建议。复用现有测试方式，不新增 Markdown 执行框架。
- [ ] 不用"文件包含某句话"的断言宣称 LLM 行为已通过验收。
- [ ] 完成三处 Skill 同步后提交：`fix: unify ACMG evidence guidance`。

## C. 补齐 CSpec 绑定校验与逐规则集材料检查（问题 7–8）

修改 `src/tooluniverse/clingen_tool.py`，测试进入现有 `tests/unit/test_clingen_cspec_tool.py`。

### C1. 逐个匹配规则集检查材料覆盖

- [ ] 先增加两个失败用例：索引匹配两个不同疾病／遗传模式的规则集，详情中第二个规则集分别为：
  1. 完全缺失；
  2. 存在，但 `criteriaCodes` 缺省、null 或为空列表。
- [ ] 在 `_search_cspec` 现有解析调用点，用匹配的规则集 ID 对照已解析 criteria 的归属，不能只检查整个 criteria 列表是否为空：

  ```python
  covered_ids = {item["rule_set_id"] for item in criteria}
  for rule_set_id in rule_set_ids:
      if rule_set_id not in covered_ids:
          entry["missing_materials"].append(
              f"criterion_specifications (rule_set_id={rule_set_id})"
          )
  ```

- [ ] 保留现有整体缺失标记，避免破坏依赖 `"criterion_specifications"` 的现有行为。
- [ ] 合法缺省造成的材料缺口只进入 `missing_materials`；不因此设置 `detail_structure_failed`。实际结构损坏继续沿用现有结构错误及 `partial_failures` 通道。
- [ ] 不改变内部 helper 的返回协议，不新增第三套材料状态，不要求规范必须提供 28 项。
- [ ] 测试必须同时确认：有效规则保留、缺失规则集 ID 可追溯、没有混用其他规则集、完整响应不会被误标。

### C2. 校验疾病与遗传模式绑定

- [ ] 在 `_cspec_index_structure_error` 中补校验，位于 `_cspec_diseases` 规范化之前。
- [ ] 新增的嵌套绑定校验限定于请求基因对应的条目；不扩大对明确无关基因内容的检查。
- [ ] 处理规则固定如下：

  | 字段形态 | 处理 |
  |---|---|
  | `diseases`／`modeOfInheritance` 缺省、null、空列表 | 保留既有合法缺省语义 |
  | 上述字段为数字、字符串或对象等错误容器 | 顶层 `status="error"` |
  | 非空列表包含非对象元素 | 顶层结构错误，不静默删除 |
  | disease 对象没有可用字符串 `label` | 顶层结构错误 |
  | inheritance 对象没有可用字符串 `@label` | 顶层结构错误 |

- [ ] 错误包含完整位置，例如：

  ```text
  index data[0].ruleSets[1].genes[0].diseases[2].modeOfInheritance[0].@label
  ```

- [ ] 不用 `str()` 修复非法类型，不把类型损坏转成空列表。
- [ ] 保留现有 `_cspec_diseases` 规范化职责，不在每个调用者重复添加校验。

### C3. 回归与提交

- [ ] 覆盖 `diseases=[有效项, null]`、`diseases=42`、错误的 inheritance 元素／标签及合法缺省值。
- [ ] 显式损坏必须返回工具错误，不能让 `TypeError` 逃出 handler。
- [ ] 先确认新增反例失败，修复后运行完整 CSpec 单元测试。
- [ ] 提交：`fix: disclose CSpec binding and rule-set gaps`。

**接口变化：** 只增加已有 `missing_materials` 中的具体说明，并将损坏输入送入已有错误通道；JSON Schema、SDK 包装和 metadata 无需重生成。

## D. 修复同一证据项内重复引用（问题 9）

修改 `src/tooluniverse/clinical_calculators_tool.py`，测试进入现有 `tests/unit/test_acmg_calculate_classification.py`。

- [ ] 先增加 SDK 失败反例：

  ```python
  def test_repeated_fact_within_one_code_does_not_block_sdk():
      record = met("PVS1", "VeryStrong", fact="assay-1")
      record["evidence_ids"].append("assay-1")
      payload = args(build_evidence(record, met("PM2", "Supporting")))

      data = _sdk_run(payload)["data"]

      assert data["classification_status"] == "computed"
      assert data["classification"] == "Likely Pathogenic"
      assert data["total_score"] == 9
  ```

- [ ] 只在收集事实所属代码时对单条记录去重，保持出现顺序：

  ```python
  for fact in dict.fromkeys(record["evidence_ids"]):
      fact_owners.setdefault(fact, []).append(record["criterion"])
  ```

- [ ] 保留返回的原始 evidence 记录；不修改引用内容，不做跨记录自动去重。
- [ ] 现有跨代码复用测试必须继续暂停；再覆盖"同一项内重复且另一项也引用该事实"的情况，所属代码列表不得重复。
- [ ] 不对 Schema 增加 `uniqueItems`，因为重复引用不是重复计分，也不是本轮要拒绝的非法输入。
- [ ] 测试通过后提交：`fix: deduplicate fact owners within one criterion`。

## E. 同步、恢复锁文件与最终验收

### E1. 发布副本同步

- [ ] 同步本轮涉及的 ACMG 和 variant-interpretation 两个 Skill 目录。
- [ ] Claude 副本按现有流程同步；Codex 使用 `scripts/sync-codex-plugin-skills.sh`，通过 `CODEX_PLUGIN_SKILLS_DEST` 输出到临时目录，只回填目标目录。
- [ ] 核对正文一致、引用文件齐全、Codex 不含 `disable-model-invocation`，且没有无关 Skill 改动。
- [ ] 不直接用 canonical 文件覆盖 Codex frontmatter。

### E2. 按用户选择恢复官方锁文件

- [ ] 仅恢复这一文件：

  ```bash
  git restore --source=752188d0f4daf9005d96edca0b7c8f0dfc7f10c6 -- uv.lock
  ```

- [ ] 验证 `git diff 752188d0 -- uv.lock` 为空。
- [ ] 不修改 `pyproject.toml`，不重新解析依赖，不重建现有 `.venv`。
- [ ] 本轮测试直接使用 `.venv/bin/python`；需要使用 `uv run` 或安装命令时必须带 `--frozen`，防止把升级重新写回。
- [ ] 更正运行文档和实施记录：恢复的官方锁本身未同步当前 manifest 的部分内容，例如 OCR extra。记录这是保留的上游问题，不宣称锁一致性检查通过，也不把现有环境说成"已按恢复后的锁重新安装"。
- [ ] 提交锁文件及记录更正：`chore: restore official dependency lock`。

### E3. 自动化回归

在恢复锁文件之后运行，记录实际退出码和统计：

```bash
env -u PYTHONPATH .venv/bin/python -m pytest \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_clingen_*.py \
  tests/unit/test_clinical_calc*.py \
  tests/integration/test_acmg_mcp_stdio.py \
  tests/unit/test_lazy_load_cache_consistency.py \
  tests/unit/test_backward_compatibility.py \
  tests/unit/test_tool_name_shortening.py \
  tests/unit/test_run_parameters.py \
  tests/unit/test_tools_package_imports.py \
  tests/unit/test_packaging_dependencies.py \
  tests/integration/test_smcp_schema_passthrough.py \
  tests/unit/test_codex_plugin.py \
  --no-cov -p no:cacheprovider
```

- [ ] 修改的 Python 文件通过现有 ruff 检查。
- [ ] 两段提交范围检查均通过：

  ```bash
  git diff --check 4257921e12637126d36a2770fbfbc0b20de21e2b..HEAD
  git diff --check 752188d0f4daf9005d96edca0b7c8f0dfc7f10c6..HEAD
  ```

- [ ] Claude 插件构建及测试在临时快照运行，避免写入受限工作区的 `dist`。基线和当前使用同一环境、相同参数，并关闭 `maxfail`。
- [ ] 注意 `git archive` 会因 `export-ignore` 排除 `tests/`；用对应提交的 `git show` 补入测试文件，不能因缺测试文件而跳过验证。
- [ ] 上轮对照为双方 **83 passed、6 项相同失败**；本轮以实际失败集合比较，不能仍写"五项基线失败"。

### E4. 交接与完成标准

- [ ] 实施记录逐项对应九个问题，列明修改、反例结果、提交及剩余限制。
- [ ] 科学规则核对、代码回归和真实 LLM 工作流验收分开报告。没有宿主调用轨迹时继续明确标注"LLM 工作流未验收"。
- [ ] 最终确认目标工作区干净、旧工作区状态保留、锁文件与固定官方基线一致、未推送。

**完成标准：** 六项指导问题得到修正或通过删除重复规则消除；三个程序反例转为正确结果；相关回归无新增失败；用户选择的锁文件恢复完成且上游不一致得到如实记录。无需新增架构或实现特殊 CSpec 组合算法。
