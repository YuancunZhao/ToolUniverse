# ACMG PM1 与相关规则护栏修正实施计划

> **For agentic workers:** 使用 executing-plans 技能，按 A → B → C 串行执行；每批完成核对后再提交。不得将本计划当作授权修改分类器或扩展架构。

**Goal:** 修正文档把基本适用条件、证据缺口、强度调整与组合限制混淆的问题，保留计算器已有正确行为，并让实际安装的 Skill 与修订版一致。

**Architecture:** 规则解释仍由统一 ACMG Skill 承担；计算器只执行既有契约、计分和暂停检查。修改 canonical 文档，通过现有分发机制生成副本，复用现有 pytest 与 evals 格式，不增加规则引擎、状态机、hooks 或依赖。

**Tech Stack:** Markdown、Python/pytest、现有 Skill evals JSON、bash/rsync、现有 worktree 的 Python 环境。

**Spec:** 本文内嵌 2026-09-24 只读审查的结论、逐项修正要求和验收标准；不要求执行 agent 读取历史聊天，不另建设计或报告体系。

## 起点、依据与全局约束

- 唯一开发入口：`/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`。
- 保留分支：`codex/acmg-svi-cspec-lightweight`；工作区目录名不是 Git 分支名。
- 审查 HEAD：`9faae64ed4655efdc039f86f7c68f08987a863b1`，审查时工作树干净。执行前必须重新核实；本计划文件属于预期新增文件。
- 官方 upstream 明确指 `https://github.com/mims-harvard/ToolUniverse`；此前合入基线为 `2128ff57`。本轮不拉取或合并上游，不新建分支/worktree，不改旧 `ToolUniverse-fork` 工作区。
- 用户先前列出的 `4fb85fdd` 是历史版本。计算器实现、计算器 JSON Schema、canonical SVI_REFERENCE.md 在该版本到审查 HEAD 间相同。不要回退工作区。
- Python 固定为目标 worktree 的 `.venv/bin/python`；使用 `env -u PYTHONPATH`，确认导入来自目标 `src`。不重装环境，不更新锁文件。
- Git 使用可用的 `/Library/Developer/CommandLineTools/usr/bin/git`；以下简写为 `git`。执行前核实普通 git 是否可用，不绕过 Xcode license 修改机器设置。
- 生产代码、公共 API、Schema、工具 JSON、生成包装、CSpec 查询逻辑、依赖、`uv.lock` 均不在修改范围。不得放松材料完整性、重复事实、特殊组合和 PP3+PM1 上限检查。
- 本轮不是 TSC2 p.Lys1701Thr 的重新分类；所有验收事实用明确标识的合成病例，不能把验收结论移植到真实变异。
- 不改用户全局 MCP 配置；可更新下文两处目标 Skill 的两个文件。其他 Skill 不动。
- 实施时可按批次 commit；默认不 push、不发包。自动化通过与真实宿主通过分别报告。
- HEAD 若已前进：先比较本计划涉及文件，保留已有修改，记录新的实施起点；若科学规则已变化或发现新的生产缺陷，报告具体差异，不强行覆盖或悄悄扩大本计划。

### 已确认的问题与事实

1. SVI_REFERENCE.md 第 55–59 行摘要的 “PM1: specification-defined regions only”，以及第 235–241 行的 “Apply only ... Without either, PM1 is not_met” 是明确错误；第 246–247 行来源说明强化了误读。
2. PM1 默认 Moderate 不要求 VCEP，也不普遍要求量化 domain depletion；“关键域/热点且无良性变异”的事实要求仍必须满足。
3. 无 CSpec 的完整 28 项合成输入、仅 PM1 met/Moderate，已实际返回 computed/VUS/2。没有发现错误的 PM1/CSpec 代码门槛。因此计算器回归新增用例应在修文档前就通过，不能声称它原来失败。
4. PP3/BP4 的“不一致即两项都不用”在 SVI_REFERENCE.md 两处、SKILL.md 一处重复，与所引用的预选单工具校准框架冲突。
5. PP2 的 z-score 必要门槛读法、BS2 的无规范即暂停读法、PS3 的流行病学绝对优先、SKILL 的模糊证据直接 not_met、未确认亲缘关系一律暂停，都需针对性澄清。
6. 两份安装 SVI_REFERENCE.md 与仓库 canonical/Claude/Codex 共五份内容相同，审查 SHA256：
   `7b9153809b48426896422925786af08471d6085a1709d9cdd966a1accf40426a`。
   两份安装 SKILL.md 与 Codex 分发相同，审查 SHA256：
   `521724ee1b5ef6f6f17588862f615efb77fe76650711f3fc86677b49fe303b93`。
   这些值用于识别实施前本地改动，不能当作修订后期望值。
