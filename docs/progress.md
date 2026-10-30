# 项目进度

更新：2026-10-31（Asia/Shanghai）。当前交付以包含本文档的 main 提交为准；历史设计和本地绝对路径不作为新设备运行前提。

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
| Registry | 五个已检查方法的本地关键词 search → load；补充 GCPSkillRegistry／Google Cloud Agent Registry 接入说明，未连接托管服务 |
| 执行追溯 | report、decision、evidence、trace、requests、usage；失败留档、方法哈希与共享预算 |
| 正文与图片 | 任务设计与方法分工、工具／代码／运行／Trace 请求闭环、参数归属、全部实验入口；重画架构 SVG、新增请求循环 SVG，保留三张真实 Trace PNG |
| 跨设备材料 | AGENTS.md 保存约定；本文记录状态、验证证据、待办与恢复步骤 |

## 本次修改（2026-10-31）

### 演讲主线重排

1. README 标题改为“使用 Google ADK Skills 构建股票研究多 Agent 系统”；按概念 → 任务设计与分工 → 环境 → 函数／Tool 与预检 → Agent／Workflow／Runner → 运行 → Trace → 参数机制 → Registry → 方法改造与扩展 → 成本排错重排。
2. 展开股票研究输入与输出契约：CLI argparse 直取 ticker，Web 正则解析显式参数，Python 负责取证据、算指标与目标交易周；五个 Skill 的职责、正文原文节选和调用顺序单独展示。
3. 区分应用函数、两个业务 Tool 与 ADK Skill Tool；补齐角色指令、schema、State、三角色 Agent、顺序 Workflow 与 Runner／Web 当前 invocation 的接线。
4. 将 Trace 独立成章，按加载前后 Request、Skill 工具返回、动态工具、模型 Response、Review State 注入与最终校验讲解；定位 ADK 请求处理器和 Gemini SDK 出站／返回位置，明确 requests.json 仅为摘要。
5. 新增参数归属表，区分 Skill frontmatter／metadata、SkillToolset、SkillLifecycleConfig、LlmAgent、Workflow／RunConfig、项目 YAML、环境变量与 Web 服务参数。
6. Registry 分为项目自定义 LocalRegistry 与 Google Cloud 接法，核对 ADK 2.13.0 的 GCPSkillRegistry、Agent Registry API、ADC／权限与默认 revision；仅介绍，不配置或接入云服务。
7. 重画 architecture.svg，新增 request-pipeline.svg；两图均实际渲染并检查。补充 Cloud Shell 的 --allow_origins 命令，同步 AGENTS、INSTRUCTOR 与引用来源。

### 本日此前修改

1. README 第 05 节补充 Discovery 的请求处理代码与共用工具调用辅助函数，说明准备请求、读取目录和真正调用模型的区别。
2. 第 06 节补充生命周期配置、load／unload、invocation 切换与状态观察代码，与原有激活列表、工具变化和历史正文替换说明对应。
3. 第 08 节补充 Position Sizer 的适配与脚本执行接线、Artifact 保存与读回、LocalRegistry 接口及 search → load 调用，保留五个 lab 的 CLI／Web 入口。
4. 摘录只保留功能配置、关键调用与结果解释；共用上下文与调用辅助函数集中说明，省略重复准备代码。本次未修改运行实现。
5. 按用户要求修复本机虚拟环境的 macOS 隔离标记问题，恢复 PyYAML／pydantic_core 原生扩展加载，并完成全量回归。
6. 按读者的理解与操作顺序通读并优化 README 全文：区分 Skill 文件夹、名称与描述列表、方法正文，补充 Session／State／invocation 等概念，展开预检范围、配置优先级与实验观察步骤。
7. 重写 Discovery 上下文开销和生命周期表格，说明同一会话中的执行轮次、每个 Agent 的 BOUNDED 数量限制、淘汰顺序，以及卸载对后续请求和已保存结果的不同影响。
8. 补全固定证据对照、最终报告与中间输出的区别、第三方导入与脚本执行条件、Artifact 保存及读回、预算计次和排错步骤；保留核心代码摘录与五组实验入口。

## 上次修改（2026-10-30）

1. 将“核心代码与配置”前移到环境准备之后，所有实际研究和机制运行均在代码介绍之后。
2. 将 Web UI 启动移至运行章节，先统一介绍 CLI／Web 两种入口，再执行首次报告。
3. 在 README 正文展开 doctor、scan／inspect_skill、accepted_skills、offline-check 的实现、代码摘录、失败语义与复用方法，不再只链接到附录。
4. 一并交付上一轮已完成的原生 Web 入口、CLI／Web 共用运行逻辑、真实 Trace 截图及相关回归测试。
5. 更新讲师安排、实现参考与验证记录，使章节顺序和开发状态一致。

## 验证与代码检查

### 本次复核（2026-10-31）

- 本轮重排后，README 的 65 个代码围栏闭合，26 段 Python、20 段 Bash、2 段 JSON 与 2 段 YAML 通过语法／解析检查；七份 Markdown 的本地链接、锚点与表格结构通过检查，五段 Skill 引文与源文件逐字匹配，五组 lab 均保留 CLI／UI 入口。
- 两张 SVG 通过 XML 解析与 PNG 渲染目视检查；本地 ADK 2.13.0 的参数默认值、GCPSkillRegistry 签名、Web --allow_origins 的 regex 支持已核对。doctor 五个 Skill 均 SUPPORTED；offline-check 显示 model_called=false，三角色构造通过。未重跑模型或云端服务，详细记录见 VALIDATION.md 的“演讲主线、Trace 与 Registry”。
- README 全文可读性调整后，55 个代码围栏闭合；17 段 Python 的 AST、2 段 JSON 和 2 段 YAML 的解析值与本轮调整前一致，43 处本地链接、图片路径及锚点有效，五组 lab 的 CLI／Web 入口保留，`git diff --check` 通过。本轮只改文档，没有重跑模型或研究任务；详细记录见 VALIDATION.md 的“README 全文可读性复核”。
- README 的 55 个代码围栏闭合；17 段 Python、2 段 JSON、2 段 YAML 通过语法／解析检查，42 处本地链接及锚点有效，五组 lab 的 CLI／Web 命令均保留。
- 摘录和说明已与当前 labs.py、Skill 文件及本地 ADK 实现核对；`git diff --check` 通过。
- 首轮定向测试因 macOS 拒绝加载 `pydantic_core` 扩展，在收集阶段退出；获授权在沙箱外重试仍失败。随后确认 `.venv` 携带 `sharingd` 隔离标记，相关扩展的代码签名及安装记录哈希检查通过；按用户要求备份并清除该虚拟环境的隔离属性，未改动全局安全设置。
- 修复后 PyYAML 6.0.3 的 LibYAML 扩展、Pydantic 2.14.1／pydantic_core 2.50.1 均能正常导入；`.venv/bin/python -m pytest -q`：**28 passed，5 warnings**，包含五个 lab。`spctl --status` 仍为 `assessments enabled`，没有调用 Gemini。细节见 VALIDATION.md。

### 上次复核（2026-10-30）

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
