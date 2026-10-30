# 项目进度

更新：2026-10-30（Asia/Shanghai）。当前交付以包含本文档的 main 提交为准；历史设计和本地绝对路径不作为新设备运行前提。

## 目标与决定

- 2026 年 11 月 Google 线下 Workshop，100 分钟含讲解与实验，成果展示另计，每组 5 人；原设计对时间的早期表述已由后续确认覆盖。
- 三个 Agent、五个核心 Skill，主线为美股下周研究，输出来源、反证、信心与失效条件，不执行交易。
- 使用 ADK Python 2.13.0、Gemini 3.8 Flash 和 AI Studio Key；默认不用付费 Search Grounding。每组目标 $5，当前不需要按设计扩至 $30。
- README 同时承担演讲和实验手册；HTTPS 仓库为分发入口，不再维护 ZIP 或独立 WORKSHOP.md。
- 已汇总当前项目的设计对话与 README／Web UI 对话，并以最新用户要求为准写入仓库根目录 [AGENTS.md](../AGENTS.md)。长说明在 [implementation.md](implementation.md)，讲师安排和验证事实分别见 [INSTRUCTOR.md](../INSTRUCTOR.md)、[VALIDATION.md](../VALIDATION.md)。

## 已完成

| 范围 | 当前状态 |
| --- | --- |
| ADK 研究团队 | technical → catalyst → review 原生 Workflow；结构化 Analysis／Decision 与 State 模板传递 |
| 核心方法 | data-quality、technical-trend、news-catalyst、risk-review、decision-report，真实 ADK 解析与检查 |
| 应用预检 | doctor 环境诊断；scan／inspect_skill 能力与资源检查；accepted_skills 过滤；offline-check 构造验证 |
| 数据与结果 | 完整美股日线、确定性指标、纽约交易周、RSS 标题、日缓存、引用检查与降级规则 |
| CLI／Web | 两种入口共用运行流程、预算账本、锁与留档；Web prompt 路由不调用额外模型，原生 Trace 可查看三个角色 |
| Discovery／生命周期 | EAGER／LAZY；bounded 淘汰、ephemeral 过期、显式卸载与指令替换机制实验 |
| 第三方与脚本 | 固定 Position Sizer 原件和 MIT 许可；ADK 适配版脚本／Artifact 读回；npx 安装再导入流程 |
| Registry | 五个已检查方法的本地关键词 search → load，无向量库与托管服务 |
| 执行追溯 | report、decision、evidence、trace、requests、usage；失败留档、方法哈希与共享预算 |
| 正文与图片 | 入门介绍、代码／配置／State、全部实验 CLI 与 UI prompt；官方 PNG、一组三张真实 Trace PNG，来源和许可证齐全 |
| 跨设备材料 | AGENTS.md 保存约定；本文记录状态、验证证据、待办与恢复步骤 |

## 本次修改

1. 将“核心代码与配置”前移到环境准备之后，所有实际研究和机制运行均在代码介绍之后。
2. 将 Web UI 启动移至运行章节，先统一介绍 CLI／Web 两种入口，再执行首次报告。
3. 在 README 正文展开 doctor、scan／inspect_skill、accepted_skills、offline-check 的实现、代码摘录、失败语义与复用方法，不再只链接到附录。
4. 一并交付上一轮已完成的原生 Web 入口、CLI／Web 共用运行逻辑、真实 Trace 截图及相关回归测试。
5. 更新讲师安排、实现参考与验证记录，使章节顺序和开发状态一致。

## 验证与代码检查

### 本次复核