7. MCP 配置指向本 worktree 的 stdio 入口，不等于能证明历史会话读取了哪份 Skill。验收须保存实际读取路径与修订后哈希；不能推断宿主优先级。

### 规则来源

- Richards 2015，Table 3/4：<https://www.genomicseducation.hee.nhs.uk/wp-content/uploads/2016/04/Standards_Guidelines_for_the_Interpretation_of_Sequence_Variants.pdf>
- Pejaver 2022，Table 4、单工具预选及 PM1+PP3 组合讨论：<https://www.ccs.neu.edu/home/radivojac/papers/pejaver_amjhumgenet_2022.pdf>
- Brnich 功能证据框架：<https://genomemedicine.biomedcentral.com/counter/pdf/10.1186/s13073-019-0690-2.pdf>
- Walker 2023 剪接推荐：<https://pmc.ncbi.nlm.nih.gov/articles/PMC10357475/>
- PS2/PM6 使用现有参考文档所引用的 ClinGen SVI de novo v1.1；本轮不改其中已列明的 assumed-parentage 点表。

## A. 修正规则正文、补最小回归并同步仓库副本

**文件职责：**
- 修改 `skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md`：准则条件和来源。
- 修改同目录 `SKILL.md`：工作流状态语义与简短规则摘要。
- 修改 `tests/unit/test_acmg_calculate_classification.py`：用现有 helper 固定无 CSpec 的 PM1 正向契约。
- 修改 `tests/unit/test_variant_interpretation_code_patterns.py`：复用已有文档护栏及副本一致性检查。
- 同步 `plugin/skills/tooluniverse-acmg-variant-classification/` 和 `plugins/tooluniverse/skills/tooluniverse-acmg-variant-classification/` 的上述两个 Markdown 文件。

**接口：** 输入/输出结构和算法完全不变。改动只影响宿主解释规则时的文字依据。

- [x] 先在现有文档测试文件补一个小型检查，规范化空白及 Markdown 加粗后检查下列已确认错误原句。先跑一次，应在原文上失败；保存完整失败项，不只是第一个命中。
  - SVI_REFERENCE：`PM1: specification-defined regions only`
  - SVI_REFERENCE：`Without either, PM1 is not_met`（规范化时同时移除反引号）
  - SVI_REFERENCE 和 SKILL：`discordant calibrated predictors → neither`
  - SVI_REFERENCE：`gnomAD missense z-score > 3.09 is the common convention`
  - SVI_REFERENCE：`specifications define "healthy" thresholds (age, exam) — otherwise record needs_review`
  - SVI_REFERENCE：`epidemiological contradictions take precedence`
  - SKILL：`Ambiguous evidence → not_met or needs_review`
  - SKILL：`and under-validated assays leave the criterion at needs_review`

检查代码沿用现有简单字符串检查方式，不建立 Markdown parser：

```python
def test_acmg_reference_has_no_known_overrestrictive_shortcuts():
    root = SKILL_DIR.parent / "tooluniverse-acmg-variant-classification"
    forbidden = {
        "SVI_REFERENCE.md": (
            "PM1: specification-defined regions only",
            "Without either, PM1 is not_met",
            "discordant calibrated predictors → neither",
            "gnomAD missense z-score > 3.09 is the common convention",
            'specifications define "healthy" thresholds (age, exam) — otherwise record needs_review',
            "epidemiological contradictions take precedence",
        ),
        "SKILL.md": (
            "discordant calibrated predictors → neither",
            "Ambiguous evidence → not_met or needs_review",
            "and under-validated assays leave the criterion at needs_review",
        ),
    }
    failures = []
    for name, markers in forbidden.items():
        text = (root / name).read_text().replace("**", "").replace("`", "")
        normalized = " ".join(text.split()).casefold()
        for marker in markers:
            if marker.casefold() in normalized:
                failures.append(f"{name}: {marker}")
    assert not failures, "\n".join(failures)
```

这只能防止已知错误原句复现，不能证明科学语义正确或 LLM 会遵守。必须同时人工逐项核对下表，不能只改写同义句来使测试通过。

- [x] 用下列英文整体替换 PM1 条目；保留相邻 PM2 等条目，不做无关润色：

```markdown
### PM1 — mutational hotspot / critical functional domain (Moderate by default)

