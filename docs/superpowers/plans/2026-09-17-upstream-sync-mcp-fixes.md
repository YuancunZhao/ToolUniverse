# 官方 upstream 同步与 MCP 工具缺陷修复计划

> 状态：待执行。本文件保存此前对话中的完整实施计划及后续分批执行约定。
> 保存日期：2026-09-17。保存计划不代表已经合并、修复、测试、提交或推送。
> 以下上游核查结果对应固定快照，不代表执行时的实时 main；执行时仍按固定 SHA 整合。

## 1. 已核实的起点与整合范围

官方 upstream 明确指 https://github.com/mims-harvard/ToolUniverse 。

核查时，官方 main 为 2128ff571b9ea9fcc8488486146c4cd40dc80790，相对原基线 752188d0 新增 50 个提交、166 个变更文件。最新发布及该提交中的项目版本均为 1.5.0。

- 官方差异：https://github.com/mims-harvard/ToolUniverse/compare/752188d0f4daf9005d96edca0b7c8f0dfc7f10c6...2128ff571b9ea9fcc8488486146c4cd40dc80790
- 正式发布：https://github.com/mims-harvard/ToolUniverse/releases/tag/v1.5.0

本地起点：

- 工作区：/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
- 分支：codex/acmg-svi-cspec-lightweight
- HEAD：4fb85fddb26d0350e3805119c7ad3b7ac35d5957
- 核查时工作区干净；此前仅完成只读调查，尚未合并或修改代码。
- 实施时必须重新检查真实状态；如其他 agent 已推进，从现状续接，不重置到历史起点。

纳入上游的全部更新，包括 AlphaGenome Atlas、Consensus/Exa、搜索与指南检索修复、远程 MCP 契约校验、HTTP 客户端以及 MCPB 打包修复。保留已有 ACMG/CSpec 增强。

上游没有修复此次报告的四项缺陷。实施顺序：
上游同步 → 两项 P0 → P1 → P2 → 综合验收。

## 2. 任务 A：合并官方更新，保留 ACMG 增强

### 分支与合并方式

1. 从本地固定起点新建 codex/upstream-20260917-tool-fixes，使用独立 worktree 验证，暂不影响现有宿主正在使用的目录。如该分支已存在，先核对其状态并续接，不重复创建。
2. 核对 upstream URL 后获取官方提交，合并上述固定 SHA；使用普通 merge 保留已推送历史，不 rebase、不批量挑选提交。
3. 使用 /Library/Developer/CommandLineTools/usr/bin/git；Python 使用现有可运行的 venv 解释器，不调用被 Xcode license 阻断的系统 Python。

### 冲突处理

逐文件三方预览发现 6 个文件各有一处冲突，对应 canonical 的两份文档及其 Claude/Codex 分发副本：

- skills/tooluniverse-variant-interpretation/SKILL.md
- skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md
- plugin/skills/tooluniverse-variant-interpretation/ 下的对应两文件
- plugins/tooluniverse/skills/tooluniverse-variant-interpretation/ 下的对应两文件

处理规则：

- 保留新增 Atlas/Folklore 的工具说明、参数、访问条件及适用范围。
- 保留 Atlas 预计算分数与 live 模型效应量的区别；不把 AVI_SCORE 描述为经过临床校准的致病概率。
- 保留本地“收集原始预测结果，交给统一 ACMG Skill 判断”的职责划分。
- 不恢复上游冲突段中的“预测直接对应 PS3/PP3/BP4”规则。
- 先解决 canonical 文档，再同步分发副本。Codex 使用 scripts/sync-codex-plugin-skills.sh 的临时输出目录，只回填目标 Skill，保留 frontmatter 归一化。
- 不对整个文件采用 ours/theirs，不顺带重写其他 Skill。

### 基线与依赖

- pyproject.toml、uv.lock 等采用新官方提交的版本；原先“锁文件必须等于 752188d0”更新为新基线，历史记录不改写。
- 接收上游已审核的 MCP 契约锁文件，不通过抓取实时远程 schema 更新哈希来消除测试失败。
- 隔离环境按冻结锁安装必要测试依赖，不使用 --all-extras，不重建正在使用的 .venv。
- ACMG 计算器、CSpec 实现、28 项证据约定、暂停条件和三态报告规则保持原有行为。

