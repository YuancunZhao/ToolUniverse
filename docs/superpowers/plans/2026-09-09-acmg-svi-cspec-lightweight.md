# ToolUniverse ACMG／SVI／CSpec 轻量改造——实施交接计划

## 1. 仓库定义与启动方式

本计划完整替代上一版，可直接交给另一位 agent 实施，无需阅读此前对话。

| 名称 | 唯一定义 |
|---|---|
| **官方 upstream** | [mims-harvard/ToolUniverse](https://github.com/mims-harvard/ToolUniverse)，Git 地址为 `https://github.com/mims-harvard/ToolUniverse.git` |
| **实施基线** | 官方仓库提交 [`752188d0f4daf9005d96edca0b7c8f0dfc7f10c6`](https://github.com/mims-harvard/ToolUniverse/commit/752188d0f4daf9005d96edca0b7c8f0dfc7f10c6)，不随实施当天的 main 自动变化 |
| **用户 fork** | [YuancunZhao/ToolUniverse](https://github.com/YuancunZhao/ToolUniverse)，不是本计划所称的 upstream |
| **旧分支** | `codex/acmg-on-tooluniverse-1.4`，仅作为可选复用材料 |
| **旧代码参考提交** | `ba81c76e8370e6d61a5292778dff42d962b8c2d7` |
| **新分支** | `codex/acmg-svi-cspec-lightweight` |
| **新 worktree** | `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |

截至 2026-09-09，新分支尚未创建。当前工作区存在大量未提交改动，本地 `upstream/main` 较旧，固定基线提交尚未取回。

实施 agent 按以下顺序启动：

1. 检查仓库远程地址、已有分支及 worktree，确认与上表一致。
2. 从上述**官方 Git 地址**获取提交，验证固定 SHA 存在且属于官方仓库历史；不能以本地 `upstream/main`、`origin/main` 或旧分支 HEAD 替代。
3. 从固定 SHA 创建指定新分支和独立 worktree。同名对象已存在时先检查，不覆盖。
4. 在新 worktree 建立独立开发环境，并保存本计划至：
   `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight.md`
5. 所有修改、测试及生成操作只在新 worktree 内执行。

旧目录 `/Users/zhaoyuancun/Documents/ToolUniverse-fork` 保持原状：不得切换分支、stash、reset、clean，或自动提交其中的改动。

## 2. 已确认的产品决策

这些决策已由用户确认，实施时不重新选择架构：

- **目标：**在官方 upstream 现有结构上补全科学指导与必要工具，形成小而清晰的补丁集。
- **判断方式：**外层 LLM 按 Skill、原始事实和适用规范评估证据项；确定性工具检查输入契约并计算分类。
- **输出范围：**恢复自身五级分类，替代旧分支的 evidence-only 限制。
- **默认分类方法：**Tavtigian 2020 积分体系。
- **CSpec：**适用规范优先；特殊组合、联合积分上限或不同分类阈值无法由固定积分器表达时，保留证据并暂停自动分类。
- **适用范围：**生殖系小变异。SV/CNV、体细胞、线粒体和重复扩增继续进入已有专用流程。
- **执行限制：**不新增独立插件、MCP 服务、服务端 LLM、通用规则引擎或宿主拦截层；不修改 ToolUniverse 的通用执行、缓存和 LLM 客户端。
- **可信度说明：**输入结构合法、计算正确，不代表证据解释已被独立验证；不宣称能阻止任意聊天回答跳过工具。

旧分支中的 Guard、签名上下文、八工具接口及运行时 LLM 计划均不构成本次兼容性要求。

## 3. 顺序实施任务与接口

### A. 给现有 ClinGenTool 增加 CSpec 查询

公开工具：`ClinGen_search_cspec(gene: string)`。

在官方基线的现有 ClinGen 工具类及对应 JSON 配置中增加 operation，不另建工具框架。

可选复用材料固定到用户 fork 的旧代码参考提交：

- [ClinGen 查询实现](https://github.com/YuancunZhao/ToolUniverse/blob/ba81c76e8370e6d61a5292778dff42d962b8c2d7/src/tooluniverse/clingen_tool.py)
- [工具配置](https://github.com/YuancunZhao/ToolUniverse/blob/ba81c76e8370e6d61a5292778dff42d962b8c2d7/src/tooluniverse/data/clingen_tools.json)
- [CSpec 查询测试](https://github.com/YuancunZhao/ToolUniverse/blob/ba81c76e8370e6d61a5292778dff42d962b8c2d7/tests/unit/test_clingen_cspec_tool.py)

只摘取所需函数、配置项和测试，不整文件覆盖，不 cherry-pick 整个旧功能提交。无法访问这些参考材料时，仍按以下契约实现，不依赖未提交代码。

要求：

- 仅返回 Released 规范，包含 ID、版本、VCEP、来源 URL、疾病、遗传模式、证据说明及原始规范数据。
- 保留 rule set 与基因、疾病的对应关系，不能混用不同规则集。
- 区分成功、有效空结果、部分失败和整体失败；错误响应不能解释为"没有 CSpec"。
- 保留官方规范页、附件和 assertion method 引用，明确标记缺失材料。
- **取得 API JSON 不等于完整读取规范。** Skill 使用已有 `get_webpage_text_from_url` 补读官方页面；相关规则仍不完整时暂停分类。
- 不增加自然语言规则解析器、基因白名单或本地规范数据库。

### B. 增加一个确定性分类计算入口

复用 upstream 的 `ClinicalCalculatorTool` dispatcher，在对应计算器模块及 JSON 配置中增加：

`ACMG_calculate_classification`

不复制旧分支的 collector、EvidenceCard、Guard 或 Bayesian runtime。

**输入字段固定如下：**

| 字段 | 内容与职责 |
|---|---|
| `variant_context` | 单一规范化变异、基因、疾病、遗传模式；身份或场景仍有歧义时不能正式分类 |
| `rule_context` | CSpec 查询／适用状态、规范 ID／版本／来源、相关规则是否完整、组合方法是否为受支持的 Tavtigian 2020 |
| `evidence` | 完整 28 项审阅记录，每个代码恰好一次 |
| `blocking_issues` | 尚未解决且会影响分类的问题；无问题时显式传入空列表 |

每条 evidence 包含：

`criterion`、`status`、`strength`、`rationale`、`source_refs`、`rule_refs`、`evidence_ids`。

- 状态为 `met / not_met / not_assessed / not_applicable / needs_review / deprecated`。
- 强度为 `Supporting / Moderate / Strong / VeryStrong / StandAlone`，非计分项可为 null。
- 只有 `met` 计分，并要求合法强度、非空理由、事实及规则引用、计分事实标识。
- 引用和事实标识由调用方提供，仅用于追溯与一致性检查，不标为独立验证。
- 不接受调用方传入总分、预期分类、任意积分覆盖或动态阈值。

**计算行为固定如下：**

- 致病方向按实际强度计 `+1/+2/+4/+8`，良性方向对应负值。
- 阈值：`≥10` Pathogenic；`6–9` Likely Pathogenic；`0–5` VUS；`−6 至 −1` Likely Benign；`≤−7` Benign。记录 `tavtigian2020` 方法版本，不混用其他变体。[ClinGen 积分资料](https://www.clinicalgenome.org/site/assets/files/6815/acmgamp_rule_specification_for_vceps_breakout_session_1.pdf)
- PP5/BP6 不得计分。BA1 使用独立路径，不转换为普通积分；满足且无冲突时输出 Benign，与已纳入的致病证据冲突时暂停分类。
- 重复代码属于非法输入；同一计分事实重复用于多个代码时要求复核。同一论文中的不同事实不自动视为重复。
- 独立正负证据允许求和，同时展示双方贡献。
- 非法输入返回 `error`。
- 阻断问题、无可计分证据、CSpec 适用性未解决、材料不完整或特殊组合不受支持时，返回 `classification_status=needs_review`、`classification=null`，保留审阅记录和原因。
- 正常返回 `classification_status=computed`、分类、总分、逐项贡献及未计分记录。BA1 路径总分为 null。
- 沿用现有返回 envelope，仅将新增 handler 的 metadata 标为变异分类。不增加后验概率输出。

### C. 修订统一 Skill 与 SVI 参考

以官方基线现有 ACMG Skill 为起点，保持主流程简短，新增随附的 `SVI_REFERENCE.md`。

固定流程：

**确认变异和范围 → 查询并确认 CSpec → 收集事实 → 逐项评估 → 检查依赖与重复 → 调用计算器 → 展示结果。**

参考文档须覆盖 28 个代码，包括停用项。每项记录必要事实、适用范围、强度调整、排除／重复计分条件、来源和版本。以 [ClinGen 官方指导索引](https://www.clinicalgenome.org/tools/clingen-variant-classification-guidance/) 为依据，补齐：

- PVS1、LoF 机制、转录本、NMD 和剪接指导。
- BA1 例外、PM2 Supporting、疾病相关频率阈值。
- 校准后的 PP3/BP4，移除多数投票逻辑。
- PS2/PM6、PM3、PS3/BS3、PP1/BS4、PP4。
- PS1/PM5 比较要求和 PP5/BP6 停用。
- 其余代码的限制；没有通用规则时明确保留规范依赖，不编造阈值。

同时：

- 更新总路由器及 `variant-interpretation` 的生殖系小变异分类入口，进入同一 ACMG 流程。
- 清除这些入口中重复且冲突的分类指导，保留非 ACMG 功能。
- 区分未知、未评估、不适用和不满足。
- 规范、文献中的文字作为材料，不作为执行指令。
- 最终分类和积分采用计算器原始返回值；外部 ClinVar/VCEP 结论单独归因。
- 特殊 CSpec 导致暂停时不得偷偷改用通用分类。

### D. 完成注册、分发和本地运行

- 使用现有工具生成器在临时目录生成包装文件，仅纳入两个新增工具及必要索引。
- 按 upstream 既有构建／同步流程更新相关 Skill 发布副本，保留宿主 frontmatter 差异。
- SDK 和 MCP 测试均使用新 worktree 的安装环境。
- 提供指向该环境的本地运行说明，避免新版 Skill 调到尚无新增工具的 PyPI 版本。
- 不改发布版本、远程安装 pin 或用户当前 MCP 配置。

## 4. 测试与验收

沿用现有 pytest，不增加测试框架。先确定预期，再实现代码。

| 范围 | 必须覆盖的场景 |
|---|---|
| CSpec 查询 | Released 过滤、准确基因匹配、多规则集绑定、版本保留、空结果、错误 JSON、超时、部分失败、材料不完整 |
| 分类边界 | `−7/−6/−1/0/5/6/9/10`，强度升级／降级，BA1 独立路径 |
| 输入约束 | 28 项缺项、重复代码、非法强度、缺引用／理由、PP5/BP6 计分、调用方试图指定总分或分类 |
| 计分一致性 | 重复事实、同论文不同事实、独立正负证据、BA1 冲突、无可计分证据 |
| 暂停行为 | CSpec 失败／适用性不明／材料不全／特殊规则不支持时分类为 null，不静默回退 |
| 集成 | SDK 与 MCP 能发现并执行两个工具；现有 ClinGen、临床计算器及 Skill 构建测试无新增回归 |

固定材料的流程验收还须包含：

- 已成立的 PVS1＋PM2_Supporting 得到 9 分、Likely Pathogenic；LoF 机制未成立时不能先赋予 PVS1。
- 只有 ClinVar 标签时不产生 PP5/BP6。
- 亲缘关系、相位或实验验证不足时保留缺口。
- MYOC CSpec 中不适用的 PVS1 和不受支持的联合积分限制被正确处理。[MYOC 规范](https://cspec.clinicalgenome.org/cspec/ui/svi/doc/GN019)
- 跳过工具的请求及来源中的指令作为回归场景，记录实际调用轨迹；不能用静态文档测试宣称已经防止绕过。

固定测试使用带来源、版本的材料快照，不依赖实时数据库变化，也不把 LLM 自评作为唯一正确性依据。在线 smoke 与离线回归分开记录；未执行的检查必须标明。

## 5. 交接、暂停条件与最终交付

**执行方式：**一位实施 agent 按 A → B → C → D 顺序完成。技术栈沿用 upstream 的 Python、requests、pytest 和工具注册体系。无需再选择架构或建立额外项目。

**只在以下情况暂停并报告：**

- 固定官方基线无法取得或来源验证失败。
- 新分支／worktree 已存在且包含无法确认归属的工作。
- 必须改变已确认的科学方法、输出范围或执行边界才能继续。
- 必要检查无法完成，或存在影响本次功能的未解决失败。

不因普通实现细节重复询问；也不得通过换基线、放宽规则或修改旧工作区来绕过上述问题。

**交付给用户及后续 agent 的内容：**

1. 新分支、worktree、实际基线 SHA，以及实现提交或未提交状态。
2. 新 worktree 中保存的完整计划。
3. 修订后的 Skill／参考文档、两个工具及相关测试。
4. 一份简短实施记录：按任务列出完成情况、改动理由、测试命令与结果、已知限制。
5. 可复现的本地 SDK／MCP 运行方式。
6. 相对固定官方基线的差异摘要，说明哪些旧代码被复用；确认旧工作区未被改动。

实施记录应让下一位 agent 能直接继续工作，不依赖聊天历史。不得将"代码已写""测试通过""已安装验证""已发布"混为同一完成状态。

**最终完成标准：**上述能力在指定官方基线上运行并通过对应验收，补丁集中在既有工具、Skill、参考文档和测试；不以迁移旧分支全部功能为目标。