- **Basic applicability:** Under ACMG/AMP 2015, PM1 applies when the
  variant lies in a mutational hotspot and/or a critical, well-established
  functional domain without benign variation. The default strength is
  **Moderate**.
- **No specification prerequisite:** An applicable VCEP/CSpec is not
  required for the generic rule. A formal quantitative domain-depletion
  analysis is not a universal prerequisite for default Moderate strength.
- **Evidence:** Document the region, its boundaries, the variant's
  location, its established hotspot or critical-domain relevance, and
  the evidence supporting absence of benign variation. A domain
  annotation alone is insufficient. Missing data are not evidence of
  absence.
- **Applicable specifications:** Follow an applicable Released CSpec
  under the precedence rules in SKILL.md; do not infer inapplicability
  merely because no specification exists.
- **Strength adjustment:** Treat a non-default strength as a separate
  decision requiring a documented applicable rule or justified
  calibration. Cite that basis in rule_refs and explain it in rationale.
  Quantitative depletion alone does not automatically authorize a
  strength change. There is no PM1-specific ClinGen SVI recommendation
  defining a universal strength-adjustment ladder.
- **Status:** Lack of a CSpec or quantitative depletion estimate alone
  must not cause not_met. Follow SKILL.md to distinguish satisfied,
  evaluated-but-unsatisfied, unevaluated, and unresolved conditions.
- **Combination limit:** PP3 + PM1 must not exceed Strong in total
  (4 points in this workflow), following Pejaver et al. 2022.
- **Double counting:** Do not reuse the same fact for PM1 and another
  criterion, including PP2 or PS3. Distinct facts are not duplicates
  merely because they concern one domain or occur in one publication.
- **Sources:** Richards et al. 2015, Table 3 (basic applicability and
  default strength); Tavtigian et al. 2020 (point framework, not PM1
  eligibility); Pejaver et al. 2022 (combination cap); applicable CSpec
  and the cited rule/calibration for any non-default strength.
```

- [x] 重写第 55–59 行总述，避免修了条目却保留错误摘要：

```markdown
- **No SVI criteria-specific recommendation exists for PS4, PM1, BP5,
  PS1, or PM5** in the guidance index cited here. Their generic
  applicability comes from ACMG/AMP 2015 and the additional published
  routes cited in their entries. An applicable specification takes
  precedence. Absence of a specification does not disable a generic
  criterion; non-default thresholds or strengths require an explicit
  supporting basis.
```

- [x] 按下表完成其余限定修正。位置以标题和原句定位，行号只是审查快照。

| 位置 | 必须落地的最终语义 |
|---|---|
| PP2，原 359–365 | 保留“错义是常见疾病机制 + 良性错义变异率低”。删除 z>3.09 作为 common convention 的句子；基因约束只能作为需解释的支持信息，不能自动满足 PP2，也不能因未达到这一数值自动否决。适用 CSpec 可给出具体条件。 |
| PP3/BP4，原 368–372、526–527；SKILL 原 171–173 | 依预选且适用的单一校准工具与区间判断；删除其他预测器不同意就清零的规则。保留禁止投票、事后择优和不适用工具。其他结果可记录；若揭示真正的适用性或数据质量问题，应说明并处理该具体问题。 |
| BS2，原 471–474 | 适用 CSpec 存在时使用其健康、年龄等要求；无 CSpec 按 ACMG 基础条件核对健康成人、相应基因型与早期完全外显预期。证据缺口而非规范缺席才是复核理由。 |
| PS3，原 198–200 | 保留同一实验事实不得重复支持 PS3/PM1；删去流行病学一律优先。分别记录冲突证据的质量、验证、疾病机制和适用性；未解决的实质冲突记录 needs_review，不按证据类别自动胜出。 |
| SKILL 原 165–166 | 已评估但不满足为 not_met；未评估为 not_assessed；存在未解决歧义为 needs_review。保守原则不允许把未知伪装成不满足。不要重复维护完整状态表，简短指向第 4 步。 |
| SKILL 原 107–109 | 区分“父母已检测变异、亲缘关系未确认但符合 assumed-parentage 路径”和“父母变异状态等必要事实缺失”。前者依 PS2/PM6 既有点表评估，后者记录具体缺口；实验验证不足依 PS3/BS3 框架决定是否有合格证据，不能一律判为需复核。 |

- [x] 保留以下正确规则：PM5 默认 Moderate 与规范升级的区分、PS3/BS3 从验证出发定强度、Walker 剪接 Supporting 处理、PM2 Supporting、PP3+PM1 ≤4、重复事实和 CSpec 候选裁决。不重写这些数值表或旧入口导航。

- [x] 在计算器现有测试文件新增下列回归。复用 `run/_sdk_run/args/build_evidence/met`，同时检查 handler 和 SDK；它们在旧实现上本来就应通过。

```python
@pytest.mark.parametrize("invoke", [run, _sdk_run], ids=["handler", "sdk"])
def test_pm1_moderate_without_cspec_uses_generic_rule(invoke):
    payload = args(
        build_evidence(
            met("PM1", "Moderate", paper="synthetic:domain-evidence",
                rule="Richards2015:PM1", fact="synthetic-domain-1"),
            per_criterion={
                "PP5": {"status": "deprecated"},
                "BP6": {"status": "deprecated"},
            },
        ),
        rule_context={
            "cspec_lookup_status": "no_released_spec",
            "specification": None,
            "applicable_rules_complete": True,
            "combination_method": "tavtigian2020",
        },
    )
    assert len(payload["evidence"]) == 28
    result = invoke(payload)
    assert result["status"] == "success"
    data = result["data"]
    assert data["classification_status"] == "computed"
    assert data["classification"] == "VUS"
    assert data["total_score"] == 2
    assert data["point_contributions"] == [
        {"criterion": "PM1", "strength": "Moderate",
         "points": 2, "direction": "pathogenic"}
    ]
    assert not data.get("review_reasons")
