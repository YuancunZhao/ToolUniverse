# CSpec 策略收尾与 ID 校验修复计划

> **交接要求：** 执行 agent 使用 `executing-plans`，按 A→B→C→D 顺序完成；从现有提交继续，不重新实施此前改造。

**目标：** 修复两处已复现的遗漏，并明确"CSpec 优先、通用规则补充、未知情况暂停"的工作流。

**架构：** 继续使用官方 ToolUniverse 的现有 ClinGen 工具、Skill 和计算器。共享解析函数负责 ID 校验；Skill 负责规范适用性与证据解读；计算器保留当前支持范围。

**技术：** Python、现有 pytest 测试、Markdown Skill；不新增依赖或框架。

**依据：** 上一轮 `2026-09-09-acmg-svi-cspec-remaining-fixes.md`、本次审查的两个反例，以及已确认的 CSpec 策略。本计划是增量收尾，特殊组合算法不在本轮实现。

## A. 核对起点与保存计划

- [ ] 官方 upstream 明确定义为 **https://github.com/mims-harvard/ToolUniverse**，固定基线为 `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6`；用户 fork 和当前分支均不称为 upstream。
- [ ] 在以下工作区继续，不另建分支：

  ```text
  工作区：/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
  分支：codex/acmg-svi-cspec-lightweight
  本轮起点：559002a1d4dded998472858543419a5956d67466
  ```

- [ ] 先检查 `git status`、分支、HEAD 和 worktree。若起点变化，先审阅新增差异再继续，不自动重置。
- [ ] 保留旧工作区 `/Users/zhaoyuancun/Documents/ToolUniverse-fork` 的全部状态，不 checkout、stash、reset 或 clean。
- [ ] 执行阶段将本计划保存到目标工作区的 `docs/superpowers/plans/2026-09-09-acmg-svi-cspec-final-fixes.md`。
- [ ] 沿用现有 `.venv`；不改用户 MCP 配置，不更新 `uv.lock`，不推送。

## B. 在共享函数中修复 ID 校验

**修改位置：** `src/tooluniverse/clingen_tool.py`（`_cspec_id`）。
**测试位置：** `tests/unit/test_clingen_cspec_tool.py`。

**已复现问题：** `_cspec_id()` 将数字、对象和纯空白转换为有效字符串；详情中的非法 ID 因此可能被误认为属于无关规则集，绕过损坏披露。

### 实施步骤

- [ ] 先增加失败测试，覆盖以下输入与结果：

  | 场景 | 必须得到的结果 |
  |---|---|
  | 明确匹配的规则集 ID 为数字、对象或纯空白 | 顶层 `status="error"` |
  | 未列出基因的候选规则集使用上述非法 ID | 顶层 `status="error"`，不得生成伪造的候选 ID |
  | 有效详情后混入一个非法 ID 的规则集 | 保留有效规则，并披露无法确定归属的结构损坏 |
  | 合法字符串 ID、完整 IRI | 保持原有解析与匹配结果 |
  | 明确属于无关规则集的合法 ID，其内部内容损坏 | 不污染所选规则集 |

- [ ] 复用现有 `_index_record`、`_detail_payload`、`_patch`，不另建测试设施。索引反例示例：

  ```python
  @pytest.mark.parametrize("raw_id", [123, {"bad": "id"}, " \t "])
  @pytest.mark.parametrize("unresolved", [False, True])
  def test_invalid_rule_set_id_is_error(monkeypatch, raw_id, unresolved):
      record = _index_record()
      record["ruleSets"][0]["@id"] = raw_id
      if unresolved:
          del record["ruleSets"][0]["genes"]
      _patch(monkeypatch, _index(record))

      result = _tool().run({"gene": "MYOC"})

      assert result["status"] == "error"
  ```

- [ ] 运行新测试，确认修复前失败，再修改共享函数：

  ```python
  @staticmethod
  def _cspec_id(iri: Any) -> str:
      """Extract an ID from a non-empty string; invalid input yields empty."""
      if not isinstance(iri, str):
          return ""
      return iri.strip().rstrip("/").rsplit("/", 1)[-1].strip()
  ```

- [ ] 核对全部调用点。索引中的规范 ID 校验也复用该函数判空，避免规范 ID 经规范化后为空却继续生成结果；为纯斜杠等归一化为空的值补一个反例。
- [ ] 保持现有错误分流：
  - 索引中规范 ID、命中规则集 ID 或候选规则集 ID 无效：返回现有 `status="error"`。
  - 详情中的规则集 ID 无效：先记录结构错误，再跳过该元素；不能进入"明确无关规则集"的过滤分支。
- [ ] 详情反例必须同时断言：有效 `criterion_modifications` 保留、`detail_structure_failed=true`、`missing_materials` 含具体 `ruleSets[n].@id` 路径、`partial_failures` 包含该规范。
- [ ] 保留字符串形式的数字 ID，例如 `"635003681"`。本轮不引入 URI 校验库或 ID 格式正则。
- [ ] 新测试及整个 CSpec 测试文件通过后，单独提交本任务。

**接口变化：** 公共参数、返回字段及错误格式不变；此前被错误接受的非法 ID 改为进入已有错误路径。无需重生成工具包装或 metadata。

