# ToolUniverse 剩余问题增量修复计划

## 1. 起点与交付约束

**目标：** 修复复查发现的剩余问题，不重做架构，不重新实施已关闭的 F01、F04、F05、F07、F08、F09、F10。

- 工作目录：`/Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight`
- 分支：`codex/acmg-svi-cspec-lightweight`
- 起点：`5df7d9a53bea6a6519ca72bc99edf31ec53eb5be`，本次核对工作区干净。
- 官方 upstream：[mims-harvard/ToolUniverse](https://github.com/mims-harvard/ToolUniverse)，已合入基线 `2128ff57`。
- 保留现有公开参数、返回字段和计算器行为；不改依赖、锁文件、工具 JSON、SDK 包装或全局配置。
- 本轮仅同步仓库分发副本，不再覆盖已安装 Skill。
- 按 A→B→C→D→E 执行，每批独立提交；不 push。

每批先运行失败反例，再修复、回归并提交；兼容用例若原本通过，应如实记录。

## 2. 分批修复

### A．修正 PVS1 文案与科学场景附件

修改 `skills/tooluniverse-acmg-variant-classification/SVI_REFERENCE.md` 及 evals。

**PVS1 文案：**

- 删除"只有确认剪接和蛋白功能保留，才能按救援机制排除 PVS1"的统一门槛。
- 保留"框内不等于功能恢复"的必要提醒。
- 明确：有来源支持的自然救援转录本、预测保持功能的剪接位点，可以按适用 SVI／基因规则进入 N/A 路径；不普遍要求变异特异的 RNA 或蛋白实验。
- 多种合理结果未解决时，采用最低适用结果；满足条件的 N/A 也在其中。不能因为存在未经支持的救援猜想就直接 N/A。
- 通用树中，小于等于 10%、非关键区域的框内损失写为 **Moderate**；Supporting 必须另有适用规则依据。Walker 2023（PMC10357475）、Abou Tayoun 2018（PMC6185798）。

**修正案例 14／15：**

为避免与其他独立场景混淆，两案使用合成转录本 `NM_999997.1`，明确第 334 位参考密码子为 `GGA`：

| 场景 | 待评变异 | 致病参考变异 |
|---|---|---|
| 14，PS1 边界 | `c.1000G>A → p.Gly334Arg` | `c.1000G>C → p.Gly334Arg` |
| 15，PM5 边界 | `c.1001G>T → p.Gly334Val` | 同上 |

保留"参考变异通过剪接致病、待评变异无对应剪接影响"的事实。只更新两案相关附件、提示词和断言，不批量替换案例 13 或历史回执。

**补充案例 16：**

- 使用独立合成转录本 `NM_999996.1:c.1200+2T>C`。
- 给出符合适用 SVI 条件、预测保持功能的 GC donor 事实和依据；没有变异特异 RNA／蛋白实验。
- 验证宿主不会额外要求实验确认才能记录 PVS1 N/A。
- 无其他计分证据时，计算器应返回 `needs_review / no_scoring_evidence / classification=null`，不补造总分。

**测试：**

- 文档守卫抓到原确认门槛和无依据的 Supporting 表述。
- 案例 ID 保留 1–15，追加 16；附件存在。
- 对案例 14／15 加固定密码子一致性检查，使用 `GGA/AGA/CGA/GTA` 四个标准密码子即可，不引入 HGVS 解析依赖。
- 中性事实附件不包含预期赋码、分类或总分。

同步 canonical、Claude、Codex；Codex 经正式同步脚本生成到临时目录，只回填目标 Skill。提交建议：`docs(acmg): correct rescue guidance and coherent eval fixtures`。

### B．补齐 ClinVar 逐记录解析失败处理

修改 `src/tooluniverse/clinvar_tool.py`，继续使用已有完整性字段。

**共享解析器：**

- 空对象不能作为有效详情。
- `genes` 缺省仍允许；提供时必须为列表，元素必须为对象。
- `germline_classification` 缺省仍允许；提供时必须为对象。
- 不要求每条记录必须已有临床分类，不新增生物学适用条件。
- 损坏结构统一抛出带字段说明的 `ValueError`。

**两个调用方同时处理：**

- 搜索工具逐记录捕获解析失败：保留计数、IDs 和其他有效详情，将失败 UID 加入 `missing_variant_ids`，告警放入 `warnings`，完整性为 false。
- `ClinVar_get_variant_details` 在组装详情及获取引文前处理共享解析错误，返回明确 error，避免裸异常或空详情成功。
- 不使用笼统 `except Exception` 掩盖其他程序错误。

**修正健康夹具：**

当前 `_variant_record` 使用了解析器不读取的字段。改用真实结构：

```python
{
    "uid": uid,
    "title": name,
    "genes": [{"symbol": "NF1"}],
    "germline_classification": {
        "description": "Pathogenic",
        "review_status": "criteria provided, single submitter",
    },
}
```

测试必须断言标题、基因和临床分类内容，不能只检查 ID 和完整性。

**必须覆盖：**

- `{}`、`genes=None`、`genes={}`、非法列表元素、`germline_classification=None`。
- 一条健康记录加一条损坏记录，健康内容完整保留。
- 缺省可选字段、健康空查询、分页查询保持兼容。
- 单详情入口明确报错，且不继续请求引文。
- 保留旧 SDK 位置参数及候选 OR 回归。
- 将误称"默认 MCP 注册路径"的直接实例化测试准确命名；另用真实 SMCP 注册后调用验证部分结果契约，HTTP 全部 mock。

提交建议：`fix(clinvar): isolate malformed summary records`。

### C．区分 CSpec 元数据缺省与损坏

修改 `src/tooluniverse/clingen_tool.py`。

对详情的 `@id`、`version`、`cspecStatus`，先检查类型，再进行现有比较：

- 缺键、null、空白字符串视为可选信息缺省，保留兼容。
- 非字符串且非 null 的值视为损坏。
- 非空 `@id` 无法归一化，例如 `///`，视为损坏。
- 有效字符串继续按现有 ID、版本、状态比较逻辑处理。
- 错误写入现有 `detail_structure_failed`、`missing_materials`、`partial_failures`，包含字段及实际值。
- 保留候选、原始详情和有效规则；不自动换版本、不新增状态。

**测试矩阵：**

- `@id=123/{}/[]/"///"`。
- `cspecStatus=123/{}/[]`。
- 非字符串 version，不得通过字符串化或标题回退隐藏损坏。
- 缺省／null／空白兼容。
- 普通 ID、版本、Retired 矛盾仍在三通道披露。
- 一个规范损坏不影响另一个正常规范。

提交建议：`fix(clingen): disclose malformed specification metadata`。

### D．修正收集示例及测试盲区

修改 `skills/tooluniverse-variant-interpretation/CODE_PATTERNS.md`、`skills/tooluniverse-variant-interpretation/TOOLS_REFERENCE.md` 和现有文档测试。

**CELLxGENE：**

- 删除错误的 operation／organism，使用工具默认值。
- 过滤器改为字符串，例如：`var_value_filter=f"feature_name == '{gene_symbol}'"`

**同类 ChIPAtlas 错误：**

两份文档中的 `operation="gene_list"` 也不符合枚举；删除该参数，使用默认 `enrichment_analysis`。

**结构示例按已确认选择简化：**

- CODE_PATTERNS 结构段仅查询 SIFTS 并保留完整原始回执。
- 删除仅为自动预测服务的序列读取、`if not pdb_hits` 和 NvidiaNIM 兜底。
- 不把请求失败解释为"无实验结构"，不添加自动分析实现。
- 工具能力保持原样；已有合法的 AlphaFold DB 资料收集示例可以保留。

**测试升级：**

- 现有 AST 检查继续验证工具名、关键词、必需参数。
- 对可静态求值的参数，追加 type／enum 校验。
- 当前反例应至少抓到两份文档的 7 个字面量错误；动态过滤器通过执行示例、在 stub 中按真实 Schema 校验。
- SIFTS 示例使用"有结构、健康空、请求错误"三种真实返回形状测试，确认原始状态和内容保留，且不自动调用预测。
- 不新增通用文档测试框架。

同步两个目标 Skill 的仓库分发。提交建议：`docs(variants): validate example values and simplify structure collection`。

## 3. 回归与独立宿主验收

解释器固定为 worktree 内 `.venv/bin/python`，清除 PYTHONPATH、使用干净 PATH，运行：

```bash
env -u PYTHONPATH PATH=/usr/bin:/bin:/usr/sbin:/sbin \
  PYTHONDONTWRITEBYTECODE=1 \
  /Users/zhaoyuancun/Documents/ToolUniverse-acmg-svi-cspec-lightweight/.venv/bin/python \
  -B -m pytest --no-cov --maxfail=0 -p no:cacheprovider <测试文件>
```

每批运行相关测试；最终重跑上一轮完整定向集合，包括：

- ACMG 计算器、CSpec、Skill 文档、evals、Codex 插件及 ACMG stdio。
- 全部 `test_clinvar_*.py`、compound variant、SpliceAI。
- 参数校验、SDK 导入、包装依赖、SMCP Schema、生成器类型测试。

**949 passed / 1 skipped 是起点记录，不是预测结果。** 保存本轮实际命令、退出码、计数和跳过原因。

同时要求：

- 修改文件 ruff 通过。
- 对 `5df7d9a5` 和 `2128ff57` 的 `git diff --check` 干净。
- 依赖、锁文件、工具 JSON、SDK 包装及 metadata 相对起点零变化。
- 分发一致性及 Codex frontmatter 检查通过。

独立宿主运行案例 11–16，再回归 3/4。使用修订后的临时 Skill 副本、独立会话和对应事实；不提供计划、断言、预期答案。保存完整调用轨迹、最终答复、版本、模型与哈希。

额度中断保留原生续接入口；缺最终答复仍标 PARTIAL。合成案例通过不等于真实变异或完整在线收集流程验收通过。

## 4. E 批：修正记录并交付

继续更新既有运行文档（`docs/acmg_svi_cspec_local_run.md`）和实施记录（`docs/superpowers/plans/2026-09-09-acmg-svi-cspec-lightweight-IMPLEMENTATION.md`），不新建平行记录体系。

- 就地更正上一轮"未修改已安装 Skill"的错误表述，明确两处安装副本曾被更新，属于计划范围偏差。
- 更正上一轮"F01–F11 全部完成"：保留提交和实测事实，注明复查发现的未闭环项及本轮解决提交。
- 历史回执、历史测试数字和旧 PARTIAL 不覆盖。
- 分别报告代码修复、自动化验证、独立宿主验收状态。
- 每批短报告，长日志落盘；最后独立提交记录。

不包含全局安装、push 或会触发本机段错误的串行全量测试。已安装 Skill 本轮不会自动更新；真实使用仍可能加载旧文案，必须与临时验收副本明确区分。