- `.venv/bin/python -m pytest -q`：**28 passed**；覆盖 ADK 解析、指标与日历、降级与引用、原生机制实验、CLI／YAML 优先级，以及 CLI／Web 两种真实 Runner 路径。
- Web 回归验证 State 交接、新 Session 隔离、调用上限失败留档、共享账本计次与锁清理；脚本化模型测试禁止 HTTP，不消耗 Gemini token。
- `pip check`：无依赖冲突。pytest 保留已有 pandas 弃用提示与 Skill 生命周期实验提示，未隐藏警告。
- `doctor`：ADK 2.13.0，五个核心方法全部 SUPPORTED；`offline-check`：model_called=false，三角色和目标交易周构造通过。
- 扩展样例复核：needs-search／metrics-export 为 ADAPTABLE；needs-desktop 为 UNSUPPORTED，与正文解释一致。
- 七份 Markdown 的本地链接、锚点、围栏与 23 段 Python／JSON／YAML 示例检查通过；确认 Web 启动位于代码章节之后。
- 审阅本次包含的 runtime／Web／测试改动：两种入口复用最终校验与预算，原生 UI 子节点保留当前 invocation 的 Trace 关联；未发现本次交付的阻塞问题。
- `git diff --check` 通过；发布候选中未包含实际 Key、私人配置、runs、缓存或虚拟环境。推送前已 fetch 远端 main，基线与本地一致。

### 已有真实运行证据

以下均为 2026-10-30 的真实 Gemini Web UI 运行，详见 VALIDATION.md；本次文档调整不重新消耗模型额度。

| 输入 | 模式 | 模型响应／工具调用 | runtime 耗时 | 估算费用 |
| --- | --- | --- | --- | --- |
| 合成 DEMO | EAGER | 9 / 17 | 28.23 秒 | $0.016508 |
| 合成 DEMO | LAZY | 13 / 21 | 39.46 秒 | $0.021883 |
| 真实 GOOGL | EAGER | 9 / 20 | 43.31 秒 | $0.022519 |

EAGER／LAZY 数据哈希相同，LAZY 三个角色各调用 list_skills。五个 lab 的 UI prompt 均已操作验证。费用是代码中的付费标价估算，非实际账单；原始 runs 与真实数据只留在本机，Git 中仅保留合成输入的正式截图。

历史提交：`031cfe5` 建立仓库与合并手册；`2dc6313` 补源码及输出；`9b0d913` 补 Discovery／State／预检并修复 YAML discovery 默认行为。本次版本在此基础上继续。

## 尚未完成

### 活动前准备

- [ ] Cloud Shell 安装、API 访问、`adk web` 和 Web Preview 端到端彩排。此前用户明确暂缓，本次仍不执行；本地通过不能替代云端验证。
- [ ] 确认活动发放的 Google Cloud 额度能否用于当前 Gemini Developer API／AI Studio 计费，以及组级请求／token 配额。
- [ ] 在最终活动日期复核模型可用性、价格与依赖版本，并按最终环境完成一次主线彩排。
- [ ] 用自定义 Skill 改动做一组完整的固定证据前后对照，保留方法哈希、报告差异和关键执行证据；已有主线测试不能替代这次教学素材准备。

### 可选扩展与实现边界

- [ ] Gemini 自主选择并执行第三方适配版的模型实验；当前只有代码控制的真实脚本工具／Artifact 验证。
- [ ] 新闻全文、权威公告、未来事件日历核验；当前只有 RSS 标题，信心上限仍为 medium。
- [ ] 托管 Skill Registry、向量检索、Vertex AI／Cloud Run；当前主线无这些依赖。
- [ ] 港股／A 股与跨领域预设；当前行情和交易日历只覆盖美股流程。
- [ ] 自动模型短审查／UNKNOWN 路径、Skill 自动重验证与更完整兼容性规则；当前以静态规则为主。
- [ ] 生产化会话／Trace 持久化、脚本隔离、平台硬额度及跨目录预算；当前只承诺本地教学范围。

当前没有将这些可选项列为已实现能力，也不将它们作为本次 README 调整的阻塞项。

## 新设备继续开发

```bash
git clone https://github.com/ohmystack/adk-stock-research.git
cd adk-stock-research
git status --short --branch
bash scripts/setup.sh
.venv/bin/python scripts/configure.py
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli offline-check
.venv/bin/python -m pytest -q
```

先读 AGENTS.md、本文和 README。Key 通过本机隐藏输入配置，虚拟环境重建；不复制 `.env`、`.venv`、`.adk` 或真实数据缓存。需要 UI 时执行 README 运行章节中的启动命令，选择 research 并新建 Session。

已有克隆先保存本地修改，再 `git pull --ff-only origin main`；通过 `git rev-parse HEAD` 与 `git ls-remote origin refs/heads/main` 核对版本。代理按设备网络另配，不将作者本机地址当作课程依赖。