```

将该测试放在 `_sdk_run` 定义之后。不要为它修改生产代码。原有组合上限、材料不完整等反例原样运行。

- [x] 同步仓库目标副本，按下文“定向同步”执行。运行两个修改后的测试文件及 `test_codex_plugin.py`；确认无目标外分发变化。
- [x] 提交 A：`514fd086`（`docs(acmg): separate criterion eligibility from evidence guardrails`）。显式暂存本批文件，不使用 `git add .`。

### 定向同步（A 及后续确有文档修改时使用）

不要直接运行会重建全部 Claude skills 的 `plugin/sync-skills.sh`。本轮只有目标 Skill 的两个文件变化，Claude 逐文件同步；Codex 由官方脚本写临时目标，然后仅取回目标文件。

```bash
cd /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight
acmg_sync_tmp="$(mktemp -d /private/tmp/acmg-guardrails-sync.XXXXXX)"
CODEX_PLUGIN_SKILLS_DEST="$acmg_sync_tmp/skills" \
CODEX_PLUGIN_PYTHON="$PWD/.venv/bin/python" \
bash scripts/sync-codex-plugin-skills.sh

for acmg_file in SKILL.md SVI_REFERENCE.md; do
  cp "skills/tooluniverse-acmg-variant-classification/$acmg_file" \
     "plugin/skills/tooluniverse-acmg-variant-classification/$acmg_file"
  cp "$acmg_sync_tmp/skills/tooluniverse-acmg-variant-classification/$acmg_file" \
     "plugins/tooluniverse/skills/tooluniverse-acmg-variant-classification/$acmg_file"
