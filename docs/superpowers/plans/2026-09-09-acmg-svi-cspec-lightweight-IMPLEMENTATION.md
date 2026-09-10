# ACMG/CSpec 轻量改造 — 当前状态记录

> 本文件是当前状态的唯一记录；历史过程由 Git 保存（`git log` / `git show`）。
> 旧版逐轮实施记录与已完成的五份计划可在 `git show 77f9aa9c:<原路径>` 查看。

## 1. 仓库与架构

| 项 | 值 |
|---|---|
| 官方 upstream | https://github.com/mims-harvard/ToolUniverse |
| 官方固定基线 | `752188d0f4daf9005d96edca0b7c8f0dfc7f10c6` |
| 分支 / 工作区 | `codex/acmg-svi-cspec-lightweight` @ `/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight` |
| 架构 | 外层 LLM 按 ACMG Skill 评估 28 项证据；`ClinGen_search_cspec` 查询 Released CSpec（含范围待判定候选）；`ACMG_calculate_classification` 校验契约并按 Tavtigian 2020 确定性组合；特殊组合/材料不全/未决适用性一律 `needs_review`，分类为 null |

两个工具挂在 upstream 既有框架（ClinGenTool operation、ClinicalCalculatorTool
dispatch），SDK 包装在 `src/tooluniverse/tools/`，MCP 经运行时注册表自动暴露。
本地运行方式见 `docs/acmg_svi_cspec_local_run.md`。

## 2. 已落实的科学修正（来源索引）

全部数值表经原文核验（PMC/PDF 链接在 SVI_REFERENCE.md 头部）：

- PVS1 决策树（Abou Tayoun 2018 + Walker 2023 RNA 扩展）：NMD 逃逸不等于
  Strong——关键区域证据/截短比例决定档位；LoF 机制未确立不得赋任何强度。
- PM3 官方 v1.0 表（2019-05-02）：确认 in trans P/LP=1.0；相位未知 P=0.5/次、
  LP=0.25/次（两次 P 或四次 LP 才达 1.0=Moderate）；纯合 0.5（上限 1.0）；
  VUS 0.25/0（上限 0.5）；受累先证者+双变异 PM2 罕见性+反循环分类前提。
- PM4 通用定义（SVI Q&A 2021-09-23）：非重复区 in-frame del/ins 或
  stop-loss；frameshift 不自动纳入；LoF 机制不构成排除；PVS1 任意强度不与
  PM4 并用；PVS1 不适用不自动转 PM4 满足。
- PP3/BP4（Pejaver 2022 + Walker 2023）：单一预先指定校准工具；精确区间表；
  PP3+PM1 合计 ≤Strong；SpliceAI ≥0.2→PP3、≤0.1→BP4；同义变异不适用氨基
  酸预测但可经剪接路径进 PP3；canonical ±1/2 走 PVS1；RNA 结果替代预测证据。
- BP2（ACMG 2015 Table 4）：trans 分支限完全外显显性基因/疾病；cis 分支任
  意遗传方式；相位证据必需。
- BP3：须为无已知功能的重复区；注释本身不足。
- PS2/PM6 de novo（SVI v1.1）、PP1/BS4/PP4（Biesecker 2023，含 PP1+PP4 ≤+5
  上限、BS4 −4.0）、PS3/BS3（Brnich 2020 验证框架、良性封顶 Strong）、
  PM2 Supporting（v1.0）、BA1（Ghosh 2018 + 九变体例外清单）、PP5/BP6 停用
  （Biesecker & Harrison 2018）。
- 旧入口（tooluniverse-variant-interpretation）只做资料收集，不再赋码/分类
  （守卫测试防回归：两个示例函数与投票字段不得回来）。

## 3. 可复跑的验收命令与结果（2026-09-10，本轮实测）

```
env -u PYTHONPATH .venv/bin/python -m pytest \
  tests/unit/test_acmg_calculate_classification.py \
  tests/unit/test_clingen_*.py tests/unit/test_clinical_calc*.py \
  tests/integration/test_acmg_mcp_stdio.py \
  tests/unit/test_lazy_load_cache_consistency.py \
  tests/unit/test_backward_compatibility.py \
  tests/unit/test_tool_name_shortening.py tests/unit/test_run_parameters.py \
  tests/unit/test_tools_package_imports.py tests/unit/test_packaging_dependencies.py \
  tests/integration/test_smcp_schema_passthrough.py tests/unit/test_codex_plugin.py \
  tests/unit/test_variant_interpretation_code_patterns.py \
  --maxfail=0 --no-cov -p no:cacheprovider
```
（本轮最终数字见第 5 节验收结论；完整输出可按上命令复跑。）

