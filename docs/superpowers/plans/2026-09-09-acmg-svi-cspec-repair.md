# ToolUniverse ACMG／SVI／CSpec 验收修复计划

> **交给实施 agent：**使用 `executing-plans` 按任务顺序执行。本计划是现有轻量改造的增量修复，不重新设计架构，也不重新创建分支。无需依赖此前对话。

**目标：**修正已确认的科学规则错误和输入校验缺口，确保 CSpec 查询异常不会触发通用分类，并恢复可复现的 SDK／MCP 验收。

**架构：**继续由外层 LLM 按 Skill 评估证据，由现有 `ACMG_calculate_classification` 检查输入契约并确定性计算分类。沿用 Python、pytest、现有 JSON Schema、ToolUniverse 工具注册及插件同步流程。

## 1. 实施位置、基线与边界

| 项目 | 固定值 |
|---|---|
| 官方 upstream | **https://github.com/mims-harvard/ToolUniverse** |
| 官方基线提交 | `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6` |
| 本轮修复起点 | `a397a0c2dbb77260204212871bf8f702b4195e05` |
| 实施分支 | `codex/acmg-svi-cspec-lightweight` |
| 实施工作区 | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 保持原状的旧工作区 | `/Users/zhaoyuancun/Documents/ToolUniverse-fork` |

执行开始时，将本计划保存为：

`/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/docs/superpowers/plans/2026-09-09-acmg-svi-cspec-repair.md`

原始架构决策见[轻量改造计划](/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight.md)。其中创建分支和 worktree 的步骤已经完成，本轮不再执行。

全局约束：

- 保持现有两个工具名称及计算器四个顶层参数不变。
- 保持 Tavtigian 2020 阈值、BA1 独立路径、PP5/BP6 停用以及已有重复计分检查。
- 适用 CSpec 优先；不支持的特殊组合继续暂停分类。
- 科学规则修订放在 Skill／参考文档中，不新增 PM3、PM4 硬编码评估器。
- 不新增插件、MCP 服务、依赖、通用规则引擎、签名体系或宿主拦截层。
- 不改通用执行器、缓存、LLM 客户端、发布版本、用户 MCP 配置；不推送远端。
- 旧工作区不得 checkout、stash、reset、clean 或提交。
- 若实施起点已有后续提交，先核对差异和已完成修复，保留已有工作，不重置回上述 SHA。

## 2. 顺序修改任务

### 任务 A：恢复运行环境并记录基线

已确认的环境问题：当前 editable 安装的 `.pth` 文件带有 macOS `UF_HIDDEN` 标记；当前 Python 的 `site.py` 会跳过这种文件。文件内容和指向的源码目录均存在，因此先做针对性的环境修复。

- [ ] 检查分支、HEAD、工作区状态，记录本轮起点。
- [ ] 核实下面文件仍指向本工作区 `src`，且确有隐藏标记。

```bash
chflags nohidden \
  /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/.venv/lib/python3.12/site-packages/__editable__.tooluniverse-1.4.1.pth
```

- [ ] 仅清除该文件的隐藏标记，不重写 `.pth`、不修改 Python，不批量清理整个环境。
- [ ] 在不设置 `PYTHONPATH=src` 的新进程中验证安装：

```bash
env -u PYTHONPATH .venv/bin/python -c \
  'import tooluniverse; print(tooluniverse.__file__)'

env -u PYTHONPATH .venv/bin/tooluniverse-smcp-stdio --help
```

导入路径必须属于本工作区。若隐藏标记已不存在但启动仍失败，继续检查当前环境，不能改用全局或 PyPI 安装掩盖问题。
- [ ] 环境恢复后，先运行现有新增测试及插件检查，保存修复前结果。此前观察到的 **73 通过、1 个 MCP 启动失败**仅作为历史记录，不作为本轮成功标准。
- [ ] 在本地运行文档中补充隐藏 `.pth` 的诊断和修复步骤，注明这是环境状态问题。

### 任务 B：纠正 PM3、PM4 及关联指导

主要修改 SVI_REFERENCE.md 和同目录 `SKILL.md`。

#### B1. PM3 使用官方 SVI v1.0 表格