done
```

核对 canonical/Claude 一致、Codex 正文一致、Codex frontmatter 无 disable-model-invocation；复用现有 `test_published_copies_match_sources` 和 `test_codex_plugin.py`。不把 evals/ 复制进任何分发目录。临时目录验收后可删除，仅删除本次 mktemp 返回的目录。

## B. 增补四个定向宿主验收定义

**文件：**
- 修改现有 `skills/tooluniverse-acmg-variant-classification/evals/evals.json`，保留 1–6 原样，追加 7–10。
- 新增 `evals/files/case7-10-rule-boundary-facts.md` 一份合成事实文件。
- 修改 `tests/unit/test_acmg_skill_evals.py`：完整 ID 断言改为 1–10；保留唯一性、附件存在与案例 3 真计算器 LP/9 检查。不新增验收框架。

**输入事实文件内容要求（只含事实，不含预期答案）：**
- 所有场景均为合成；固定 variant=`NM_999999.1:c.1000C>T`、gene=`TESTGENE`、疾病=`Synthetic fixture disease`、遗传方式=AD。
- 已完成合成规则检索，确认无适用 Released CSpec、无待裁决候选；通用规则材料完整。禁止查找这个虚构基因。
- 三个独立事实块，不跨块合并：
  - **A / fixture:A**：错义变异位于经独立实验和研究确立的关键功能域 300–360；合成评审已核实该区域无良性变异。没有 VCEP、没有量化贫乏估计、没有支持非默认强度的规则或校准。除本域事实之外未提供其他证据。
  - **B / fixture:B**：仅有数据库预测的域注释 300–360，尚未确认关键功能意义，也没有良性变异分布材料；其余同 A。这里是病例事实不足，不能伪装成规则文件未读完。
  - **C / fixture:C**：错义预测适用，REVEL 在看到本变异及其他结果前已预选，版本/校准兼容 Pejaver 2022，值 0.94；额外收集的非预选 BayesDel（无 AF 版本）值 -0.40。无域证据、无 RNA/其他独立证据、无已知输入或适用性问题。

**四个 eval 条目均使用现有字段：** id/prompt/expected_output/files/assertions；files 指向上述同一事实文件。给宿主只发送 prompt 和事实附件，不发送 expected_output/assertions。

| ID | prompt 的完整任务要求 | 评判标准，保存在 expected_output/assertions |
|---|---|---|
| 7 | “请使用 $tooluniverse-acmg-variant-classification，依据附件事实块 A 完成一次合成评估。检索结论和事实作为已核实输入，不查询虚构基因。逐项提交 28 条评审记录给真实计算器并如实汇报。未提供的其他准则记为未评估，退休准则按 Skill 处理；不修改软件或配置。” | 实际读取修订 Skill/参考；PM1 met/Moderate；不能以无 CSpec 或无量化贫乏拒绝；调用实际计算器，computed/VUS/2，最终与回执一致。 |
| 8 | 与 7 相同，但仅使用事实块 B。 | PM1 needs_review，理由具体为关键域意义/良性分布未核实；不能直接 met，也不能仅因无 CSpec 判 not_met；真实计算器 needs_review、classification=null、无补造 total_score。 |
| 9 | 与 7 相同，使用事实块 A，并加：“请评估现有资料是否足以将这项域证据提高到 Strong，按有依据的实际强度提交。” | 仍为 PM1 Moderate；说明没有额外升级依据，不能因不能升 Strong 而删除默认 Moderate；computed/VUS/2。 |
| 10 | 与 7 相同，但仅使用事实块 C。 | 按预选 REVEL 得 PP3 Strong；BP4 不计分；非预选工具不同意不自动清除 PP3，不进行投票或事后挑选；PM1 未评估；computed/VUS/4。 |

“与 7 相同”只是本表压缩表达：写入 evals.json 的每个 prompt 必须展开成完整、自包含文本，不得引用其他 case 的 prompt。以上是固定资料的真实 LLM 判断验收，不是在线临床证据收集能力验收。

- [x] 先新增案例及附件，再更新 ID 断言；验证离线结构检查能发现 ID/附件遗漏。
- [x] 不编写按关键词自动判断医学答案的评分器；逐条对照 assertions 与实际 trace 判定。
- [x] 提交 B：`65d4b394`（`test(acmg): add PM1 and calibrated-predictor host scenarios`）。

## C. 定向回归、更新实际安装副本、运行宿主并记录

### 自动化回归

- [x] 在 worktree 内执行一次以下适配本改动的完整范围；失败只定位相关原因，不启动历史上会段错误的全仓库套件：

```bash
env -u PYTHONPATH .venv/bin/python -m pytest \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_clingen_cspec_tool.py \
  tests/unit/test_variant_interpretation_code_patterns.py \
  tests/unit/test_acmg_skill_evals.py \
  tests/unit/test_codex_plugin.py \
  tests/integration/test_acmg_mcp_stdio.py \
  --no-cov --maxfail=0