提交 A：官方 merge，包含上述冲突解决。

## 3. 任务 B—E：逐项修复工具缺陷

### B．P0：SpliceAI 数值解析与错误披露

已确认：src/tooluniverse/spliceai_tool.py 原起点第 157 行附近跳过字符串 DS 分数。真实响应最大值为 "0.997"，现有工具却输出 0.0。

修改共享 _predict_splice 路径，让 _get_max_delta 复用修复结果：

- 四个标准 DS_* 转为有限数值，拒绝布尔值、非法字符串及超出 [0,1] 的值。
- 空 scores、结构损坏、必要 DS 缺失或非法时明确返回错误，不把部分分数当作完整最大值，更不默认零分。
- 最大值只计算 DS_AG/DS_AL/DS_DG/DS_DL，不混入 *_REF/*_ALT。
- DP_* 转换为整数；非整数不截断，记录字段路径和警告。DP 异常不否定已完整获得的 DS。
- 保留未修改的 raw_response；两工具一致透传错误和警告。

回归：

- 真实字符串响应 → 0.997。
- 数字输入、多转录本、合法全零。
- 空值、布尔值、NaN/Infinity、越界、缺项。
- DP 转换；原始响应不变。

兼容性：合法结果保留现有字段及预测解释标签；异常数据由“成功零分”改为明确失败。预测解释不等于 ACMG 分类。

提交 B：解析修复、必要 Schema 描述与回归测试。

### C．P0：ClinVar 字符串化数组与 MCP 边界

当前证据需要区分：

- 真正的 JSON 数组经直连部署 MCP 入口能够正常查询。
- 字符串化数组进入 src/tooluniverse/clinvar_tool.py 原起点第 534 行后被作为单个名称；第 566 行删除双引号，随后组成所见的 "[A, B]"[Variant name] 查询。
- 这是已确认的畸形查询形成位置，不是宿主发生数组 → 字符串转换的证明。行号均对应原起点，实施时重新定位。

最小修复：

- 在 ClinVar 名称查询入口，用标准库 json.loads 解析完整外层方括号包裹的 JSON 数组字符串。
- 真数组保持数组；普通名称和合法 HGVS 内部方括号保持原义。
- 仅接受字符串元素，沿用去空白行为；最终无有效名称、嵌套数组、非字符串项、畸形数组字符串均明确报错。
- 不按逗号猜拆 [A, B]，不修改全局 SDK 的字符串/数组联合类型语义。
- search_params 补充收到的类型及实际使用的名称；发生兼容性解析时给出警告。
- 修复 src/tooluniverse/smcp.py 的 _strict_field_constraints 对列表类型进行集合成员判断时的 TypeError，只作局部修改。
- 更新缺少 variant_name 的 SDK 包装；使用现有生成流程，仅保留受影响文件差异。

回归：

- 真数组、单字符串、JSON 数组字符串产生等价查询。
- HGVS 方括号、空数组、混合类型及畸形字符串。
- 通过真实 tooluniverse-smcp-stdio 的 tools/call 验证，分别记录默认 hooks 和禁用 hooks 的结果。

ZCode 定界使用临时启动配置捕获原始 stdin 帧，不修改全局配置。若没有捕获到真实宿主帧，报告继续标注宿主归因未确定，不阻塞服务器侧已证实缺陷的修复。

提交 C：ClinVar 参数处理、局部 schema 修复及接口回归。

### D．P1：variant_id 与 eSearch 假空结果

已确认：rs2151556776[uid] 返回零条且 translation 为空；以自由词查询 rsID 则命中 2737810。

- 复用现有 ID 归一化逻辑，接受正整数 ClinVar ID 和无版本后缀的 VCV accession，转换为数字 UID 查询。
- variant_id 中的 rsID 明确报错，并提示使用 query="rs2151556776"；不暗中改写用户参数。
- 空白、零、布尔值和非法 ID 在请求前拒绝。
- 校验 eSearch 必要响应结构、count、idlist 和 translation；请求失败或结构异常不得降为成功空结果。
- 区分致命错误与可保留的查询警告：真实 OR 查询出现 phrasesnotfound 时仍可能有有效命中，不能一律判失败。
- 同时检查基因别名等现有重试路径，失败诊断不得伪装为“查询成功但数量为零”。

回归覆盖合法 ID/VCV、rsID 误填、合法零结果、空或损坏响应、请求失败、带警告的有效 OR 结果及重试失败。更新依赖 data={} 假成功的旧测试夹具。

提交 D：ID 校验和搜索响应校验。

### E．P2：暴露提交者引文

已从真实 VCV XML 确认：

- ClinicalAssertion/Classification/Citation 含 PMID 31573083。
- ClinicalAssertion/AttributeSet/Citation 含 PMID 28492532，应保留其方法学引用来源。

实现：

- 扩展 src/tooluniverse/clinvar_submitted_tool.py 的现有 VCV 解析器，在 submissions[].citations 输出 pmid、title、source_path。
- ClinVar_get_variant_details 复用该解析结果，提供携带 SCV 和提交者归属的 citations。
- 同一提交及来源路径内去重，不抹掉跨提交者的引用关系。
- XML 没有标题时，复用现有 PubMed 批量摘要接口补齐，不新增网页抓取器或依赖。
- 标题获取失败时保留 PMID、标题为 null，并给出警告；引文获取失败不丢弃已经成功取得的变异详情。
- 增加 citations_complete：完整获取及补全为 true；获取、解析或标题补全失败为 false。成功确认无引文可返回空数组及 true。

回归覆盖两种引用位置、多 SCV、重复 PMID、无引用、标题补全失败及 XML 请求失败。

兼容性：现有字段不移除；增加引文查询的网络开销，使用现有超时机制和单次批量标题请求。

提交 E：引文输出、Schema 与测试。

## 4. 验收与复现要求

可在目标 worktree 使用以下命令复跑真实数据；保留实际输出，不预填测试结果：

~~~bash
env -u PYTHONPATH .venv/bin/tu run SpliceAI_get_max_delta \
  '{"variant":"chr17-31337608-C-G","genome":"38"}'

env -u PYTHONPATH .venv/bin/tu run ClinVar_search_variants \
  '{"gene":"NF1","variant_name":["NM_001042492.3:c.6642+26C>G","c.6642+26C>G"],"max_results":10}'

env -u PYTHONPATH .venv/bin/tu run ClinVar_search_variants \
  '{"gene":"NF1","variant_name":"[\"NM_001042492.3:c.6642+26C>G\", \"c.6642+26C>G\"]","max_results":10}'

env -u PYTHONPATH .venv/bin/tu run ClinVar_search_variants \
  '{"variant_id":"rs2151556776","max_results":10}'

env -u PYTHONPATH .venv/bin/tu run ClinVar_get_submitted_records \
  '{"variant_id":"VCV002737810"}'
~~~

这些 CLI 检查不能替代 MCP 传输验证。最终验收包括：

1. 缺陷回归：先确认失败反例，再修复；SDK、CLI、真实 stdio MCP 的关键结果一致。
2. 原有增强：恢复 docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md 中的 23 文件回归范围（第 3 节命令加 tests/unit/test_acmg_skill_evals.py），验证 CSpec 候选、材料完整性、重复事实、特殊组合暂停及 Skill 副本一致性。
3. 上游更新：运行此次变更涉及的 28 个测试文件中的离线测试；需要服务或密钥的在线测试另列结果，不把跳过计作通过。
4. 插件对照：以新官方 SHA 的干净快照重新建立对照，不继续把历史“六项失败”当作固定豁免。
5. 真实宿主：用临时配置重跑已有六案例，并增加 NF1 工具检索验证。案例 6 仍报告为主动绕行边界观察；不将本轮工具修复直接当作 NF1 临床分类结论。
6. 差异审计：确认上游固定提交已成为祖先；非 ACMG、非本轮明确修复的文件没有意外偏离上游；检查两个范围的 git diff --check，按实际输出记录通过、失败和跳过数量。

## 5. 交付与默认边界

- 按 A → B → C → D → E 独立提交，最后更新现有运行文档和实施记录，不再建立平行记录体系。
- 全部验收通过后，确认原工作区仍干净且未被其他 agent 推进，再将结果快进合入 codex/acmg-svi-cspec-lightweight；保留集成分支供追溯。
- 默认交付本地合并和提交，不自动 push、发布软件包或修改用户全局 MCP 配置。
- 不增加第二套分类器、宿主强制状态机、通用参数修复框架或全仓清理任务。
- 最终报告分别说明：上游同步完成情况、四项修复结果、宿主归因证据、真实 LLM 验收范围及尚未完成的检查。
- 本计划文件只是交接材料。如它在原工作区尚未跟踪，实施者先保存到集成分支随交付提交；不得因该已知计划文件误判原工作区存在未知改动，也不得借此忽略其他改动。

## 6. ZCode 分批执行约定

为减少 model_output_limit_exceeded，每轮只执行一个批次；先检查实际状态，不能因上一轮输出失败就假定文件没有修改。

| 批次 | 本轮范围 |
| --- | --- |
| A1 | 核对当前状态、准备隔离分支、获取并核实固定上游提交 |
| A2 | 合并上游、解决两份 canonical 文档及副本冲突、针对性验证 |
| B | SpliceAI 修复及回归 |
| C1 | ClinVar 数组处理、局部 schema 修复、包装与单元测试 |
| C2 | 真实 stdio MCP 验证；有条件时完成 ZCode stdin 定界 |
| D | variant_id 与 eSearch 错误处理 |
| E | 提交者引文输出及回归 |
| F | 综合验收、记录、按原计划快进整合 |

执行规则：

1. 先检查 worktree、分支、HEAD、git status、未提交 diff 及正在进行的 merge；从实际状态继续，不重置、不丢弃已有改动。
2. 理解完整计划及约束，本轮只完成指定批次，不扩展范围。
3. 直接操作文件和运行工具，不重新输出计划、完整代码、整份 diff 或完整日志。
4. 使用小补丁分步修改；生成文件使用仓库已有脚本，避免一次巨大工具调用。
5. 测试日志保存到临时文件，回复只列实际结果和必要的失败摘要。简化输出不能省略验证、输入校验或错误处理。
6. 使用一个 PROGRESS.md 作为简短续接记录（不替代实施记录），控制在 30 行内：工作区、分支、HEAD、已完成批次、未提交改动、测试结果、下一步。
7. 验证通过后按上述 A—E 提交边界提交；C1/C2 属同一逻辑任务，可先保留测试通过的阶段提交，完整验收必须覆盖两者。不提交已知失败状态，不 push，不改全局 MCP 配置。
8. 本轮完成即停止，最终回复不超过 300 字，仅报告完成内容、测试、commit、下一批次或阻塞原因。
9. 如中断，下一轮先核对 PROGRESS.md 与真实 git 状态，再继续。不可仅凭简短记录宣称测试通过。

## 修订（2026-09-18）：ClinVar 补修、验收修正与临时分支清理

本节修订原计划"验收通过后保留集成分支"的条款：集成分支
`codex/upstream-20260917-tool-fixes` 在本轮全部补修与验收完成后删除，
开发入口固定为 `ToolUniverse-acmg-svi-cspec-lightweight` 工作区中的
`codex/acmg-svi-cspec-lightweight` 分支（合并历史不丢失）。

三项补修（分别提交于保留分支）：

- R1 `0ab6f451` fix(clinvar): validate esearch responses across retry
  paths —— 所有 eSearch 请求经同一 `_validate_esearch_payload` 入口；
  count 仅非负整数（拒绝布尔/负数/小数/"--1"）；idlist 必须为 UID 字符串
  列表（retmax=0 允许 count>0 配空 idlist）；querytranslation 必须非空白；
  顶层/esearchresult 内 API error 不再变成成功；errorlist 与 warninglist
  同时读取，真实位置的 phrasesnotfound 保留为警告。三条实际替代重试
  （去连字符、别名解析、疾病自由词）请求或结构校验失败返回明确错误；
  仅解释零的辅助查询（基因别名、count-only 归因）失败保留原结果加警告。
- R2 `815d8979` fix(clinvar): preserve records when citation enrichment
  fails —— esummary 顶层/result/文章对象类型先检后用；[]/null/标量不再
  抛 AttributeError；标题仅非空白字符串，缺失/空白/类型错误保留 null 并
  披露 PMID；citations_complete 不再被空 PMID 列表捷径覆盖解析警告。
- R3 `01c5d9c4` feat(clinvar): include submitter citations in variant
  details —— 详情工具复用 submitted-records 获取+解析路径一次，展平
  citations[]（pmid/title/source_path/scv_accession/submitter，同 PMID
  多 SCV 保留各自归属）；esummary 失败沿用原错误；引文获取失败保留详情
  + 空 citations + false + 警告。两个工具的 schema/描述已同步（生成器
  复核：包装文件不含 schema/描述，无需重生成）。

验收（日志：temp_docs_and_tests/benchmark_tracking/
2026-09-18-r1-r3-acceptance/，gitignored）：

- 修复回归：五文件 108 + fixture/新反例 172 outcomes 全过。
- ACMG 23 文件：682 passed、8 skipped，共 690 项执行结果（干净
  PATH；默认 PATH 下 codex_plugin 3 项为机器级 /usr/local/bin 损坏
  二进制所致。2026-09-20 更正：原文误记 "717 outcomes、0 failed"，
  依归档 acmg23b.log 点数实际为 682+8，本计划同步修正，日志原文
  保留）。
- 插件对照：官方 2128ff57 干净快照 vs 最终分支，同解释器同命令——
  快照 7 failed vs 分支 6 failed，差集仅快照侧 test_build_codex_plugin
  （Xcode license 机器级 exit 69）；其余 6 项两侧一致。
- xdist 全量：18 项失败与 2026-09-17 基线清单一致（损坏二进制/scipy
  收集/borzoi 抖动），零新增。未重跑会段错误的串行全量。
- 真实工具链路（非离线）：details 2737810 citations=2 complete=True；
  RPE65 自由词重试 total=1；GBA 别名重试 total=791；SpliceAI max=0.827；
  stdio MCP tools/call citations=2。
- 六案例真实 LLM 复跑：未执行，标为未验收（2026-09-15 记录不替代新
  HEAD 验证）。

清理：临时 worktree /tmp/up-wt 与快照 /tmp/upstream-2128ff57 已删；
集成 worktree 与临时分支删除命令及前置检查见运行文档。

## 2026-09-19/20 修订：A/B 补修、计数更正与在线回执

继 2026-09-18 修订之后，在保留分支 `codex/acmg-svi-cspec-lightweight`
（起点 `1b42f4be`）上又落两个补修提交与一份文档更正：

- `cb349d8f` fix(clinvar): validate gene alias lookup responses——
  Gene eSearch 响应复用统一校验器 `_validate_esearch_payload`
  （API error/空 translation/非法 count/非 UID → 别名告警而非静默
  放行）；Gene esummary 单独检查结果结构和非空白字符串名称；
  辅助失败仅告警、健康空查询仍视为"未被改名"。
- `d9468438` fix(clinvar): keep failed condition attribution
  inconclusive——condition-only 计数失败时零结果提示改为归因未知
  并建议去掉 condition 重试；不再输出 "None record(s)"，不设
  condition_only_match_count，不做识别结论。
- 统一回归：295 passed / 295 collected / exit 0（A/B 反例先失败后
  通过）；ruff 与两个基线区间的 `git diff --check` 均干净。
- 计数更正：上文 ACMG-23 数字已就地改为 682/8/690（依据与保留
  原则见该条目内注）；本轮同范围重收 690 selected /
  691 collected / 1 deselected 单独记录。
- 在线回执：`temp_docs_and_tests/benchmark_tracking/
  2026-09-19-followup-verification/`（CONTEXT.txt 含运行时间
  2026-09-20 11:35:14 CST、HEAD d9468438、解释器/入口路径；CLI
  四例 + stdio 同会话两调用，stdout/stderr/exit 分文件）。时点
  观察值：details 2737810 citations=2 complete=True；GBA total=791
  translation=GBA1[gene]；RPE65 total=1 走 [All Fields] 重试；本次
  SpliceAI 变异体 chr17-31337608-C-G max=0.997 与原始 DS 一致
  （上文 0.827 为当时另一记录，未改动）。
- 六案例真实 LLM 验收仍未执行、未验收；无串行全量重跑；无新增
  公共参数/schema/依赖。