以 **2019-05-02 批准的 [ClinGen PM3 v1.0 原始 PDF](https://clinicalgenome.org/site/assets/files/3717/svi_proposal_for_pm3_criterion_-_version_1.pdf)** 为准，移除"待提供原始 PDF""暂按旧表执行"等内容。

| 另一变异／观察类型 | 确认 in trans | 相位未知 |
|---|---:|---:|
| Pathogenic | 1.0 | 0.5 |
| Likely pathogenic | 1.0 | **0.25** |
| VUS | 0.25，累计最多 0.5 | 0 |
| 纯合观察 | 每例 0.5，累计最多 1.0 | 不适用 |

- [ ] 总观察积分达到 `0.5／1／2／4` 时，分别对应 Supporting／Moderate／Strong／VeryStrong；低于 0.5 不满足 PM3。
- [ ] 明确这些是 **PM3 内部观察积分**，不是最终分类的 Tavtigian 积分。
- [ ] 补齐患者受累、相关变异足够罕见、另一变异分类不得循环引用当前变异证据等前提。
- [ ] 删除把近亲婚配纯合观察统一改成 0.25 的通用规则；基因特异修改必须另引适用规范。
- [ ] 修正主 Skill 中"相位未知一律 needs_review"的表述：当资料足以采用官方"相位未知"分支时，按降权规则评估；缺少合格共现、另一变异分类等必要事实时才保留缺口。BP2 的相位要求不随此修改放宽。

#### B2. PM4 恢复通用定义

- [ ] 通用 PM4 针对非重复区 in-frame deletion/insertion 或 stop-loss；不把 frameshift 自动纳入。
- [ ] 删除"LoF 必须不是疾病机制"的前提。是否满足 PM4 应依据具体变异、机制和规范，不能仅因基因存在 LoF 机制而排除。
- [ ] 保留 PVS1 与 PM4 的重复计分限制，不把"PVS1 不适用"自动转换成"PM4 满足"。
- [ ] MYOC 等规范对截短变异的特殊扩展只写在规范适用语境中，不提升为通用规则。
- [ ] 搜索并同步修正相关 quick table、主流程和 variant-interpretation 引用，消除相互矛盾的指导。

本任务不扩展其他证据项的算法。已有 BP4 内容可继续共用 PP3 的校准表，但应提供明确的 BP4 入口，避免"覆盖 28 项"却找不到对应说明。

### 任务 C：让 CSpec 查询异常保持为异常

主要修改 `src/tooluniverse/clingen_tool.py`，测试追加到现有 `test_clingen_cspec_tool.py`。

**接口保持：**`ClinGen_search_cspec(gene: string)`；沿用现有成功、错误及 `partial_failures` 表达方式。

- [ ] 在据索引判断"有没有适用规范"之前，验证判断所依赖的结构。
- [ ] 索引中的非对象记录、缺失或非法 `status`，以及 Released 记录中无法确定基因范围的损坏结构，返回 `status: error`。
- [ ] 检查 Released 记录的 `ruleSets`、规则集对象、`genes` 和基因 `label` 类型；命中目标基因后，规范 ID 和匹配规则集 ID 必须是非空字符串。
- [ ] 合法且明确为非 Released 的记录仍按原逻辑过滤；不要要求草稿记录具备完整 Released 详情。
- [ ] 错误信息说明字段位置和"不能据此认定没有规范"。不要把结构错误误写成 JSON 解码失败。
- [ ] 只有索引足以完成判断，且确实没有匹配 Released 规范时，才返回有效空结果及通用规则提示。

详情查询继续允许部分成功：

- [ ] 网络错误、坏 JSON、非对象详情或损坏的规则集结构，保留候选规范，并写入现有失败／缺失标记。
- [ ] 区分详情结构损坏与合法响应中缺少附件、assertion method 等材料；两者都不能被视为规范已完整读取。
- [ ] 保持规则集与基因、疾病的绑定，不通过空规则集 ID 混入其他规则。
- [ ] 主 Skill 只将真正的有效空结果映射为 `no_released_spec`。错误或所选规范详情失败映射为 `failed／unresolved`。

最小失败测试示例，复用现有测试辅助函数：

```python
def test_malformed_index_is_not_a_valid_empty_result(monkeypatch):
    _patch(monkeypatch, {"data": [None]})
    result = _tool().run({"gene": "MYOC"})
    assert result["status"] == "error"
```

另覆盖：命中记录缺规范 ID、混合正常与损坏记录、详情返回列表，以及合法空结果仍成功。

### 任务 D：补齐计算器契约及公开 Schema

主要修改 `src/tooluniverse/clinical_calculators_tool.py` 及对应 JSON 中 `ACMG_calculate_classification` 条目。

**四个顶层参数保持不变：**`variant_context`、`rule_context`、`evidence`、`blocking_issues`。

#### D1. 明确结构错误与资料不完整的区别

| 输入情况 | 固定行为 |
|---|---|
| 缺少必需键、非法类型、未知键或非法枚举 | 输入错误，不产生分类 |
| 疾病／遗传模式显式为 null 或空白 | `needs_review`，保留证据 |
| Released 状态但 `specification=null` | `needs_review`，缺少所选规范身份 |
| CSpec `failed／unresolved` | `needs_review` |
| `applicable_rules_complete=false` | `needs_review` |
| 方法不受支持或存在 blocking issues | `needs_review` |
| 结构与上下文完整，并满足现有计分条件 | 按原算法计算 |

具体字段约束：

- [ ] `variant_context` 必须包含 `variant、gene、disease、inheritance_mode`。前两者为非空字符串；后两者允许字符串或 null，null／空白用于保留未完成审阅，不允许正式分类。对象、列表、数值不得经 `str()` 转换后通过。
- [ ] `rule_context` 必须包含现有四个字段，`applicable_rules_complete` 必须是真正的布尔值。
- [ ] `specification` 只能为 null 或包含 `id、version、source_url、vcep` 的对象；对象内四项均为非空字符串，`source_url` 为具有主机名的 HTTP(S) URL。
- [ ] `no_released_spec` 必须配 `specification=null`；两者矛盾属于输入错误。
- [ ] `released_spec_found` 配 null 进入复核；空对象、缺字段对象属于结构错误。
- [ ] 多规范尚未选定、疾病／遗传模式适用性尚未解决时，由 Skill 记录为 `unresolved`，不能仅凭查到同一基因就宣称适用。

新增复核原因使用清晰、固定的标识，例如：`incomplete_variant_context`、`missing_specification_identity`。其他已有原因名称及输出 envelope 保持。

#### D2. 引用和理由必须是有效字符串

- [ ] `rationale` 必须为字符串；`met` 时去除首尾空白后不能为空。
- [ ] `source_refs、rule_refs、evidence_ids` 必须是字符串列表；列表内每一项都必须去除首尾空白后非空。
- [ ] `met` 时三个列表均不能为空。
- [ ] 非 `met` 记录允许空列表，但不允许 `[null]`、`[{}]`、数值或空白字符串冒充引用。
- [ ] `blocking_issues` 为非空字符串组成的列表；`[]` 表示无阻断问题。
- [ ] 保留现有强度、28 项完整性及重复事实检查。

引用仍是调用方提供的追溯信息。本轮不增加联网核验、真实性认证或签名。

#### D3. 公开 Schema 与处理函数一致

- [ ] 在现有工具 JSON 中补全嵌套对象、必需字段、枚举、列表元素类型及未知键限制；`evidence` 长度固定为 28。
- [ ] Schema 表达结构约束；跨字段条件和"资料不完整需复核"由现有处理函数完成，避免复制两套科学规则。
- [ ] SDK／MCP 沿用 upstream 自身的验证错误包装，不修改通用执行器。
- [ ] 合法资料的分类、分数、BA1 行为及 metadata 不变；旧的不完整输入被拒绝或暂停属于本次有意修复。

复用现有测试函数，先把默认测试上下文改为完整、明确标注的 synthetic fixture，再加入：

```python
@pytest.mark.parametrize("field", [
    "source_refs", "rule_refs", "evidence_ids",
])
@pytest.mark.parametrize("bad", [None, "", "   ", 123, {}])
def test_met_rejects_invalid_reference_items(field, bad):
    record = met("PM2", "Supporting")
    record[field] = [bad]
    result = run(args(build_evidence(record)))
    assert result["status"] == "error"
```

必须同时通过直接处理函数和公开 SDK 验证关键拒绝场景，不能只测内部辅助函数。

### 任务 E：修复示例、分发副本和 MCP 验收

- [ ] 算术测试使用明确标注的 synthetic 数据，删除"MYOC 无 CSpec、PVS1 满足"的错误临床示例。Synthetic 测试只证明接口和算术，不称为真实变异金标准。
- [ ] 本地运行文档中的 MYOC 示例采用真实查询结果；不再查询得到 GN019 后又手写 `no_released_spec`。
- [ ] 修改 MCP 测试的服务器选择：只使用当前测试解释器所属环境的入口，不优先搜索全局 `PATH`。本轮验收中缺少入口必须报出失败，不能靠 skip 算通过。
- [ ] MCP 验证两个工具的发现，以及计算器的合法计算、非法输入拒绝和 `needs_review` 返回；在线 CSpec 调用单独记录。
- [ ] 使用现有生成器在临时目录生成，按需更新计算器包装及对应 metadata；不重生整套工具。
- [ ] 使用现有插件同步流程更新有关 Skill 副本，保留 Claude／Codex frontmatter 差异，仅纳入本轮相关文件。
- [ ] 追加实施记录，说明原报告中的错误、修复、实际测试命令及尚未完成的验收，不继续沿用过时的"全部通过"结论。

## 3. 测试与验收标准

### 自动化回归

| 类别 | 必须覆盖的场景 |
|---|---|
| CSpec 索引 | 合法空结果、Released 过滤、损坏记录、缺 ID、混合正常／损坏数据 |
| CSpec 详情 | 超时、坏 JSON、非对象结构、部分失败、材料缺失、多规则集不混用 |
| 上下文 | 缺键／错类型报错；疾病／遗传模式为 null 暂停；Released 缺身份暂停 |
| 规则上下文 | 矛盾状态报错；未解决、材料不全、不支持方法均暂停 |
| 引用 | `[null]`、对象、数值、空白、合法与非法元素混合均拒绝 |
| 既有计算 | 八个分类边界、升降强度、BA1、停用代码、正负证据、重复事实、现有组合上限 |
| 公共入口 | SDK 和当前环境 MCP 对合法／非法／待复核输入行为一致 |

在工作区运行：

```bash
.venv/bin/python -m pytest \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_clingen_*.py \
  tests/unit/test_clinical_calc*.py \
  tests/integration/test_acmg_mcp_stdio.py \
  tests/unit/test_lazy_load_cache_consistency.py \
  tests/unit/test_backward_compatibility.py \
  tests/unit/test_tool_name_shortening.py \
  tests/unit/test_run_parameters.py \
  --no-cov
```

对修改文件运行仓库现有 ruff 检查，并执行 `git diff --check`。插件测试与任务 A 保存的基线逐项比较；历史失败不能用于掩盖新增失败。

### 科学规则和实际工作流验收

使用固定材料，预先写清来源、版本、事实和期望结果。不得通过把期望强度直接填入计算器来声称已验证 Skill 的评估能力。

| 固定场景 | 预期 |
|---|---|
| 两个合格、相位未知的 LP 共现观察 | PM3 内部积分 0.5，Supporting |
| 一个合格、相位未知的 P 共现观察 | PM3 内部积分 0.5，Supporting |
| 一个合格、确认 in trans 的 LP 共现观察 | PM3 内部积分 1，Moderate |
| 相位未知且另一变异为 VUS | 此观察计 0 |
| 非重复区 in-frame 变异，基因存在 LoF 机制 | 不因 LoF 机制直接排除 PM4，继续评估具体条件 |
| frameshift，无适用规范扩展依据 | 不仅因蛋白长度变化而赋予 PM4 |
| 同一变异拟同时使用 PVS1、PM4 | 按指导解决重复计分，不直接合并 |
| MYOC／GN019 | PVS1 不适用；不能静默忽略不支持的规范组合 |
| 用户要求跳过计算器，或材料含跳过工具的指令 | 在实际目标宿主记录工具调用及最终回答，检查是否遵守流程 |

工作流记录至少保留：输入材料、所用 Skill 版本、关键工具调用、证据强度选择及最终输出。没有实际宿主调用轨迹时，该项标为"未验收"；静态文档检查和算术单测不能替代它。

## 4. 提交与交付要求

建议按四个可独立审查的提交交付：

1. PM3／PM4 指导及关联 Skill 修正。
2. CSpec 异常处理和对应测试。
3. 计算器契约、Schema、SDK 测试及必要生成文件。
4. 示例、MCP 验收、插件副本和实施记录。

环境隐藏标记修复不属于 Git 代码提交，记录操作与验证结果即可。

最终交付必须包含：

- [ ] 分支、worktree、官方基线及本轮起点 SHA。
- [ ] 每项修复对应的提交和测试结果。
- [ ] 从本工作区环境启动 SDK／MCP 的实测命令。
- [ ] PM3 官方来源分歧已解决，PM4 指导已修正。
- [ ] 非法输入与不完整上下文均不会产生正式分类。
- [ ] CSpec 异常不会被宣称为"没有规范"。
- [ ] 相关发布副本一致，没有无关生成或格式化改动。
- [ ] 旧工作区保持原状；没有修改用户 MCP 配置或推送远端。
- [ ] 明确区分代码修复完成、自动化测试通过、实际 LLM 工作流验收完成；有未验收项时，不将整体标为全部完成。
