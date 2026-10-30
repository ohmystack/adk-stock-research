# ADK Skills Workshop · 开发约定

## 项目目标与已确认范围

- 为 2026 年 11 月 Google 线下 Workshop 提供可复制的代码与中文实验文档。100 分钟包含约 30–40 分钟讲解和组队实践，成果展示另计；每组 5 人。
- 用三个 Agent、五个核心 Skill 完成美股下周研究，输出 BUY／SELL／HOLD、趋势、证据信心、来源、反证和失效条件。它不执行交易，信心不是胜率。
- 优先 Google ADK Python 与 Gemini，当前固定 ADK 2.13.0、Gemini 3.8 Flash，使用 Google AI Studio Key / Gemini Developer API。不要自行切到 Vertex AI 或其他模型。
- 每组目标预算 $5，优先节省模型调用；只有实测需要时再讨论上调，原设计上限为 $30。当前应用账本阈值 $4、最多 20 次研究、每次最多 16 个模型步骤；这些不是平台硬账单上限。
- 本地可运行是当前交付要求。Cloud Shell / Web Preview 按用户要求暂未验证，不能写成已通过。港股／A 股、托管 Registry、向量检索等均不是已实现功能。

## 文档与演示要求

- `README.md` 是唯一面向活动的演讲与操作主文档，不恢复独立 WORKSHOP.md 或 ZIP 分发；通过 HTTPS GitHub 仓库获取与更新。
- 固定顺序：ADK／Skill 概念 → 环境安装与 Key 配置 → 核心代码、预检机制与 YAML → 实际运行 → Discovery／生命周期 → 修改方法 → 扩展实验。
- 环境准备里不启动 Web UI。讲完代码进入运行章节时，统一介绍 CLI 和 ADK Web UI 两种方式；后续每种实际实验都保留对应命令和 UI prompt。
- 重点说明项目主动实现的 `doctor`、`offline-check`、`scan()`、`inspect_skill()`、`accepted_skills()`：做什么、怎样做、输出与边界，以及怎样迁移到其他项目。不要只留一个链接让读者另查源码。
- 保留核心代码摘录、关键 Prompt、State 数据流图、EAGER／LAZY 对照和配置用途。讲逻辑与数据流，不逐行堆叠全部实现；更长细节放 `docs/implementation.md`。
- 使用中性文档语气，删除“讲师沿着／观众沿着”“不运行也能跟读”“本地已验证”等旁白和状态广告。时间安排在 `INSTRUCTOR.md`，验收明细在 `VALIDATION.md`。
- 关键操作保留实际输出节选。明确省略字段、合成输入和历史截图口径，不把示例行情当当前市场事实。
- 适量配图，原创图优先中文，保留 Skill 名等专有词。可用官网图、原创图与真实截图；引用外部图片时保留来源与许可。
- Trace 截图只放在关键机制处，展示实际 Workflow、请求内容和耗时。不得生成或伪造运行截图，也无需每次运行加图。
- 主文档不放作者机器的代理配置或绝对路径；开发与验证状态写 `docs/progress.md`。

## 架构与文件入口

- `stock_research/cli.py`：doctor、offline-check、run、fetch、lab、import-skill。
- `stock_research/web.py` 与 `web_agents/research/`：确定性 prompt 路由，原生 Web UI 加载 research；通过 `ctx.run_node(team)` 在当前 invocation 中运行同一 Workflow，不额外调用路由模型。
- `stock_research/runtime.py`：环境与 YAML、真实工具、角色 Prompt、结构化输出、Workflow、CLI／Web 共享的最终校验、预算与运行留档。
- `stock_research/compatibility.py`：零模型 token 的候选检查、内容哈希、过滤与隔离导入；ADK 原生解析器仍负责格式解析。
- `stock_research/data.py`：完整美股日线、RSS 标题、确定性指标、纽约时区交易日历和日缓存。
- `stock_research/labs.py`：程序控制的真实 ADK 工具实验，不调用 Gemini。
- `skills/`：五个核心方法；`extensions/`：待适配样例及受控脚本；`vendor/skills/`：固定来源第三方原件与许可。
- `config/workshop.yaml` 是本项目读取的应用配置，不是 ADK 通用配置格式。保留 technical → catalyst → review 的角色名与顺序，Review 模板依赖前两份分析。
- `requirements.lock` 固定依赖；`skills.lock.json` 是交付内容快照，当前运行不会自动强制比对它。方法修改后记录新哈希，需要时同步更新快照和说明。

