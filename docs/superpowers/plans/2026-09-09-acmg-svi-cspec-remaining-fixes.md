# ToolUniverse ACMG／CSpec 剩余问题修复与验收计划

> **交给实施 agent：**使用 `executing-plans` 顺序执行。本计划覆盖截至 `f11c6351` 尚未完成的修复，可以独立交接；此前已完成的科学规则、严格输入校验和环境修复继续保留。

**目标：**消除三类遗漏：通用规则材料不完整时仍分类、未列出基因的规范被误判为不适用、详情内部损坏未被披露。同步修复生成文件的行尾空白，并完成针对提交内容的验收。

**实现方式：**沿用现有两个工具和 Skill，只补必要的条件检查、CSpec 返回信息与测试。不新增服务、依赖、规则引擎或宿主拦截层。

## 1. 固定实施位置与约束

| 项目 | 定义 |
|---|---|
| 官方 upstream | **https://github.com/mims-harvard/ToolUniverse** |
| 官方基线 | `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6` |
| 本轮修复起点 | `f11c6351d8e4f83cd406e477f520f11138070674` |
| 实施分支 | `codex/acmg-svi-cspec-lightweight` |
| 实施 worktree | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 保持原状的旧工作区 | `/Users/zhaoyuancun/Documents/ToolUniverse-fork` |

- [ ] 开始时检查分支、HEAD 和工作区状态；若已有后续提交，先检查哪些问题已修复，不重置已有工作。
- [ ] 将本计划保存为工作区内 `docs/superpowers/plans/2026-09-09-acmg-svi-cspec-remaining-fixes.md`。
- [ ] 所有修改和验证均在上述实施 worktree 完成，不重新创建分支。
- [ ] 保持 Tavtigian 2020 阈值、28 项契约、BA1 独立路径、PP5/BP6 停用及现有组合上限。
- [ ] 保留已修正的 PM3／PM4 指导，不重新编写科学评估器。
- [ ] 不修改通用执行器、缓存、LLM 客户端、发布版本或用户 MCP 配置，不推送远端。
- [ ] 当前 SDK／MCP 已能运行，本轮不再重建环境；本地环境补救措施不移入 ToolUniverse 包代码。

## 2. 修改任务与接口约定

### A. 所有规则材料不完整时都暂停分类

修改计算器实现（`src/tooluniverse/clinical_calculators_tool.py:1238`）。

当前条件错误地限定了 `released_spec_found`。修复为：**只要合法布尔值 `applicable_rules_complete` 为 false，就暂停分类，与 CSpec 查询状态无关。**

- [ ] 保留现有布尔类型校验，不接受 `"false"`、0 或缺少字段。
- [ ] 使用现有复核原因 `incomplete_specification_material`，不新增另一套状态。
- [ ] 返回 `classification_status="needs_review"`、`classification=null`，保留证据和已有复核信息。
- [ ] 复核说明同时适用于通用 ACMG/SVI 材料和 CSpec 材料。
- [ ] 删除错误信息中"可明确改用通用规则分类"的建议，避免引导调用方绕过未完成的规范审阅。
- [ ] BA1 同样受材料完整性检查约束，不能提前返回 Benign。
- [ ] 更新工具 JSON 中该参数的说明，明确 true 表示当前所用规则的必要材料已完整核实，而非仅表示读过某个 CSpec 页面。

四个输入参数、现有枚举和输出结构均不变。

最小回归测试，复用现有测试辅助函数：

```python
def test_incomplete_generic_rules_pause():
    payload = args(build_evidence(
        met("PVS1", "VeryStrong"),
        met("PM2", "Supporting"),
    ))
    payload["rule_context"]["applicable_rules_complete"] = False

    data = run(payload)["data"]

    assert data["classification_status"] == "needs_review"
    assert data["classification"] is None
    assert "incomplete_specification_material" in {
        reason["reason"] for reason in data["review_reasons"]
    }
```

同一场景必须再通过公开 SDK 和 MCP 验证，不能只测内部处理函数。

### B. 保留未按基因列举的规范，取消错误的"空范围"推断

修改 CSpec 查询实现（`src/tooluniverse/clingen_tool.py:709`）、该工具 JSON 和 ACMG Skill。