```

- [x] 对三个修改后的测试文件运行 `.venv/bin/python -m ruff check`；若该模块不存在，用已安装 ruff，不安装新工具。
- [x] 运行 `git diff --check 9faae64e..HEAD` 与未提交差异检查；如果执行起点更新了，再加新起点范围。记录真实 passed/failed/skipped/deselected 和退出码，不预填数字。
- [x] 用 `git diff --name-only <实施起点>..HEAD` 核对范围；确认生产目录、依赖/锁文件零改动，目标 Skill 之外的分发零改动。本轮不重跑整个 Claude 插件历史失败对照，因为未修改构建/同步脚本或插件代码；Codex 分发校验及两个 Skill 的一致性检查必须通过。

### 安装副本更新

目标仅为下列两目录的 SKILL.md 和 SVI_REFERENCE.md：
1. `/Users/zhaoyuancun/Documents/VarsUnderReview/.agents/skills/tooluniverse-acmg-variant-classification/`
2. `/Users/zhaoyuancun/.zcode/skills/tooluniverse-acmg-variant-classification/`

- [x] 更新前记录两文件哈希并备份至本次临时目录。若与审查值不同，先逐行检查差异，保留用户修改；有冲突时只报告具体冲突，不盲目覆盖。
- [x] 安装源固定为本轮已验证的 `plugins/tooluniverse/skills/tooluniverse-acmg-variant-classification/`，而不是 canonical SKILL.md，以保持已安装 Codex 格式。
- [x] 只复制两个指定文件；逐字节核对安装副本与源文件。不要安装整个插件或改 MCP 配置。
- [ ] 两处目标安装的实际加载仍待核实。历史运行仅同会话演练；补验收已在 Codex 独立上下文实读与修订分发哈希相同的 case-local 副本，但不能据此证明目标安装目录被加载。

### 真实宿主验收与终态

- [ ] 优先在已安装、能调用目标 MCP 的 ZCode 中运行案例 7–10，每案例独立上下文、各一次；历史演练共用上下文且已读预期答案，独立验收未完成。
- [ ] Codex 补验收已运行，ZCode 未独立验收；案例 7–10 获得计算器回执后因额度中断缺最终回答，仍为 PARTIAL。补验收路径、会话 ID 与恢复步骤见 `docs/acmg_svi_cspec_local_run.md` 末节。
- [x] 同一修订版 `13d198fe` 在 Codex 独立执行案例 3（LP/9 交接）和 4（材料内嵌指令），两例 PASS，完整最终回答已保存。历史同会话演练另行保留；旧案例 1、2、5、6 未重跑。
- [ ] 保存提示、事实附件哈希、模型/宿主版本、Skill 路径/哈希、仓库提交、原始工具参数/结果、最终答案、退出状态至既有忽略目录。历史归档缺完整可见轨迹、完整响应和逐案最终回答；case9 摘要与请求说明不一致，不据摘要反推。目标目录：
  `temp_docs_and_tests/benchmark_tracking/<实际日期>-acmg-rule-guardrails/`。
  这是实际运行日期目录，不冒用计划日期，不覆盖历史失败记录。
- 条件要求（本次已触发）：案例 7–10 的额度中断、会话 ID、原始轨迹和退出状态已保存；最终回答缺失，归档项仍未全部完成。原生 resume 尚未验证，恢复时另存续接回执；无法续接则注明重开上下文。不以 pytest/stdio 代替宿主验收。
- 条件要求（历史运行缺独立判定）：定向案例失败时保留反例，仅在本计划文案范围内定位；不追加规则引擎、签名、hooks 或冗长“必须遵守”条款。未解决失败应如实作为交付限制。
- [x] 更新既有 `docs/acmg_svi_cspec_local_run.md` 和 `docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`，追加本轮实际记录。不要新建平行实施报告；不要把既往“已验证”的科学规则错误描述继续当作当前有效结论。
- [x] 提交 C：`docs(acmg): record rule-guardrail validation and installation`。提交只包含记录及本轮必要修订，不包含 gitignored 运行 trace 或用户安装目录。

## 完成标准与交接要求

完成状态按三层独立报告：
1. **仓库修正完成**：所有上述文字落盘、已知错误原句消失、正确基础条件和护栏保留、分发同步、定向自动化通过；计算器无需改动。
2. **本机安装完成**：两处目标副本与修订 Codex 分发一致，有安装前后哈希和实际宿主读取证据；缺少读取证据只能报告文件同步完成。
3. **真实宿主完成**：实际运行 7–10 和 3、4，逐例报告 pass/fail/未完成、宿主名和覆盖边界。没有轨迹不得宣布通过。即使全部通过，也只证明本轮固定场景，不宣称跨模型可靠性或真实 TSC2 临床结论。

允许把仓库修正提交后交给其他 agent 做尚缺的宿主验收，但报告必须保留缺项，不能把“可以交接测试”写成“全部临床验收完成”。

为避免再次触发宿主输出 token 上限：
- 每轮执行一批；长日志保存到上述运行目录，回复只给改动、关键结果、下一批起点。
- 在本计划复选框和既有实施记录中更新进度；恢复时读 HEAD/diff/进度，不能从头重做。
- 执行命令单独检查退出码。编辑失败后不得继续串联 commit；不提交已知失败断言。
- 最终报告限：提交列表、实测计数、案例结果、安装哈希及未验收项。默认不 push，不把生成计划本身当作实施完成。
