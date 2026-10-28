# 2026-10-28 复查剩余问题修复计划

## 1. 目标与执行边界

> 交给执行 Agent：使用 executing-plans，按 A→B→C 串行实施；每批独立提交，不 push。

**目标：** 修复区域扫描的提前退出和计数校验缺口，补强验收测试，纠正案例及记录。保留上一轮已通过的修复，不重新设计接口。

| 项目 | 起点／要求 |
|---|---|
| 工作目录 | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 分支 | `codex/acmg-svi-cspec-lightweight` |
| 当前 HEAD | `08c4a776815725b922304ee646ace832e64cf644`，工作区干净 |
| 官方 upstream | [mims-harvard/ToolUniverse](https://github.com/mims-harvard/ToolUniverse)，已合入基线 `2128ff57` |
| 最新回归 | **1045 passed、1 skipped**，实际展开为 **41 个测试文件** |
| 已选策略 | 区域详情不完整时整次 error；保留旧版每个 `variation_set` 的结果粒度，不按 UID 去重 |

不改计算器、CSpec、依赖、锁文件、工具 Schema、SDK 包装、服务器默认值或全局配置；不改 `ToolUniverse-fork`，不覆盖已安装 Skill。

参考：[本轮反例结果](/private/tmp/ToolUniverse-recheck-20261028-probes.json)、[反例脚本](/private/tmp/ToolUniverse-recheck-20261028-probes.py)。临时文件缺失时按下文重新构造。

## 2. A 批：修复区域扫描并补齐真实反例

修改 `src/tooluniverse/clinvar_tool.py` 和 `tests/unit/test_clinvar_region_scan_completeness.py`。

### A1．完整遍历，保持结果粒度

- [ ] 删除"发现一个可用坐标就结束该 UID 扫描"的退出逻辑。
- [ ] 遍历所有 `variation_set`，以及其中的定位条目；不得因已找到重叠结果而跳过后续校验。
- [ ] 仅使用请求 assembly、请求染色体的定位判断重叠。明确属于其他 assembly／染色体的定位不参与结果，其坐标不必满足当前查询要求；无法识别归属的损坏元素明确报错。
- [ ] 复用现有 `_optional_record_list` 和 `_parse_span_int`，在调用处补 UID／字段路径，不新增校验框架。
- [ ] 每个 `variation_set` 最多输出一条记录，选择其第一条有效重叠定位；同一 UID 的不同 `variation_set` 可以分别返回，不新增去重。
- [ ] 全部相关条目校验结束后才返回成功；后续发现损坏时整次 error，不返回已累积的部分结果。

计数与排序保持现有约定：

- `n_candidates`：返回的候选 ID 数。
- `n_overlapping`：生成的重叠结果条数，不改成唯一 UID 数。
- 按 span 升序排序，之后应用 `max_results`。
- 候选截断与详情失败继续区分：前者披露截断，后者整次 error。

### A2．覆盖 count=0 的矛盾载荷

共享 eSearch 校验成功后直接读取已验证的 count，删除不可达的 `None` 回退。

将：

```python
if 0 < total_available < len(ids):
```

改为：

```python
if total_available < len(ids):
```

保留 `count>0 且 idlist=[]` 的错误检查，不改变共享校验器对 `retmax=0` 计数查询的兼容行为。

### A3．测试必须命中目标原因

新增下列失败反例，先在起点确认失败，再修生产代码：

| 场景 | 修复后预期 |
|---|---|
| 第一 `variation_set` 不重叠，第二个重叠 | 返回后者，不能完整零结果 |
| 两个 `variation_set` 都重叠、UID 相同 | 保留两条结果，计数为 2 |
| 同一 `variation_set` 前一定位不重叠、后一定位重叠 | 返回该集合的第一条有效重叠定位 |
| 已有健康定位，后续集合或相关定位损坏 | 整次 error |
| 已找到重叠，后续当前 assembly 坐标损坏 | 仍为整次 error |
| 明确其他 assembly／染色体的定位坐标不可用 | 不污染当前查询 |
| `count=0、idlist=["1"]`，详情健康 | eSearch 阶段 error，详情请求次数为 0 |
| 健康零结果、全部不重叠、正常截断、结果上限 | 原有行为不变 |

**注意：** 零计数反例要提供健康详情备用。否则旧代码可能因缺少假响应而报错，造成测试假通过。

### A4．重写跨批失败测试

从现有"两条 ID"参数化测试中移除 `later-chunk-failure`，新增独立测试：

- eSearch 返回 **201 个 ID**。
- 第一批 200 条详情全部健康，其中至少一条重叠。
- 第二批一个 ID 的请求返回 HTTP 503。
- 断言详情请求发生 **两次**，失败原因包含 eSummary 和 HTTP 503，最终整次 error。
- 增加两批均健康的控制用例，证明正常第二批能够被处理。

该跨批控制在当前代码上可能已经通过，应如实标注为覆盖补强，不伪称先失败后修复。

**提交：**

```text
fix(clinvar): complete region scans and validate zero counts
```

## 3. B 批：纠正案例预期和示例审查状态

### B1．案例 17 使用真实计算器返回值

修改 `skills/tooluniverse-acmg-variant-classification/evals/evals.json` 和 `tests/unit/test_acmg_skill_evals.py`。

- [ ] 将案例 17 关于计算器回执的表述统一为 **`computed / VUS / total_score 4`**。
- [ ] 不全仓替换"Uncertain significance"；ClinVar 等外部数据库的标签不属于此次修正。
- [ ] 保留案例 ID、提示词、事实附件和 PS1／PM5 解释，不新增案例。
- [ ] 增加实际计算器调用：按案例 17 上下文构造完整 28 条记录，只有 PS1 Strong 计分，PM5 为 not_met，PP5/BP6 为 deprecated，其余按无资料记录。
- [ ] 断言实际返回 `classification_status="computed"`、`classification="VUS"`、`total_score=4`。
- [ ] 用实际返回构造上述规范短语，检查它存在于案例预期和断言中；替换当前仅搜索单词及任意数字"4"的薄弱检查。

这是离线计算器契约测试，不能标为 LLM 判断验收。计算器实现保持不变。

### B2．移除没有依据的双星补写

修改 `skills/tooluniverse-variant-interpretation/EXAMPLES.md:260`。

将 TP53 示例的 review-status 行改为：

```text
| Review Status | Not specified in this illustrative example |
```

删除该行的星号及新增的 `no conflicts`；保留原有分类、提交者数量和示例属性。不通过补造"一致"来解释双星，也不为此开展新的在线分类更新。

在现有文档测试中加入针对该示例的检查，禁止重新将"3 个提交者"自动解释成"无冲突双星"。

### B3．仅同步实际修改的分发文件

- Claude 分发同步该 `EXAMPLES.md`。
- Codex 使用正式脚本生成到临时目录，仅回填该文件。
- 使用干净 PATH、worktree Python；不覆盖 SKILL.md、不改变 frontmatter，不同步其他 Skill。
- evals 按现有规则留在 canonical，不进入分发。
- 分发一致性测试必须通过。

**提交：**

```text
test(acmg): align case17 receipts and remove unsupported review claims
```

## 4. C 批：重新验收、补归档并更正记录

### 自动化验证

先运行 A、B 相关测试，再复用[上一轮计划](2026-10-23-review-remediation.md)的完整定向命令。

解释器和环境继续固定为：

```bash
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -B -m pytest \
  tests/unit/test_clinvar_region_scan_completeness.py \
  tests/unit/test_acmg_skill_evals.py \
  tests/unit/test_variant_interpretation_code_patterns.py \
  tests/unit/test_codex_plugin.py \
  tests/integration/test_acmg_mcp_stdio.py \
  --no-cov --maxfail=0 -p no:cacheprovider
```

上述五文件是定向检查，不替代完整回归。最终必须：

- 记录完整命令、shell 展开后的测试文件清单和实际测试数字。
- 明确上一轮是 **19 个入口参数、展开为 41 个文件**，不是 19 个文件。
- 保留原来的 1045／1 历史结果，新增本轮结果，不预测新增测试后的总数。
- 修改的 Python 文件通过 Ruff；对 `08c4a776` 和 `2128ff57` 的 `git diff --check` 干净。
- 检查冻结文件零变化，生产改动仅在区域扫描相关逻辑。

### 在线证据重新归档

旧验收目录只有摘要，不能补造当时的原始日志。为本轮新建 gitignored 证据目录：

```text
temp_docs_and_tests/benchmark_tracking/2026-10-28-review-followup/
```

保存真实命令、运行时间、HEAD、解释器、完整 stdout、stderr 和退出码。重新执行：

1. 数字 ID `2737810` 的 ClinVar 详情查询。
2. `chr7:155593770-155593780`、GRCh37 的区域查询。

核对字段、排序和成功／失败含义；**不将旧的 98 个候选、19 个重叠作为固定预期**。网络失败则保存失败回执并标"在线未完成"。

独立 LLM 案例 17／3／4 沿用此前验收要求：已有宿主可用时使用新会话、临时 Skill 副本和中性事实；没有宿主则继续标"未验收"，不安装宿主或修改全局配置。

### 更新既有记录并交付

更新既有运行文档、实施记录和本轮计划：

- 就地更正"19 个文件"的口径。
- 将上一轮"全部完成"限定为当时交付，并注明本次发现和修复的区域回归。
- 旧在线记录标明仅有摘要，缺少原始回执；本轮新记录单独标注日期与 SHA。
- 分别报告代码、自动化、在线工具和独立 LLM 验收状态。
- 最终工作区干净，提交留在原分支；不 push、不新建或删除 worktree。

**提交：**

```text
docs(acmg): record follow-up verification and correct evidence scope
```

**未纳入本轮：** upstream 再同步、计算器或 CSpec 改造、其他上游工具审查，以及机器级串行测试问题修复。多定位扫描可能更早暴露损坏数据并报 error，这是已选定的整次失败策略；独立宿主未执行时仍不能宣称整体验收完成。

---

## 5. 执行记录（2026-10-28，随 C 批提交回填）

- **A 批** `67fa683d` `fix(clinvar): complete region scans and validate zero counts`：8 类失败反例先在起点 `08c4a776` 确认失败（与探针 JSON 一致），再删提前退出、全量遍历校验、每 variation_set 至多一条（取首个有效重叠定位）、assembly+染色体归属过滤（无法识别归属报错）、count 直读并去掉 `0 <` 前缀；移除双 ID 的 later-chunk-failure 参数化，新增 201 ID 跨批失败测试与两批健康控制（如实标注为覆盖补强）。
- **B 批** `6133ff01` `test(acmg): align case17 receipts and remove unsupported review claims`：案例 17 预期统一为真实回执 `classification_status "computed" / classification "VUS" / total_score 4`（仅案例 17，未全仓替换标签）；新增真实计算器契约测试（28 条记录、PS1 Strong 唯一计分、PM5 not_met、PP5/BP6 deprecated），以实际返回构造规范短语并要求其在 eval 文本中逐字存在；EXAMPLES.md:260 改为 "Not specified in this illustrative example"，守卫禁止从提交者数重新推断双星无冲突层级（宽标记 `review status ★★ ` 因误伤合法 `★★★` 行收窄为精确短语 + 带尾随空格的双星审查行禁令）；该文件已同步两处分发，evals/ 未进分发。
- **C 批**（本提交）：五文件定向 **365 passed**（18.29s，exit 0）；完整定向回归 **1055 passed, 1 skipped**（同一 PyMuPDF 既有 skip，52.69s，exit 0），较上轮 1045/1 净增 10。**口径以实测为准：完整命令为 18 个入口参数（17 显式路径 + 1 通配），shell 展开为 40 个测试文件**——本计划草稿第 4 节"19 个入口参数、展开为 41 个文件"与实测展开不符，以证据目录 `02-full-regression.list` 的实测清单为准（08c4a776 后测试树无增删，上轮展开亦为 40）。Ruff（仅检查）通过；对 `08c4a776` 与 `2128ff57` 的 `git diff --check` 干净；冻结文件（uv.lock、pyproject.toml、计算器、CSpec、SDK 包装、registry）零变化。两项在线检查在 HEAD `6133ff01` 重跑成功（详情 2737810 健康；区域 chr7:155593770-155593780 GRCh37 健康，98 候选全扫、19 重叠、最小 span 优先——时点观察，不作固定预期），完整原始回执存于 `temp_docs_and_tests/benchmark_tracking/2026-10-28-review-followup/`（gitignored）。独立 LLM 宿主（案例 17/3/4）本环境无宿主，继续**未验收**。