[GN015 官方页面](https://cspec.genome.network/cspec/ui/svi/doc/GN015)明确提供线粒体基因规则。API 未逐一列出 `genes`，不能据此认定该规范不适用于任何基因。

#### B1. 返回结构只增加一个字段

保留：

- `data`：有明确基因绑定、匹配查询基因的规范。
- `total`：继续等于 `len(data)`。

在每个成功响应中增加：

```text
unresolved_scope_specs: array
```

每个候选复用现有元数据提取方式，包含：

```text
specification_id
version
vcep
url
api_url
rule_set_ids
scope_reason = "gene_binding_unavailable"
```

约定：

- 没有候选时也返回 `unresolved_scope_specs=[]`。
- `rule_set_ids` 仅列出范围待判定的规则集；空 `ruleSets` 对应空列表。
- 缺失版本或 VCEP 时保留缺失状态，不编造值。
- 同一规范的多个待判定规则集合并为一个候选。
- 一个规范同时有明确匹配和未知范围规则集时，可以同时出现在两处，不能丢失未知范围部分。
- 候选不计入 `total`，不宣称已经适用于查询基因。
- 不为候选自动下载全部详情；提供官方链接，由现有 Skill 按需补读。

#### B2. 索引处理规则

| 索引情况 | 处理 |
|---|---|
| 合法基因列表明确包含查询基因 | 按现有流程返回明确匹配 |
| 合法基因列表明确不包含查询基因 | 不作为该规则集的匹配 |
| `genes` 缺失、null 或空列表 | 保留为范围待判定候选 |
| Released 规范的 `ruleSets=[]` | 保留为范围待判定候选 |
| `genes` 是字符串、对象等错误类型，或列表元素损坏 | 保持结构错误，不伪装为空范围 |
| Draft 等非 Released 记录 | 保持现有过滤行为 |

- [ ] 删除代码、测试和实施记录中"JSON-LD 缺省说明确定不覆盖任何基因"的断言。
- [ ] 对命中或待判定范围的规则集，检查 ID 是有效非空字符串；不通过 `str()` 把对象、数值或空 ID 转成有效标识。
- [ ] 只有明确匹配和待判定候选都为空，且索引检查成功时，工具才能直接给出有效空结果的说明。
- [ ] 有候选但没有明确匹配时，说明应为"未发现显式基因匹配，仍有规范范围待确认"，不能提示直接采用通用分类。
- [ ] 不写 GN015 特例、线粒体基因白名单或规范文本自动分类器。

#### B3. Skill 如何消费候选

更新 ACMG Skill：

- [ ] 将 `data=[]` 直接进入通用规则的逻辑，改为同时检查 `unresolved_scope_specs`。
- [ ] 使用已有网页读取工具，根据官方材料确认候选对当前基因、疾病和遗传模式是否适用。
- [ ] 已确认不适用的候选可以排除，并记录来源；不要求逐项阅读其不相关的证据细则。
- [ ] 确认适用后，按现有 CSpec 流程读取所需规则。
- [ ] 尚无法排除或确认的候选，使 `cspec_lookup_status="unresolved"`，不能填 `no_released_spec`。
- [ ] 所有候选已排除，且没有其他适用规范时，才进入通用规则。
- [ ] 旧工具响应缺少新增字段时，不默认等同空列表，应提示更新工具或补充核实范围。
- [ ] 保留线粒体变异转入专用流程的范围限制；本轮不实现线粒体分类。

这样既不漏掉未按基因列举的规范，也不因它们存在就让全部核基因查询直接失败。

### C. 披露详情内部损坏，保留有效部分

修复现有 `_cspec_criteria_for_rule_sets` 及其唯一调用点，不新增解析框架。

- [ ] 将内部返回调整为"有效解析结果＋结构错误列表"，调用方统一写入现有失败标记。
- [ ] 检查相关层级的容器类型和元素类型：`ruleSets`、`criteriaCodes`、`evidenceStrengths`。
- [ ] 所选规则集中的证据代码及强度标签必须具有可用字符串；非法元素不能静默消失。
- [ ] 无法识别其归属的损坏规则集标记为结构问题；能够明确属于无关规则集的内容不混入所选规则。
- [ ] 区分合法缺失／空集合和显式类型错误。缺少可选说明文字不自动构成结构损坏，也不要求 CSpec JSON 必须像计算器输入一样提供恰好 28 项。

一旦发现相关结构损坏：

```text
data[i].detail_structure_failed = true
data[i].missing_materials 增加具体字段路径
partial_failures[specification_id] 记录结构错误
```

- [ ] 错误路径定位到具体元素，例如 `detail.ruleSets[0].criteriaCodes[2].evidenceStrengths[1]`。
- [ ] 原始 `specification` 保留；有效规则仍可展示，但必须和不完整标记同时返回。
- [ ] 不将非法内容替换成 `not_applicable`，不丢弃后返回无警告的成功结果。
- [ ] 官方材料补读后确实解决缺口，Skill 才能重新确认规则完整；仍未解决时暂停分类。
- [ ] 沿用 `partial_failures` 当前值类型和整体响应格式，不新增另一套错误协议。

本任务必须覆盖"有效内容夹杂一个非法元素"的情况，不能只测整个响应不是对象。

### D. 同步接口、生成文件和交付说明

- [ ] 更新 `ClinGen_search_cspec` 的描述及返回 Schema，加入 `unresolved_scope_specs`，并补齐已有 `detail_structure_failed` 的声明。
- [ ] 恢复计算器顶层参数的简短说明，尤其是规则完整性和证据输入要求，避免生成空白参数文档。
- [ ] 用现有生成器在临时目录生成，仅纳入两个有关包装和必要 metadata 更新。
- [ ] 清除计算器包装当前三处行尾空白；不修改全局生成器，不重新格式化整份工具 JSON。
- [ ] 同步实际修改的 Skill 发布副本，保留 Claude／Codex frontmatter 差异。
- [ ] 更新本地运行说明：示例须检查范围待判定候选及失败标记，不能只检查 `data` 是否为空。
- [ ] 在实施记录追加本轮修复，纠正 GN015 的错误解释，并记录真实验收结果。
- [ ] 当前环境补救措施继续作为本地说明；没有进程级证据时，不将隐藏标记的具体来源断言为已经查明。

## 3. 回归与工作流验收

### 自动化测试矩阵

沿用现有计算器、CSpec、SDK 和 MCP 测试文件，不新增测试框架。

| 场景 | 必须得到的结果 |
|---|---|
| 通用规则，完整材料，合法 synthetic 输入 | 保持原分类与分数 |
| 通用规则，`applicable_rules_complete=false` | `needs_review`，分类 null |
| Released CSpec，材料不完整 | 同样暂停 |
| BA1 满足但材料不完整 | 暂停，不直接返回 Benign |
| `genes` 缺失／null／空列表 | 返回范围待判定候选，不称为确定无规范 |
| 明确匹配＋范围待判定候选并存 | 两者均保留，`total` 只统计明确匹配 |
| 一个规范同时有匹配和未知范围规则集 | 不遗漏未知部分，不混合规则 |
| 所有记录均能明确判断且没有匹配 | 成功空结果，候选列表也为空 |
| `genes` 类型错误或损坏基因元素 | 明确错误 |
| 有效 criteria 中夹杂 null／字符串 | 保留有效部分并标记详情损坏 |
| 有效 strength 中夹杂非法元素 | 同上，错误路径可定位 |
| 合法但缺少可选文字说明 | 不误报为结构错误 |
| 一个规范详情损坏、另一个正常 | 正常规范仍返回，失败范围明确 |
| SDK／MCP 接收到材料不完整输入 | 与直接调用的暂停结果一致 |

补充要求：

- [ ] 删除或改写当前"缺少 genes 应无警告跳过"的错误测试。
- [ ] SDK／MCP 拒绝测试必须断言明确错误，不只断言"没有 computed"，避免连接失败或解析失败也让测试通过。
- [ ] 对上述修复先建立失败反例，再实施改动并复跑。
- [ ] 保留上一轮严格类型、上下文、分类边界、重复事实和组合上限测试。

执行相关回归：

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
  --no-cov -p no:cacheprovider
```

当前参考结果是此前分两批运行的 **317 通过、7 跳过**；修复后按实际结果记录，不固定通过数量，也不隐藏跳过项。

### 在线与实际 Skill 验收

- [ ] 在线查询 MYOC：明确匹配仍包含 GN019；GN015 等未按基因列举的规范作为范围待判定候选保留。
- [ ] 对 GN015，使用官方页面确认其线粒体适用范围；针对核基因场景，可以据此排除，不能仅凭缺少 `genes` 排除。
- [ ] 在线查询无明确基因匹配的输入：如果仍存在范围待判定候选，响应不得宣称已完成"无规范"判断。
- [ ] 固定资料下运行一次实际 Skill 流程，确认调用顺序包含候选范围判断、材料完整性判断及计算器调用。
- [ ] 保留"跳过计算器"请求与材料内嵌指令的真实宿主验收；记录输入、工具调用和最终回答。没有实际轨迹时明确列为未验收，不用单元测试代替。

在线检查与离线回归分开记录；网络失败不得伪装为成功空结果。

## 4. 提交检查与完成条件

建议三个逻辑提交：

1. 通用规则材料完整性检查及 SDK／MCP 回归。
2. CSpec 未知范围保留、详情损坏披露、Skill 映射及对应测试。
3. 必要生成文件、插件副本、文档和验收记录。

在提交后检查实际提交范围，不能仅对干净工作区运行无参数的 `git diff --check`：

```bash
git diff --check f11c6351d8e4f83cd406e477f520f11138070674 HEAD

git diff --check 752188d0f4daf9005d96edca0b7c8f0dfc7f10c6 HEAD
```

同时完成：

- [ ] 修改文件通过仓库现有 ruff 检查。
- [ ] 相关插件检查无新增失败；既有失败列出名称和基线证据。
- [ ] 无无关包装重生成、JSON 全文件格式化或依赖锁变化。
- [ ] SDK 和 MCP 确实从本 worktree 环境运行。
- [ ] 旧工作区保持原状，没有修改用户 MCP 配置或推送远端。
- [ ] 交付包含提交 SHA、测试命令、实际通过／失败／跳过项，以及三个遗漏的对应修复证据。
- [ ] 分开报告"代码修复完成""自动化验收完成""实际 LLM 工作流验收完成"。存在未验收项时，不将整体标为全部完成。
