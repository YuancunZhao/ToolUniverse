# ACMG 轻量工作流修正与真实宿主验收计划

（执行版全文见交接 prompt；要点固定如下）

- 起点：codex/acmg-svi-cspec-lightweight @ 52386bd435d97acbf90366a466309256794ac9de，工作区干净。
- 上一轮验收报告：temp_docs_and_tests/benchmark_tracking/2026-09-14-acceptance/acceptance-report.md（自 /private/tmp/tu-llm-acceptance-20260914-4a8bgzkx 迁入）。上轮结论：正常暂停路径通过；防绕行失败（零调用自评"致病 12 分"）——**失败记录原样保留，不得改写为通过**。
- 任务 A：Skill 第 7 步与输出模板改为三态报告约定（computed 引用实际返回；needs_review 分类空值+全部原因+不补造 total_score；工具不可用/失败/未调用→明确本次未取得计算器结果）；用户取消流程说明；旧入口专家结论快捷说明（查询可直接引用、重新评估仍走统一流程）；删除"Rule precedence 与 SVI_REFERENCE 相同表述"过时说明；同步两个 Skill。
- 任务 B：skills/tooluniverse-acmg-variant-classification/evals/evals.json，upstream 格式（skill_name/evals/id/prompt/expected_output/files/assertions），六个固定案例（显式正常、隐式触发、合成计算成功、材料内嵌指令、计算器不可用、用户主动绕行=边界观察）；离线检查：ID 唯一、附件存在、合成输入过现有计算器得 computed/LP/9。
- 任务 C：真实宿主（Codex CLI 0.154.0，gpt-6-astra，xhigh）六案例各一次、独立上下文，先合成/不可用后在线；记录 CLI/模型/强度/提交/Skill 哈希；保存提示/参数/响应/退出状态；不用 ephemeral，额度中断优先原生续接（只能重开上下文须单独记录）；判定 pass/fail/覆盖未完成（案例 6 非阻断）；迁移上轮 /tmp 材料到 temp_docs_and_tests/benchmark_tracking/（gitignored，保留校验值）；更新运行文档与实施记录。
- 边界：不改生产 API/Schema/计算器/CSpec 逻辑；不新增宿主/服务/编排/中间件；轻量方案不承诺阻止用户主动绕行；默认不推送。
- 停止条件：验收通过后停止扩展；正常请求或材料注入仍失败时保留反例并报告缺口，不堆叠"必须遵守"提示词冒充修复。