Claude 插件对照（临时快照，双侧同环境同参数）：
`git archive <sha>` + `git show` 补入 tests → `scripts/build-plugin.sh` →
`.venv/bin/python -m pytest tests/test_claude_code_plugin.py --maxfail=0
--no-cov -p no:cacheprovider --tb=short`。

在线 smoke（另行记录，不进离线回归）：ClinGen_search_cspec MYOC → GN019
v2.1 明确匹配 + GN015 等范围待判定候选；未知基因 → 有效空结果或候选提示。

## 4. 现存限制（如实）

1. **特殊组合算法未实现**：CSpec 专属组合/联合上限（如 MYOC 的
   PP3+PM5≤5）由 `combination_method≠tavtigian2020` 表达，计算器返回
   `needs_review` 保留证据——这是设计边界，不是缺陷待修。
2. **真实 LLM 工作流未验收**：无宿主调用轨迹前不宣称 Skill 行为已验证；
   工具链演练与文档检查不替代。
3. **锁文件**：`uv.lock` 逐字节等于官方基线（按用户选择恢复）；该锁未覆盖
   当前 manifest 的部分内容（如 OCR extra）——保留的上游不一致，非锁一致性
   验证通过；`.venv` 未按恢复锁重装，uv 命令须 `--frozen`。
4. **环境**：本机 iCloud 文件管理持续把 venv 内 `.pth` 标记为 UF_HIDDEN
   （chflags 后约 3 秒回归；具体进程未经证实）；以 venv 内
   `sitecustomize.py` 补路径为持久应对，详见本地运行文档。
5. **上游插件测试既有失败**（不在本项目范围）：6 项完整清单见第 5 节。

## 5. 历史追溯

- 完整过程记录：`git log 752188d0..HEAD`；各轮实施细节：
  `git show 77f9aa9c:docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`
- 已完成计划（已从当前树删除）：acmg-svi-cspec-lightweight / -repair /
  -remaining-fixes / -final-fixes / review-fixes（同法 `git show` 查看）。
- 本轮计划：`docs/superpowers/plans/2026-09-10-acmg-svi-cspec-cleanup.md`。

---

## 6. 清理轮验收（2026-09-10，计划 2026-09-10-acmg-svi-cspec-cleanup.md）

四个提交：`f8818c9f`（三项科学修正落盘+单一维护位置）、`48d1fe55`（旧入口
清理+守卫）、`a0bf8289`（JSON 基线格式恢复 461+/0−）、第四个（本记录重写+
五份旧计划删除+运行文档压缩）。

- **三项科学修正位置与反例核对**：SVI_REFERENCE.md —— PP3 Exclusions 节
  （同义≠排除，非 canonical+SpliceAI≥0.2 可进剪接 PP3）；BP2 条目（trans 限
  完全外显显性、cis 任意遗传、相位必需，标题已改）；BP3 条目（须无已知功能
  重复区）。逐条对照计划反例人工核对，非以测试代替。
- **回归实测**：13 文件 `--maxfail=0` → **673 passed, 8 skipped,
  1 deselected, 0 failed，exit 0**（较起点 672 为新增守卫测试；跳过项为既有
  环境性）。ruff 通过；`git diff --check` 对本轮起点与官方基线均干净；
  `uv.lock` 与基线 0 差异；两个 JSON 与本轮起点解析结果相等。
- **Claude 插件完整对照**（临时快照，双侧 build exit 0，同一 venv 解释器，
  `--maxfail=0 --tb=short`，完整日志 /tmp/pb_test.log、/tmp/ph_test.log）：
  双侧均 **82 passed、6 failed、1 deselected**，失败集合逐行一致，为上游既有
  六项：test_uvx_refresh_flag、test_example_params_match_schema[research.md]、
  [researcher.md]、test_slash_commands_documented、
  test_mentions_tu_run_cli[research.md]、[researcher.md]——无新增失败，
  本项目不修复。此前"五项失败"记录系不完整对照所致，以本六项完整集合为准。
- **LLM 工作流：未验收**（无宿主轨迹；守卫测试只验证文档契约）。