## 必须保持的行为

- Agent：technical 分配 data-quality + technical-trend；catalyst 分配 news-catalyst；review 分配 risk-review + decision-report。
- 原始证据在 Python bundle 中，由工具读取；State 传递 ticker、as_of 和结构化分析，Review 通过 `{technical}`／`{catalyst}` 模板读取。不要将完整 bundle 与 State 混称。
- `doctor` 检查 Key 存在性和静态能力，不联网、不打印 Key；零退出码不表示所有 Skill 或 API 可用。
- `offline-check` 真正准备合成数据并构造 ADK 团队，检查后关闭 Toolset；不运行 Runner、不生成虚构报告。
- 只有 SUPPORTED 方法进入团队；必需方法被拒绝时明确失败，不悄悄退回无 Skill 流程。保持能力画像 `TOOLS` 与宿主真实工具注册一致。
- `vendor/` 导入只隔离保存，不能自动激活、执行脚本或覆盖不同内容的同名版本。静态通过不是安全审计或语义兼容保证；UNKNOWN 为预留状态。
- EAGER／LAZY 控制模型目录披露，不控制本地文件何时解析。ADK 原生默认 LAZY，本项目默认 EAGER；LAZY 先 list 是项目额外 Prompt 要求。
- 开启 `ADK_ENABLE_SKILL_LIFECYCLE=1`；主任务 BOUNDED 上限每个 Agent 为 2。上限仅限制 bounded；ephemeral 下一 invocation 失效；卸载不会删除业务结果、已读事实或 Artifact。
- fixture 仅允许 DEMO，最终强制 insufficient_data / HOLD / unknown / low。live 只用完整且不过期日线；新闻只有标题时 degraded，信心最高 medium。禁止静默用 fixture 冒充 live。
- 最后交付经过 `validate_decision()` 的 Markdown／decision.json，中间 review 原始 JSON 尚未完成业务后处理。
- Web 每次研究使用 New Session；Skill 和角色 YAML 每次重新读取，Python 修改后重启服务。README 的 Web 命令使用内存 Session／Trace，重启不保留。
- CLI 和 Web 共享 `runs/budget.json`、`.running` 锁和失败留档。不要删除账本绕过预算，不并发执行同一目录的完整研究。
- 机制 lab 是代码控制的真实工具操作，不称作模型自主行为。脚本 lab 只执行包内短脚本，UnsafeLocalCodeExecutor 不提供沙箱；默认研究团队没有通用脚本执行器。

## 本地开发、验证与跨设备恢复

从仓库根目录执行，要求 Python 3.11+：

```bash
bash scripts/setup.sh
.venv/bin/python scripts/configure.py
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli offline-check
.venv/bin/python -m pytest -q
```

`configure.py` 会隐藏输入并保存本机 `.env`。另一台设备重新创建虚拟环境和凭据，不复制旧 `.venv`、`.env` 或机器专属配置。

```bash
.venv/bin/adk web web_agents --port 8000 --no-reload --no_use_local_storage
```

选择 research，新建 Session 后发送：

```text
研究 mode=fixture ticker=DEMO discovery=eager，给出证据、反证、失效条件和信心。
```

- 先读本文件、`docs/progress.md`、当前代码和 Git 状态；进度有变化时同步更新 progress，原始验证事实记录在 VALIDATION。
- 回归优先使用零网络／零 token 测试。单纯文档改动不必重复付费模型实验；需要真实验证时串行运行，核对账本，失败保留部分 trace 和 usage。
- 作者本机外部 CLI 通讯按既有约定通过 HTTP 代理 `http://127.0.0.1:1080`；模型与数据层可读 `LOCAL_PROXY`。该地址是机器配置，换设备时按实际环境设置，不写回观众操作步骤。
- 不把 `.env`、凭据、真实行情缓存、个人 runs、`.adk/`、虚拟环境、安装器输出或临时截图放进 Git。官方配图、正式合成输入 Trace 截图与许可证属于仓库资产。
- 不在日志、聊天、prompt、提交差异或截图中泄露 Key。检查暂存文件和差异；不要 `git add -f` 绕过忽略规则。
- 提交／推送遵从当次用户请求；保留已有用户改动，先检查远端 main，不 force-push。网络或权限失败时按工具要求申请执行权限，不尝试绕过。