## C. 补齐 Skill 的候选裁决与规则优先级

**主要修改位置：** ACMG Skill（`skills/tooluniverse-acmg-variant-classification/SKILL.md`），并同步其 `SVI_REFERENCE.md` 开头的优先级说明和运行文档。

### 候选裁决改成共同前置步骤

- [ ] 删除候选处理行的 `empty data` 限制，在查询结果分支之前明确：

  ```text
  On every successful lookup, inspect both data and unresolved_scope_specs.
  Resolve every unresolved-scope candidate even when data already contains
  an explicit match. An explicit match does not resolve other candidates.
  ```

- [ ] 对每个候选，根据官方材料核实当前基因、疾病和遗传模式：
  - 确认不适用：排除并记录来源，无需阅读无关证据细则。
  - 确认适用：纳入现有 CSpec 阅读与评估流程。
  - 无法确认或排除：设置 `cspec_lookup_status="unresolved"`，暂停最终评级。
- [ ] 同一规范同时出现在 `data` 和候选中时，按候选中的 `rule_set_ids` 核实剩余范围，不能因规范 ID 已出现就将候选去重丢弃。
- [ ] 旧响应缺少 `unresolved_scope_specs` 时，无论 `data` 是否为空，都不能假定候选已检查；更新工具或补充人工核实。
- [ ] 只有所有候选都已裁决，且确实没有适用规范时，才能使用 `no_released_spec`。

### 将规则优先级写清楚

- [ ] 在 Skill 与参考文件中保持同一表述：

  | 情况 | 执行策略 |
  |---|---|
  | 适用的 Released CSpec 有特别规定 | 使用 CSpec 的条件、阈值、强度及禁用规定 |
  | CSpec 明确允许沿用通用规定，或完整材料确认该部分沿用基础规则 | 使用通用 ACMG/AMP + ClinGen SVI |
  | 已确认没有适用 CSpec | 使用通用 ACMG/AMP + ClinGen SVI |
  | API 缺项、材料不完整或适用性未解决 | 补读官方材料；不能将缺失解释为允许使用通用规则 |
  | CSpec 明确某证据项不适用 | 标记 `not_applicable`，不能用通用规则重新启用 |

- [ ] 继续明确区分证据评估和最终组合：Skill 可以解释 CSpec 的特殊证据规则；计算器目前仅支持固定的 `tavtigian2020` 方法。特殊组合方法、联合上限或评级阈值继续返回 `needs_review`，不得改填通用方法绕过暂停。
- [ ] 不修改计算器算法，不新增 CSpec 配置引擎，不给 GN015 写特例。

### 同步与场景检查

- [ ] 同步 canonical、Claude plugin、Codex plugin 三处对应 Skill 文件。Claude 副本保持现有方式；Codex 使用已有同步脚本输出至临时目录，只回填本次涉及的 Skill，保留其 frontmatter 转换。
- [ ] 更新运行文档中 MYOC 示例的说明，明确已有匹配也必须裁决候选。
- [ ] 使用现有固定响应逐项检查流程：匹配＋候选、同一规范的匹配与候选并存、仅候选、两者皆空、旧响应缺字段。不要用"Markdown 包含某句话"的测试冒充 LLM 行为验收。
- [ ] 同步完成后单独提交本任务。

## D. 回归、验收与交接

### 自动化验证

- [ ] 从目标工作区执行现有相关回归集：

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
    --no-cov -p no:cacheprovider
  ```

- [ ] 运行修改 Python 文件的现有 ruff 检查，并检查两个提交范围：

  ```bash
  git diff --check 559002a1d4dded998472858543419a5956d67466..HEAD
  git diff --check 752188d0f4daf9005d96edca0b7c8f0dfc7f10c6..HEAD
  ```

- [ ] 按 pytest 实际输出记录 passed、skipped、deselected、failed，不通过 collect 数量倒推通过数。上轮参考值为 **338 passed、7 skipped、1 deselected**，本轮新增测试后的数量以实测为准。
- [ ] 确认 SDK/MCP 原有合法计算、非法输入拒绝、材料不完整暂停、特殊组合暂停的用例继续通过。

### 实际 LLM 工作流验收

- [ ] 有真实宿主时，使用固定资料记录调用轨迹（明确匹配＋无法裁决候选、可排除候选、不支持特殊组合、跳过计算器请求/内嵌指令四场景）。
- [ ] 若宿主不可用，明确记录"真实 LLM 工作流未验收"；不为完成此项安装新宿主或修改用户配置，也不将工具链演练称为 LLM 验收通过。

### 最终交付

- [ ] 更新实施记录，列出本轮提交、实际命令与结果、剩余限制。
- [ ] 分别报告"代码修复""自动化验证""真实 LLM 工作流验证"的状态。
- [ ] 确认目标工作区干净、旧工作区状态保留、无无关生成文件变更、未推送。

**完成标准：** 非法 ID 不再静默通过；候选裁决不受 `data` 是否为空影响；CSpec 优先级在三处 Skill 中一致；相关回归通过；特殊组合仍如实标记为当前未支持。
