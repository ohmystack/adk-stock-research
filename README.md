# 在正确的时刻，加载正确的 Skill

**Google ADK × Gemini · 股票研究团队实战**
`100 分钟`　`3 个 Agent`　`5 个 Skill`　`本地已验证`

![封面：ADK Skills 研究团队](docs/images/cover.svg)

> 一份文档，两条阅读路径。讲师沿着「讲解」浏览机制与图示；观众沿着「动手」复制命令、检查结果。
> 本项目已进行本地验证，完整状态见 [验证记录](VALIDATION.md)。Cloud Shell 验证尚未进行。

[GitHub 仓库](https://github.com/ohmystack/adk-stock-research) · [核心代码](#adk-wiring) · [操作与输出](#hands-on) · [讲师备忘](INSTRUCTOR.md) · [本地验证](VALIDATION.md) · [来源与许可](THIRD_PARTY_NOTICES.md)

**今天的目标**：用同一组工具，换一套 Skill，让 Agent 改变研究方法；最后得到有来源、有反证、说明信心的股票分析报告。

| 时间建议 | 内容 | 到达标志 |
| --- | --- | --- |
| 00–35 分钟 | 讲解与演示 | 理解 Agent／Tool／Skill 与能力管理 |
| 35–50 分钟 | 环境、首份报告 | 三位 Agent 实际完成任务 |
| 50–65 分钟 | Discovery、生命周期 | 看到工具集合和指令变化 |
| 65–90 分钟 | 小组改造 | 换 Skill，比较证据与结论 |
| 90–100 分钟 | 固定版本、整理产物 | 报告、修改说明、演示材料 |

成果展示另计。进度不同的小组可跳过选做内容，不要求把所有挑战做完。

**不运行也能跟读**：重要命令后附有结果节选，主要取自 2026-10-29 的本地验证。JSON 只保留与讲解相关的字段；机器上的绝对路径统一简写为 `runs/...`。股票、时间、模型文本与耗时随实际运行变化，历史结果不代表当前行情。

---

## 01 · 讲解：从模型回答到 Agent 应用

### 第一次接触 ADK？先分清模型与应用

**Gemini 是模型，ADK 是组织 Agent 应用的开源开发框架。** 直接向模型提问，通常得到一段回答；让它完成一个研究任务，还需要取数据、做计算、保存中间结果、交给另一位研究员审查，再形成最终报告。ADK 帮我们把这些步骤接起来。

ADK 全称 **Agent Development Kit**。它支持定义 Agent、连接工具、编排多 Agent 工作流，并管理会话、状态和执行事件。本次选用 Python 与 Gemini；ADK 的职责是组织执行过程，模型负责理解和判断。[ADK 官方介绍](https://adk.dev/)

![ADK 如何组织模型与工具完成任务](docs/images/adk-overview.svg)

可以把这套系统想成一个研究小组：

- **Agent（智能体）**是有明确职责的研究员，拿到目标后决定下一步需要什么信息。
- **Tool（工具）**提供实际操作，例如拉取行情或计算均线。模型发出调用请求，由运行环境执行，再把结果交回模型。
- **Session / State（会话与状态）**保存这次研究的上下文与中间结果，例如股票代码、截至时间和前一位研究员的结论。
- **Workflow（工作流）**安排谁先工作、谁读取谁的结果。确定的流程不必每一步都再请模型决定。

因此，一次用户请求可能经历多次“模型判断 → 工具执行 → 返回结果”，而不是模型回答一次就结束。我们会观察事件记录，确认 Agent 实际做过什么。

ADK 可以运行在本机或服务器，也提供开发调试界面；界面的存在不等于 Agent 已经拥有浏览器操作能力。能访问什么系统，仍取决于配置了什么工具。

### ADK + Skill：给研究员一本可替换的方法手册

研究员已经有取行情和算指标的工具，为什么还需要 Skill？因为**拥有工具，不等于知道怎样可靠地使用它**。

例如，同样看到均线、RSI 与新闻，有的方法强调趋势延续，有的方法要求先排查风险。Skill 把这些专业步骤、判断规则、参考资料和可选脚本整理成可复用目录。换一种研究方法，优先换 Skill，不必重写整个 Agent。

```text
technical-trend/
├── SKILL.md                  # 名称、描述，以及该方法的操作步骤
└── references/
    └── method.md             # 需要时再读取的详细分析规则
```

`SKILL.md` 顶部的 YAML 声明名称和描述，正文描述“何时用、怎么做、需要哪些资料”。目录还可以包含 `assets/` 或 `scripts/`；脚本需要运行环境提供执行后端，不会因为放进目录就自动执行。

![Skill 按需展开：目录、方法与参考资料](docs/images/skill-disclosure.svg)

**ADK 使用 `SkillToolset` 把 Skill 接给 Agent，并逐层披露内容：**

| 层次 | 模型在什么时候看到 | 在本项目中的例子 |
| --- | --- | --- |
| 名称与描述 | EAGER 模式随请求提供目录；LAZY 模式先用 `list_skills` 查看 | 判断 `technical-trend` 是否相关 |
| 方法正文 | 调用 `load_skill` 后 | 先检查指标，再解释趋势，最后给出反证 |
| 参考资料／资源 | 调用 `load_skill_resource` 时按需读取 | 读取 `references/method.md` 的详细规则 |

这就是**渐进披露**：先知道有哪些方法，选中后再展开步骤和资料，避免一开始把所有手册全文塞进上下文。整个 Skill 目录可以先保存在本地；这里的“按需”主要指模型上下文中看到哪些内容。[ADK Skills 官方文档](https://adk.dev/skills/)

Skill 也可以声明需要的额外工具。宿主先注册真实工具，Skill 激活后 ADK 再暴露相应工具；仅在 Markdown 中写 `WebSearch` 或 `Bash`，不会自动创建这些能力。本次的兼容性预检会先找出这类不匹配。

### 把这些概念放进股票研究任务

![三 Agent 的证据流](docs/images/architecture.svg)

| 组件 | 在本项目中做什么 |
| --- | --- |
| **Agent** | 技术分析师分析价格；事件分析师分析新闻；风险审查员审查并写结论 |
| **Tool** | 读取证据、计算可靠数值；它决定实际能做什么 |
| **Skill** | 分析方法、步骤、风险规范与参考资料；它决定怎样做 |
| **Workflow** | 固定先后顺序、传递分析结果；默认顺序运行，减少配额突发 |

新增专业方法，先考虑 Skill。新增系统访问能力，增加 Tool。需要独立上下文或判断职责，再增加 Agent。

本项目使用 ADK 2.0 的原生 **Workflow** 编排。五个 Skill 已分配给三个角色：

```text
技术分析师（technical） → data-quality + technical-trend
事件分析师（catalyst）  → news-catalyst
风险审查员（review）   → risk-review + decision-report
```

业务流程：取证据 → 算指标 → 两份分析 → 审查反证 → 建议与信心 → 校验与保存。原始数据、分析规则与执行能力分开，才能解释改动为什么影响结果。

<a id="adk-wiring"></a>

### 核心代码：ADK 怎样把这些组件接起来？

下面按执行顺序摘出项目的核心接线，省略日志、预算与错误处理；注释用于讲解，**片段不需要逐段执行**。观众动手仍使用后面的命令入口。完整实现见 [兼容性检查与加载](stock_research/compatibility.py)、[Agent 与 Workflow](stock_research/runtime.py)。

**① Skill 声明方法，以及它需要哪些工具。**

[technical-trend/SKILL.md](skills/technical-trend/SKILL.md) 的关键内容：

```markdown
---
name: technical-trend
description: Analyze stock price trend using deterministic technical indicators.
metadata:
  adk_additional_tools: ["calculate_indicators", "read_evidence"]
---

先调用 calculate_indicators。读取 references/method.md。
根据指标解释趋势；只引用工具数值和 P1。给出反证和失效条件。
```

名称和描述帮助模型选择；正文告诉它怎样做；`adk_additional_tools` 引用的是宿主必须提供的工具名称，不是安装指令。

**② 检查目录，再用 ADK 原生 API 解析 Skill。**

```python
from google.adk.skills import load_skill_from_dir

reports = scan()  # 本项目的零 token 能力检查
skills = {
    r["skill"]: load_skill_from_dir(ROOT / "skills" / r["skill"])
    for r in reports
    if r["status"] == "SUPPORTED"
}
```

这时得到的是 Python 中的 Skill 对象，模型还没有自动读过所有正文。`load_skill_from_dir` 负责解析目录；后续模型调用的 `load_skill` 工具负责把相应方法交给模型。两步不要混为一谈。

**③ SkillToolset 配置发现方式、生命周期和可绑定的真实工具。**

下面位于角色构造循环中；`names` 来自 [角色配置](config/workshop.yaml)，例如技术分析师分配到两个 Skill。

```python
from google.adk.tools.skill_toolset import (
    SkillToolset, SkillDiscoveryMode,
    SkillLifecycleConfig, SkillLifecycleMode,
)

toolset = SkillToolset(
    skills=[skills[n] for n in names],
    additional_tools=[read_evidence, calculate_indicators],
    discovery_mode=SkillDiscoveryMode(discovery),  # eager 或 lazy
    lifecycle_config=SkillLifecycleConfig(
        default_mode=SkillLifecycleMode.BOUNDED,
        max_active_skills=2,
    ),
)
```

`additional_tools` 放的是实际 Python 函数。Skill 激活后，ADK 按其元数据把匹配工具加入模型请求。主任务的上限是 2；后面的生命周期小实验会专门改成 1，方便看到淘汰。

本项目启动时还会设置 `ADK_ENABLE_SKILL_LIFECYCLE=1`；仅有配置对象，不代表实验能力已开启。

**④ Agent 配置职责、SkillToolset 和结构化结果。**

```python
from google.adk.agents import LlmAgent

agents.append(LlmAgent(
    name=role,                  # technical、catalyst、review
    model=model,                # gemini-3.8-flash
    instruction=instruction,    # 角色要求、先加载 Skill、证据规则
    tools=[toolset],
    output_schema=Decision if role == "review" else Analysis,
    output_key=role,            # 将结果写入相应 state 键
))
```

`instruction` 约束角色的任务；具体分析方法放在 Skill 中。`output_schema` 规定结果结构，不能保证事实正确。`output_key` 让后续角色读取前一位的结果。

风险审查员的指令里包含以下模板，ADK 会用 state 中的两份分析替换占位符：

```python
instruction += (
    "Technical analysis: {technical}\n"
    "Event analysis: {catalyst}\n"
    "Use both outputs, audit counterarguments and sources."
)
```

**⑤ Workflow 固定先后，Runner 执行一次任务。**

```python
from google.adk import Workflow
from google.adk.runners import Runner
from google.adk.artifacts import InMemoryArtifactService

team = Workflow(
    name="research_team",
    edges=[("START", *agents)],
    timeout=180,
)

runner = Runner(
    node=team,
    app_name="workshop",
    session_service=sessions,
    artifact_service=InMemoryArtifactService(),
)
```

`agents` 按 `technical → catalyst → review` 顺序构造，因此这里是一条顺序流程：前两位各自分析，最后一位综合。接着 `runner.run_async(...)` 接收用户消息并持续返回事件；项目从事件中记录工具调用、响应和 token 用量。

**读代码时抓住这条线**：目录解析 → 合格 Skill → SkillToolset → 角色 Agent → Workflow → Runner。观众通常只需改 Skill 正文／参考资料和角色配置，核心接线保持不变。

### 4 月以后，这次重点看什么？

| 能力 | 机制 | 本项目入口 |
| --- | --- | --- |
| Discovery | EAGER 注入本地目录；LAZY 用 list_skills 取目录 | `lab discovery` |
| 生命周期 | bounded 上限、显式卸载、ephemeral 单轮有效 | `lab lifecycle` |
| 动态工具 | Skill 激活后，宿主已注册的额外工具才暴露给模型 | 首跑的 requests／trace |
| State 注入 | 加载 Skill 时读取当前 state 变量 | data-quality 的 ticker／as_of |
| 脚本产物 | 脚本生成文件，原生保存到 ArtifactService | `lab artifacts` |
| Registry | 搜索元数据，再获取完整 Skill | `lab registry` |

动态工具和脚本执行在 4 月前已有；本次新增重点是 9 月的 Discovery／生命周期及 10 月的产物和追踪改进。版本依据见 [ADK 2.10](https://github.com/google/adk-python/releases/tag/v2.10.0)、[ADK 2.12](https://github.com/google/adk-python/releases/tag/v2.12.0)。

Skills 仍属实验能力。本项目启动时显式开启生命周期开关，不把它当作默认稳定特性。

---

<a id="hands-on"></a>

## 02 · 动手：准备环境

以下命令都在仓库根目录 `adk-stock-research` 运行。需要 Python 3.11+。主线不需要 Node；npx 挑战另需 Node 22.20+。

### 首次获取项目：HTTPS 克隆

Cloud Shell 打开终端，执行：

```bash
git clone https://github.com/ohmystack/adk-stock-research.git
cd adk-stock-research
bash scripts/setup.sh
```

这会下载整个项目，包括文档、图示、代码和 Skill。**Cloud Shell 操作路径尚未彩排**，本轮只验证本地。

安装成功时，本地日志的关键部分如下；已装依赖时还会出现 `Requirement already satisfied`，不必逐行对照版本下载进度。

```text
Successfully built adk-skills-workshop
Successfully installed adk-skills-workshop-0.1.0
```

安装脚本最后自动运行 `doctor`。第一次还没配置 Key 时，`gemini_key_present` 为 `false` 是正常的，下一步配置后再检查。

### 已有项目：拉取更新

进入之前克隆的目录，先确认本组改动，再拉取仓库更新：

```bash
cd ~/adk-stock-research
git status --short
git pull --ff-only
bash scripts/setup.sh
```

如果有本组修改或出现冲突，先保存到小组分支再处理；不要用重置命令丢弃实验成果。`git pull` 用于已有仓库，首次下载使用上面的 `git clone`。

### Python 版本检查

项目已有 `.venv` 时安装脚本会复用；没有 Python 3.11+ 时，先安装合适版本，也可用 `WORKSHOP_PYTHON=/path/to/python3.12 bash scripts/setup.sh` 明确指定解释器。

### 配置 Google AI Studio Key

在 [Google AI Studio](https://aistudio.google.com/apikey) 创建 Key。每组由一人保管；Key 不进入聊天、Git 或展示文件。

在本地或 Cloud Shell 中运行：

```bash
.venv/bin/python scripts/configure.py
```

按提示输入 Key，屏幕不回显。脚本保存到权限为 600 的 `.env`，默认使用 Gemini Developer API 的 `gemini-3.8-flash`。已有 `.env` 可直接复用，无需重复配置。

交互提示如下，隐藏输入的位置不会显示 Key：

```text
Gemini API key (hidden):
Saved private .env. Run doctor to check presence; the key will not be displayed.
```

```bash
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli offline-check
```

**检查点**：`gemini_key_present: true`；五个核心 Skill 均为 `SUPPORTED`；离线检查显示三个角色与目标交易周。`offline-check` 不调用 Gemini，也不生成虚构的模型报告。

**`doctor` 结果节选**：下面只保留两条 Skill，完整输出还包含另外三条、哈希和检查理由。

```json
{
  "python": "3.12.8",
  "adk": "2.13.0",
  "gemini_key_present": true,
  "skills": [
    {
      "skill": "data-quality",
      "status": "SUPPORTED"
    },
    {
      "skill": "decision-report",
      "status": "SUPPORTED"
    }
  ]
}
```

**`offline-check` 结果节选**：尚未调用模型，但 Agent 构造、确定性指标和目标交易周已能验证。

```json
{
  "model_called": false,
  "agents": [
    "technical",
    "catalyst",
    "review"
  ],
  "target_week": {
    "start": "2026-09-28",
    "end": "2026-10-02",
    "sessions": 5
  }
}
```

### 初始化检查做了什么？

检查器使用真实 ADK 解析 Skill，核对工具、资源、路径和已知宿主语法；不执行文档里的命令。它是零 token 的保守规则检查，**不是完整安全审计或运行成功保证**。

| 状态 | 行为 |
| --- | --- |
| SUPPORTED | 已知能力匹配，可加载；验证等级单独注明 |
| ADAPTABLE | 当前不能原样运行，先适配再检查 |
| UNSUPPORTED | 当前环境不支持，跳过 |
| UNKNOWN | 无法判断，跳过 |

将不兼容 Skill 放进 skills 后，doctor 显示原因；加载器只让通过项进入可发现目录。如果配置要求的角色 Skill 不可用，任务明确失败，不悄悄改用无 Skill 的 Agent。

---

## 03 · 动手：第一份报告

先用项目原创的合成数据，专注运行机制：

```bash
.venv/bin/python -m stock_research.cli run --mode fixture
```

这条命令**真实调用 Gemini**；`fixture` 指输入数据固定，不是模型响应回放。证券 `DEMO` 是虚构的，最终建议强制为 HOLD／观望、未知趋势、低信心。

**命令结束时的输出**（绝对路径已简写）：

```json
{
  "output": "runs/20261029T092441-dfded3"
}
```

这个路径就是本次实验的结果目录。打开其中的 `decision.json`，本地实测的重点字段如下：

```json
{
  "ticker": "DEMO",
  "data_mode": "fixture",
  "analysis_status": "insufficient_data",
  "trend": "unknown",
  "action": "HOLD",
  "confidence_level": "low",
  "evidence_ids": [
    "P1",
    "N1"
  ]
}
```

同次运行的 `usage.json` 节选：

```json
{
  "model_responses": 9,
  "tool_calls": 17,
  "seconds": 32.37,
  "estimated_usd": 0.019894
}
```

这里的费用按付费标价估算，实际免费层可能为零。合成数据下的 HOLD 是数据质量约束，不是一次真实股票判断。

成功后，终端返回 `runs/<运行编号>`。打开这个目录：

| 文件 | 用来回答什么问题 |
| --- | --- |
| `report.md` | 最终建议、反证、信心与失效条件是什么？ |
| `decision.json` | 结果、数据模式与版本能否被程序核对？ |
| `evidence.json` | 每个证据编号对应什么来源和截至时间？ |
| `trace.json` | 哪个 Agent 加载了什么、调用了什么工具？ |
| `requests.json` | 每次模型请求看到了哪些工具和系统说明？ |
| `usage.json` | 本次 token、模型响应次数、耗时与估算费用？ |

**检查点**：找到三个角色的 `load_skill` 调用；找到行情／新闻工具响应。模型跳过必要 Skill 时，程序拒绝把它标成一次成功实验。

**工具调用长什么样？**下面节选自一次本地实测的 `trace.json`；技术分析师先请求加载两个方法：

```json
{
  "author": "technical",
  "calls": [
    {
      "name": "load_skill",
      "args": {
        "skill_name": "data-quality"
      }
    },
    {
      "name": "load_skill",
      "args": {
        "skill_name": "technical-trend"
      }
    }
  ]
}
```

再看同次运行的 `requests.json`，技术分析师激活 Skill 前后，请求中的工具集合发生了变化：

```text
激活前：set_model_response, load_skill, load_skill_resource, unload_skill
激活后：以上工具 + read_evidence, calculate_indicators
```

`set_model_response` 是 ADK 为结构化结果提供的内部响应工具。新出现的两个业务工具，来自 Skill 元数据与 `additional_tools` 的匹配；不需要让所有 Agent 一开始就看到所有工具。

**Skill 怎样拿到本次任务信息？**[data-quality/SKILL.md](skills/data-quality/SKILL.md) 还声明了加载时的 state 注入：

```yaml
metadata:
  adk_inject_state: true
  adk_additional_tools: ["read_evidence"]
```

正文中的 `当前证券：{ticker}；证据截至：{as_of}`，在这次 `load_skill` 的响应里变成：

```text
当前证券：GOOGL；证据截至：2026-10-29T05:21:11.520714-04:00。
这是加载时的 state 注入快照。
```

这与风险审查员读取 `{technical}`／`{catalyst}` 的 Agent 指令模板分别发生在不同位置：一个在 Skill 加载时，一个在构造模型指令时。

### 切换真实股票

```bash
.venv/bin/python -m stock_research.cli fetch --ticker GOOGL --refresh
.venv/bin/python -m stock_research.cli run --mode live --ticker GOOGL
```

行情由 yfinance 获取，事件线索来自 Google News RSS；不使用付费 Search Grounding。每个自然日缓存一次，`fetch --refresh` 可显式更新。缓存保留真实截至时间，读取缓存不伪装成重新抓取。

**“下周”采用纽约时区**：下一个自然周的真实交易日。报告中的参考收盘价来自最新完整日线；它不是未来成交价。预测目标口径是目标周首个交易日开盘到最后交易日收盘的方向，现场不评判收益。

当前新闻路径只读标题和发布时间，未核验全文，因此最多中信心；缺少新闻明确降级，行情过期则拒绝标成 live。来源站点不可用时不会静默换成合成数据。

**真实数据获取结果节选**（2026-10-29 本地记录，字段与 `fetch` 的输出一致）：

```json
{
  "ticker": "GOOGL",
  "as_of": "2026-10-29T05:21:11.520714-04:00",
  "mode": "live",
  "indicators": {
    "last_close": 324.890015,
    "sma20": 339.8105,
    "sma60": 342.837212,
    "last_bar": "2026-10-28"
  },
  "target_week": {
    "start": "2026-11-02",
    "end": "2026-11-06",
    "sessions": 5
  }
}
```

**随后三 Agent 完成的结果节选**：

```json
{
  "ticker": "GOOGL",
  "data_mode": "live",
  "analysis_status": "degraded",
  "trend": "down",
  "action": "SELL",
  "confidence_level": "medium",
  "evidence_ids": [
    "P1",
    "N1",
    "N2",
    "N5"
  ]
}
```

这个历史样例展示“卖出＋中信心”的结果形态，不是保证再次运行会得出相同方向。`degraded` 表示证据降级：当时事件侧只读取标题，报告仍须保留反证、缺失信息和失效条件。

真实行情与新闻不提交到仓库，使用时遵守数据提供方条款。建议每组先研究一只美股；不要直接把港股／A 股代码塞进美股日历流程。

---

## 04 · 讲解＋动手：Discovery

```bash
.venv/bin/python -m stock_research.cli lab discovery
```

打开 `runs/lab-discovery.json`：

**结果节选**（只展示工具列表，省略很长的系统指令）：

```json
{
  "modes": {
    "eager": {
      "tools": [
        "load_skill",
        "load_skill_resource",
        "unload_skill"
      ]
    },
    "lazy": {
      "tools": [
        "list_skills",
        "load_skill",
        "load_skill_resource",
        "unload_skill"
      ]
    }
  }
}
```

- **EAGER**：system instruction 里有名称与描述；工具列表中没有 list_skills。
- **LAZY**：提供 list_skills，Agent 需要调用它获得本地目录。

这个无 Key 实验实际执行 ADK 请求处理器，控制条件固定，没有模型选择随机性。

有额度的组再做真实对照：

```bash
.venv/bin/python -m stock_research.cli run --mode fixture --discovery eager
.venv/bin/python -m stock_research.cli run --mode fixture --discovery lazy
```

比较两次运行的 requests、trace 与 usage。目录相同、任务相同，只改变模式。记录总 token 和耗时，不预设 LAZY 一定更省。

**原理**：LAZY 仍可能返回很长的列表；检索少量相关 Skill 需要 Registry。`search_skills` 不是第三种 Discovery 枚举模式。

---

## 05 · 讲解＋动手：加载、切换、释放

![Skill 生命周期](docs/images/lifecycle.svg)

```bash
.venv/bin/python -m stock_research.cli lab lifecycle
```

依次观察 `runs/lab-lifecycle.json`：

| 步骤 | 激活状态 | 应观察到的变化 |
| --- | --- | --- |
| 加载 risk | lab-risk | risk_probe 进入工具声明 |
| 加载 report | lab-report | bounded 上限为 1，risk 被淘汰 |
| 加载 glossary | lab-report + lab-glossary | ephemeral 不计入 bounded 上限 |
| 下一轮 | lab-report | glossary 失效，其独有贡献不再暴露 |
| 显式卸载 report | 空 | 相关动态工具消失 |

`pruned_history` 展示已经卸载的 Skill 指令被替换成短通知。卸载影响下一次请求，不删除已保存事实、报告或 Artifact。

**结果节选**：保留原始步骤名和激活列表，省略每步重复的工具声明。

```json
{
  "steps": [
    {"step": "load risk", "active": ["lab-risk"]},
    {"step": "load report; bounded cap evicts risk", "active": ["lab-report"]},
    {"step": "ephemeral loaded in turn 1", "active": ["lab-report", "lab-glossary"]},
    {"step": "turn 2; ephemeral expired", "active": ["lab-report"]},
    {"step": "explicit unload", "active": []}
  ],
  "pruned_history": {"skill_name": "lab-risk", "status": "unloaded"}
}
```

对照 `stock_research/labs.py` 中的配置，就能解释为什么会出现这些状态：

```python
SkillLifecycleConfig(
    default_mode=SkillLifecycleMode.BOUNDED,
    max_active_skills=1,
    skill_overrides={"lab-glossary": SkillLifecycleMode.EPHEMERAL},
)
```

**三件容易混淆的事**：

1. 一轮 invocation 可以包含多次模型／工具调用；ephemeral 不等于“调用一次工具就失效”。
2. 激活数量上限只约束 bounded；persistent 和 ephemeral 不计入。
3. 本实验是代码控制的真实 ADK 工具操作，用于解释机制；不能称作模型自主选择。

---

## 06 · 小组挑战：换 Skill，换方法

每组 5 人建议分工：运行、Skill 设计、数据、验证、展示。完整模型任务从一个主实例发起，避免五个人争用同一项目配额。

### A · 保守研究员｜推荐起点

编辑 `skills/risk-review/SKILL.md` 正文，在保留格式和工具声明的前提下加入：

```text
若技术面与事件面冲突，优先 HOLD，并明确列出冲突。
若只有新闻标题，没有核验全文，信心不得超过中。
即使趋势向上，也必须说明追高风险与失效条件。
```

```bash
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli run --mode live --ticker GOOGL
```

**检查点**：同一证据包，比较修改前后报告；不要只看 BUY／HOLD 有没有变化，更要看依据是否改变。每次运行重新检查并记录 Skill 哈希，重启运行即可生效。

### B · 趋势跟随者

编辑 `skills/technical-trend/references/method.md`：声明以 SMA20／60 与近期收益方向形成假设，遇到高 RSI 或高 ATR 说明风险。禁止添加工具未返回的指标值。观察方法与结论的关系。

### C · 证据审查员

加强 `news-catalyst`：区分评论、报道和未确认信息；对新闻标题只描述“标题称”，不把它扩写成已核验事件。找一个让 Agent 需要降级的输入。

### D · 添加一个新 Skill

复制一个课程 Skill 目录，修改目录名、frontmatter name 和 description；在 `config/workshop.yaml` 对应角色列表中加入新名称。它只能使用已注册工具，新增外部系统需要新增 Tool。

```bash
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli offline-check
```

如果同一角色加入三个以上 bounded Skill，要同时审视激活上限，避免加载新方法时把仍需使用的方法淘汰。Skills 改造支持的是现有研究工具范围内的方法变化，不承诺任意目录都能自动变成任意领域的 Agent。

---

## 07 · 选做：真实第三方 Skill 与 npx

包内已有固定版本的 Position Sizer，来自 [tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)，保留 MIT 许可证。它计算仓位，不预测走势。

```bash
.venv/bin/python -m stock_research.cli import-skill vendor/skills/position-sizer
```

包内原件已存在，同一内容重复导入会返回 `already_present: true` 和检查结果，不重复复制。默认运行配置没有通用脚本执行器，因此原件检查为 ADAPTABLE。导入只放进 vendor 隔离目录，不自动激活。

**导入结果节选**：安装成功与运行能力匹配是两件事。

```json
{
  "skill": "position-sizer",
  "status": "ADAPTABLE",
  "reasons": [
    "scripts present; default runtime has no script executor"
  ],
  "activated": false,
  "already_present": true
}
```

已适配版本位于 `extensions/position-sizer-adk`：脚本和参考资料保留，只把宿主操作说明改为 ADK 的工具步骤。

```bash
.venv/bin/python -m stock_research.cli lab sizing
```

**检查点**：合成账户 10,000，单笔风险 1%，入场 100，止损 95 → 20 股，风险 100。查看原生 `run_skill_script` 与写入 ArtifactService 后读回的 JSON／Markdown。

**结果文件读回并解析后的字段节选**：

```json
{
  "final_recommended_shares": 20,
  "final_position_value": 2000.0,
  "final_risk_dollars": 100.0,
  "final_risk_pct": 1.0
}
```

重点是可核算：风险预算为 100，每股风险为 5，因此得到 20 股。这个 Skill 只负责仓位计算，不提供股价趋势结论。

### npx 安装不是运行时接线

可选安装器练习需 Node >=22.20；在项目根目录运行：

```bash
npx --yes skills@1.7.4 add ./vendor/skills/position-sizer --agent universal --copy --yes
.venv/bin/python -m stock_research.cli import-skill .agents/skills/position-sizer
```

安装器把文件放入 `.agents/skills/`，ADK 仍需要检查、显式加载和实际执行后端。仓库下载、ZIP 解包、手动复制也遵循同一条路径。同名、同内容的重复导入返回检查结果；同名但内容不同则拒绝覆盖，要求另选版本目录。

**npx 本地安装输出节选**（省略交互界面的边框和进度）：

```text
Found 1 skill
Skill: position-sizer
./.agents/skills/position-sizer
copy → Universal
Installation complete
```

看到这个目录，只证明文件已安装；后续仍要经过导入检查和 ADK 接线。

`Read`、`WebSearch`、`Bash` 等宿主名称不会自动创建 ADK 工具。编程助手的开发 Skill、插件配置和 ADK 运行时 Skill 也不是同一种东西。

---

## 08 · 选做：脚本产物与 Registry

### 原生脚本产物

```bash
.venv/bin/python -m stock_research.cli lab artifacts
```

查看 `runs/lab-artifacts.json` 的 `saved.metrics.json`：它来自脚本执行后的 ArtifactService 读回，并非自己写一个文件后假装 Artifact。进程结束前导出到 runs，因此能查看与分享。

**脚本执行结果节选**：

```json
{
  "execution_result": {
    "skill_name": "metrics-export",
    "file_path": "scripts/export.py",
    "status": "success",
    "saved_artifacts": [
      "metrics.json"
    ]
  }
}
```

从 ArtifactService 读回 `metrics.json`，解析后的内容是：

```json
{
  "example": true,
  "risk_budget": 100,
  "stop_distance": 5,
  "shares": 20
}
```

关键接线是显式提供执行器和保存开关；Runner／调用上下文还需提供 ArtifactService：

```python
SkillToolset(
    skills=[script_skill],
    code_executor=UnsafeLocalCodeExecutor(),
    save_output_artifacts=True,
)
```

此实验仅启用包内审阅过的短脚本，使用 UnsafeLocalCodeExecutor；它不是沙箱。默认股票 Agent 不提供该执行器，不会运行导入目录中的任意脚本。

当前原生自动保存开关适用于 code-executor 路径，不直接适用于 Environment；框架保存 report.md 与 ADK 自动收集脚本产物要分开理解。

### 原生 Registry 接口

```bash
.venv/bin/python -m stock_research.cli lab registry
```

这是实现 ADK SkillRegistry 接口的本地关键词索引：search 返回小型元数据候选集，load 再取正文。它没有向量检索，也不声称是托管服务。

**结果节选**：查询 `risk` 后先看到候选名称，再加载对应 Skill；正文在此省略。

```json
{
  "search": [
    {
      "name": "risk-review"
    }
  ],
  "loaded": {
    "skill_name": "risk-review"
  }
}
```

Google Cloud Skill Registry 需要额外的 API、项目、区域与 IAM，留作后续扩展；本活动不把它设成完成主任务的前提。

---

## 09 · 看懂信心、成本与失败

### 信心是证据判断，不是胜率

报告输出 BUY／SELL／HOLD、趋势、高中低信心、反证、失效条件。多个 Agent 使用同一模型，观点一致不意味着独立统计证据。没有未来真值时不按预测收益评奖。

合成数据、证据不足、标题未核验、过期行情有明确处理规则。最终程序校验引用编号，拒绝虚构引用；它不能替代对事实正确性的全面核验。

### $5 的组预算

默认不调用 Search Grounding，兼容性预检和机制实验均为零模型 token。免费文本层仍有项目级请求／token 配额；换 Key 不能增加同一项目配额。[配额说明](https://ai.google.dev/gemini-api/docs/rate-limits)。

付费估算使用 2026 年 11 月 Gemini 3.8 Flash Standard 标价：输入 $0.75／百万 token，输出（含 thinking）$3.75／百万 token。40 万输入、8 万输出约 **$0.60**；实际免费层可能为零。[价格表](https://ai.google.dev/gemini-api/docs/pricing)。

`runs/budget.json` 累计本组运行与估算，默认最多 20 次、估算 $4 停止新任务；每次最多 16 个模型步骤。请求已经发出后可能产生额外消耗，这不是平台硬账单上限。不要删除账本绕过限制；组内多个目录的费用也不会自动汇总。

Google Cloud 活动抵扣与 AI Studio 余额是否通用需事先确认；本项目直接使用 AI Studio Key，不默认使用 Vertex AI。[账单说明](https://ai.google.dev/gemini-api/docs/billing)。

| 现象 | 处理 |
| --- | --- |
| Key 未配置／401／403 | doctor 只确认存在；核对 Key、模型权限、地区与 API 后端 |
| 429 | 等待配额恢复，组内串行；不要五人同时反复重试 |
| 模型未加载必要 Skill | 看 trace 与 requests，修正描述／流程；不发布“成功报告” |
| JSON 不符合契约 | 保留 failure、usage 和 trace，缩短 Skill／输出；本版不自动无限修复 |
| 行情或新闻失败 | 查看具体缺失；fixture 仅供机制练习，不伪装成实时结果 |
| 不支持 Skill | 查看 doctor 中的原因，适配后再检查 |
| `.running` 锁存在 | 先确认组内进程已结束，再人工移除残留锁；不要并发跑共享账本 |

---

## 10 · 交付你们的成果

每组保留一份运行目录、一组 Skill 修改和三句话：**改了什么、为什么、执行链和结果发生了什么变化。**

课程统一从 [GitHub 仓库](https://github.com/ohmystack/adk-stock-research) 获取与更新，不再制作 ZIP 分发包。小组修改可以保存在自己的分支或 fork 中；小组展示从 `runs/` 中单独选择报告与必要证据。

仓库的 `.gitignore` 已排除 `.env`、凭据、虚拟环境、数据缓存、临时文件和执行记录。提交前先检查 `git status --short` 与待提交差异；不要使用 `git add -f` 强行加入这些文件，也不要在 Issue、截图或报告里粘贴 Key。

**带走的能力**：Skill 让专业方法可替换；Tool 让执行可靠；Agent 让职责清晰；运行记录让这些选择可以被检验。
