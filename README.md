# 使用 Google ADK Skills 构建股票研究多 Agent 系统

**Google ADK Python × Gemini · 美股下周研究实践**

[English](README.en.md)

推荐前置阅读（ADK + Skill 基础）：[Workshop: 用 ADK 玩转 Skill](https://my.feishu.cn/wiki/EVeAwoOETiayJzk4jIMcARY2nKd)

本项目用三个 Agent 和五个 Skill，完成从证据准备、价格与新闻分析到风险审查的美股下周研究，生成带来源、反证、信心与失效条件的报告。项目只做研究，不执行交易。

全文沿着一次研究展开：先明确输入与分工，准备工具，在代码中创建并运行团队，再通过 Web UI 观察请求、模型返回和工具调用。之后对比 EAGER／LAZY，了解 Registry，并修改研究方法做实验。

[ADK 与 Skill](#adk-and-skill) · [任务设计与分工](#research-design) · [环境准备](#setup) · [函数与 Tool](#research-tools) · [Agent 与 Workflow](#agent-workflow) · [运行](#run-research) · [Web UI 请求与返回](#trace-requests) · [Discovery 对照](#skill-parameters) · [Registry](#skill-registry) · [方法改造与扩展](#extend-skills) · [成本与排错](#cost-and-errors)

<a id="adk-and-skill"></a>

## 01 · ADK 与 Skill

### 从模型回答到 Agent 应用

**Gemini 负责理解与判断，ADK 组织应用的执行过程。** 股票研究还需要获取数据、调用计算工具、保存中间结果、交给其他角色审查，并形成最终报告。这些步骤由应用连接起来。

ADK（Agent Development Kit）是用于构建 Agent 应用的开源框架，支持工具、多 Agent 编排、会话、状态与执行追踪。本项目使用 Python、Gemini 和 ADK 原生 Workflow。[官方介绍](https://adk.dev/get-started/about/)

### 已有 Codex／Claude Code + Skills，为什么还要 ADK？

**可以直接用。个人任务、一次性研究和快速验证，现成的 Agent 加合适的 Skills 往往就够了。** Codex、Claude Code 本身已经提供 Agent 运行环境。

**学 ADK，是为了把这项能力做成自己掌控、可反复调用、可接入业务的应用。** 以本项目为例：

- **流程由代码确定**：固定 `technical → catalyst → review` 的顺序，为各角色分配工具，通过 State 传递分析结果。
- **规则由程序执行**：校验证据编号、限制模型调用与预算；合成数据强制输出 `HOLD`。这些约束由应用代码实现。
- **运行过程可以检查**：CLI／Web 共用同一工作流，通过 Trace 查看模型请求、Skill 加载和工具调用，定位失败步骤。

ADK 这类框架提供工具调用、流程编排、会话、状态和追踪等通用基础设施，减少重复搭建，让开发者集中实现业务。**Skill 沉淀做事的方法，框架帮助你把方法接成应用。**

[Codex SDK](https://learn.chatgpt.com/docs/codex-sdk) 和 [Claude Agent SDK](https://platform.claude.com/docs/en/agent-sdk/overview) 同样可以用来构建应用。本 Workshop 选择 ADK + Gemini，实践的就是方法、工具与运行规则如何组合成一个应用。

### ADK 的核心组件

<img src="docs/images/adk-components.png" alt="ADK 官方组件图：Agent、工具、编排、会话、产物、调试与 Trace" width="760">

*图源：[ADK Technical Overview](https://adk.dev/get-started/about/)。*

| 组件 | 作用 | 本项目实例 |
| --- | --- | --- |
| Agent | 根据自己的职责和已有信息，判断下一步做什么 | 技术分析师、事件分析师、风险审查员 |
| Tool | 执行操作，返回事实或计算结果 | `read_evidence`、`calculate_indicators` |
| Skill | 定义方法、步骤、规则与参考资料 | 趋势分析、新闻核验、风险审查 |
| Workflow（工作流） | 安排各角色的执行顺序，以及谁需要等待谁的结果 | `technical → catalyst → review` |
| Session（会话） | 保存同一段交互中的消息和执行事件 | Web UI 中每次点击 NEW SESSION 创建的新会话 |
| State（状态） | 在会话中按键名保存数据，供后续步骤读取 | 股票代码、数据截至时间、两份分析 |
| Trace（执行追踪） | 记录执行了哪些步骤，以及各步骤的耗时 | 模型请求、Skill 加载、工具调用 |

一次任务可以包含多次“模型判断 → 工具执行 → 结果返回”。新增专业方法通常修改 Skill；新增系统访问能力需要注册 Tool；新增独立职责可以增加 Agent。

### Skill 的渐进披露

拥有工具并不等于知道如何使用工具。一个 Skill 将一套专业方法放在独立文件夹中，便于单独修改和替换：

```text
technical-trend/
├── SKILL.md
└── references/
    └── method.md
```

`SKILL.md` 开头的 YAML 区块（frontmatter）声明名称、描述等信息，后面的 Markdown 正文规定操作步骤；`references/` 保存需要时再读取的详细规则。Skill 文件夹也可以包含其他资源和脚本。要运行脚本，加载 Skill 的应用还需要配置脚本执行器。后文把这个提供工具和执行环境的应用称为“宿主”。

![Skill 的名称与描述、方法正文和参考资料逐层加载](docs/images/skill-disclosure.svg)

这些内容按需要逐层提供给模型，称为“渐进披露”。这里的模型上下文，指一次请求中模型可以读取的系统说明、对话消息和工具返回结果。

| 层次 | 进入模型上下文的时机 | 示例 |
| --- | --- | --- |
| 名称与描述 | EAGER 模式在首次模型请求中直接提供；LAZY 模式由模型调用 `list_skills` 获取列表 | 根据描述选择 `technical-trend` |
| 方法正文 | 模型调用 `load_skill` 后，正文作为工具结果返回 | 得知需要先取指标，再分析趋势与反证 |
| 参考资料 | 模型调用 `load_skill_resource` 后，指定文件的内容作为工具结果返回 | 读取 `references/method.md` 中的详细判断规则 |

ADK 的 `SkillToolset` 提供列出、加载 Skill 和读取资源的工具。调用 `load_skill` 后，该 Skill 进入激活状态：模型可以读到方法正文，也能调用它所声明、且宿主已经注册的额外工具。工具的 Python 实现仍需由应用提供。[Skills 文档](https://adk.dev/skills/)

<a id="research-design"></a>

## 02 · 股票研究任务：先确定输入、分工与调用顺序

### 把“研究下周的 GOOGL”变成执行规格

任务是：基于同一份截至时间明确的证据，研究某只美股下一个交易周的趋势，给出 BUY／SELL／HOLD，并解释来源、反证、信心与失效条件。先固定哪些事情由程序完成，再决定哪些判断交给模型。

| 设计问题 | 本项目的选择 | 落在什么位置 |
| --- | --- | --- |
| 研究哪只股票？ | 显式传入 `ticker`，例如 `GOOGL` | CLI 的 `--ticker`；Web 的 `ticker=` |
| “下周”是哪几天？ | 按证据包的 `as_of` 转为纽约日期，计算下一个周一至周日，再用美股交易日历筛选交易日 | Python `target_week()` |
| 用什么证据？ | `fixture` 使用固定合成 DEMO；`live` 获取已收盘日线与最近七天的新闻标题 | Python `load_bundle()` |
| 谁负责计算？ | Python 校验日线、计算 SMA20／60、5／20 日收益、RSI14、ATR14 等；模型读取数值并解释 | `indicators()` 与证据工具 |
| 谁负责判断？ | 技术分析师看价格趋势，事件分析师看新闻证据，风险审查员综合两份分析 | 三个 `LlmAgent` |
| 怎样得到可交付结果？ | 模型按 schema 输出；程序再次核对证据编号、合成标记与信心上限 | `Analysis`／`Decision` → `validate_decision()` |

参考价格是最新一个已收盘交易日的收盘价；研究区间是目标周第一个交易日开盘到最后一个交易日收盘。这里的信心表示证据充分程度与一致性，不是上涨概率。

### ticker 在进入模型前就已经确定

[cli.py](stock_research/cli.py) 用 `argparse` 读取命令行参数，再用正则校验股票代码，直接传给数据函数。下面是关键路径的摘录，省略其他子命令：

```python
r = sub.add_parser("run")
r.add_argument("--mode", choices=["fixture", "live"], default="fixture")
r.add_argument("--ticker", default="DEMO")
args = p.parse_args()

if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", args.ticker):
    raise ValueError("invalid US ticker")
bundle = load_bundle(args.mode, args.ticker)
```

因此 `--ticker GOOGL` 直接决定取数对象，模型收到任务时，证据包和目标交易周已经准备好。CLI 不要求模型从一句自然语言中猜股票代码。Web 也由 [parse_prompt()](stock_research/web.py) 用正则读取显式的 `mode=`、`ticker=`、`discovery=`；这一步同样不调用模型。提示词中的其余文字不会变成任意可配置的研究流程，角色和方法仍由代码与 Skill 决定。

### 三个 Agent 各带哪些 Skill

每个 Agent 有独立的 `SkillToolset`，只分配本角色需要的方法。下面五个 Skill 构成主研究团队：

| 顺序与角色 | 分配的 Skill | 方法负责什么 | 输出交给谁 |
| --- | --- | --- | --- |
| ① `technical` 技术分析师 | `data-quality` + `technical-trend` | 先检查证据模式、时效与缺失，再解释确定性指标，列出趋势反证 | `State["technical"]`，内容符合 `Analysis` |
| ② `catalyst` 事件分析师 | `news-catalyst` | 读取新闻标题与来源，区分事实、推断和未确认信息，说明事件证据缺口 | `State["catalyst"]`，内容符合 `Analysis` |
| ③ `review` 风险审查员 | `risk-review` + `decision-report` | 综合两份分析，检查冲突、引用与信心，按报告规则输出结论 | `State["review"]`，内容符合 `Decision`，再由程序校验 |

以下引文来自仓库中各 `SKILL.md` 的正文，均为原文节选：

**[data-quality](skills/data-quality/SKILL.md)：先确认数据能支持什么判断。**

> 先调用 read_evidence(context) 和 read_evidence(prices)。检查截至时间、数据模式和样本数；合成数据只验证流程，不形成真实预测。缺失值明确写入 missing_data。不要把缺失解读成中性。

**[technical-trend](skills/technical-trend/SKILL.md)：解释程序算好的指标。**

> 先调用 calculate_indicators。读取 references/method.md。根据 SMA20/60、5/20 日收益、RSI14 与 ATR14 解释趋势；只引用工具数值和 P1。给出反证和失效条件，不把多个相关指标当独立证据。

**[news-catalyst](skills/news-catalyst/SKILL.md)：约束新闻分析的证据来源。**

> 每个观点必须引用真实 N 编号；无新闻时明确缺失，不编造事件或来源。区分已报道事实、情景推断与未确认信息。

**[risk-review](skills/risk-review/SKILL.md)：审查两份分析中的冲突与不确定性。**

> 阅读两位分析师的结构化输出，检查引用、冲突、时效和反证。没有新闻不得高信心；证据不足为 HOLD、low；合成数据为 unknown 趋势。信心不是上涨概率。

**[decision-report](skills/decision-report/SKILL.md)：规定最终交付形式。**

> 读取 references/report-policy.md。综合已有技术分析和事件分析；输出严格符合 JSON schema 的最终建议。不要增加虚构证据编号；至少保留一个真实引用和一个失效条件。避免重复调用数据工具。

`technical-trend` 的详细判断规则位于 [references/method.md](skills/technical-trend/references/method.md)，`decision-report` 的报告约束位于 [references/report-policy.md](skills/decision-report/references/report-policy.md)。这些资料通过 `load_skill_resource` 按需读取。

### 一次研究的调用顺序

![股票研究从确定性输入、共享证据到三个顺序角色与最终校验](docs/images/architecture.svg)

1. **程序准备任务**：读取参数 → `load_bundle()` 取证据、计算指标和目标周 → 检查并筛选 Skill → 构造团队。
2. **technical**：加载 `data-quality`、`technical-trend` → 读取 `context`／`prices`、指标与方法资料 → 输出摘要、引用、反证和缺失信息。
3. **catalyst**：加载 `news-catalyst` → 读取 `news`／`context` → 输出事件分析。它读取同一份证据包，本项目没有把技术分析模板注入它的指令。
4. **review**：从指令中的 `{technical}`／`{catalyst}` 取得前两份输出 → 加载 `risk-review`、`decision-report` → 核对证据与报告规则 → 输出结构化建议。
5. **程序交付结果**：确认三个角色都加载了必需 Skill → `validate_decision()` 校验引用并执行降级规则 → 保存报告与执行记录。

`technical → catalyst → review` 由 Workflow 固定为顺序执行。角色内部的工具步骤由 Skill 与角色指令提出要求，模型可能在一次响应中发起多个工具调用，调用次数也会变化；运行后需要通过 Trace 核对实际过程。

<a id="setup"></a>

## 03 · 环境准备

需要 Python 3.11+ 和 [Google AI Studio API Key](https://aistudio.google.com/apikey)。以下命令在仓库根目录执行。

### 安装与配置

```bash
git clone https://github.com/ohmystack/adk-stock-research.git
cd adk-stock-research
bash scripts/setup.sh
.venv/bin/python scripts/configure.py
```

配置脚本会提示输入 Key，输入时不回显，并将其保存到本机的 `.env` 文件。已有 `.env` 可以复用；不要把 Key 提交到 Git，也不要放进发给模型的提示词（prompt）或截图。安装脚本会寻找 Python 3.11+，也可以通过 `WORKSHOP_PYTHON=/path/to/python3.12 bash scripts/setup.sh` 指定解释器，其中路径需要替换为本机 Python 的实际位置。

如果已经克隆过仓库，需要更新代码：

```bash
git status --short
git pull --ff-only
bash scripts/setup.sh
```

有未提交修改时，先在自己的分支保存，再更新。

<a id="research-tools"></a>

## 04 · 为研究方法准备函数与 Tool

**ADK 能加载 Skill 的方法说明，但方法需要的工具、数据和执行环境仍要由应用提供。** 例如，一份 Skill 要求搜索新闻或运行脚本，应用就必须提供相应能力；来自其他 Agent 的 Skill 还可能依赖原宿主的专用工具，不能直接照搬。

因此，本项目先补齐研究工具，再增加兼容性检查和运行前预检。这套做法和检查函数可以复用到自己的项目：先确认应用能支持哪些方法，再把可用的 Skill 交给 Agent。

### 把研究方法需要的能力做成 Tool

| 能力 | 本项目怎样提供 | 谁来调用 |
| --- | --- | --- |
| 准备证据与指标 | `load_bundle()`、`indicators()`、`target_week()` | 应用在研究前调用 |
| 读取证据与计算结果 | `read_evidence(section)`、`calculate_indicators()` | 模型在激活相关 Skill 后调用 |
| 发现、加载与读取方法 | ADK 的 `list_skills`、`load_skill`、`load_skill_resource` | 模型按发现模式与任务需要调用 |

[runtime.py](stock_research/runtime.py) 在 `build_team(bundle, ...)` 内定义两个业务工具，绑定本次研究的证据包。以下省略 docstring：

```python
def read_evidence(section: str) -> dict:
    if section == "prices":
        return {"source": "P1", "indicators": bundle["indicators"]}
    if section == "news":
        return {"news": bundle["news"], "warnings": bundle.get("warnings", [])}
    return {k: bundle[k] for k in [
        "ticker", "as_of", "target_week", "mode", "synthetic", "sources"
    ]}

def calculate_indicators() -> dict:
    return {"evidence_id": "P1", **bundle["indicators"]}
```

两个工具返回本次任务的证据与已计算的指标，无需模型重新计算，也无需再次传入 ticker。完整日线保存在 Python 证据包和 `evidence.json` 中。

Skill 用 `metadata.adk_additional_tools` 声明工具名称，应用在 `SkillToolset(additional_tools=[...])` 中注册实际 Python 函数。相关 Skill 激活后，ADK 才向模型开放这些工具。**Skill 说明怎样研究，Tool 让这些步骤能够执行。**

### doctor：先看环境与 Skill 是否匹配

`doctor` 是本项目的诊断命令，汇总 Python／ADK 版本、Key 是否存在，以及 `scan()` 返回的 Skill 检查结果。[cli.py](stock_research/cli.py) 的关键代码：

```python
result = {
    "python": sys.version.split()[0],
    "adk": m.version("google-adk"),
    "gemini_key_present": bool(os.getenv("GEMINI_API_KEY")),
    "skills": scan(),
    "note": "static capability checks; no model request",
}
```

它不联网、不打印 Key。运行后要阅读各 Skill 的 `status` 和 `reasons`：命令正常结束不代表所有方法都可用，找到 Key 也不代表 API 权限或额度已经验证。

### scan() 与 inspect_skill()：检查应用能否支持这些 Skill

[compatibility.py](stock_research/compatibility.py) 中的 `scan()` 遍历 `skills/`，逐个调用 `inspect_skill()`，保留每份 Skill 的检查结果：

```python
def scan(root: Path | None = None) -> list[dict]:
    root = root or ROOT / "skills"
    return [
        inspect_skill(p)
        for p in sorted(root.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]
```

`inspect_skill()` 用 ADK 原生解析器读取格式，再按本应用的能力检查以下要求；整个过程不调用模型或执行脚本。

| 检查什么 | 解决什么问题 |
| --- | --- |
| 文件结构与格式 | 文件夹名和 Skill 名是否一致，资源是否存在，路径和文件规模是否符合要求 |
| 工具与宿主依赖 | 所需工具是否已注册，是否依赖其他 Agent 的搜索、浏览器或专用语法 |
| 脚本执行能力 | Skill 包含脚本时，应用是否已配置执行器 |
| 内容哈希 | 记录本次检查的方法版本，便于比较修改前后 |

例如，用集合差找出 Skill 要求、但应用尚未注册的工具：

```python
TOOLS = {"read_evidence", "calculate_indicators"}
tools = meta.get("metadata", {}).get("adk_additional_tools", [])
missing = set(tools) - TOOLS
if missing:
    reasons.append("missing registered tools: " + ", ".join(sorted(missing)))
```

| 状态 | 含义与处理 |
| --- | --- |
| SUPPORTED | 通过已知检查，可以用于构造团队 |
| ADAPTABLE | 需要补齐工具、执行器，或修改宿主专用说明 |
| UNSUPPORTED | 当前环境无法支持，或文件／格式检查失败 |
| UNKNOWN | 预留状态，当前检查流程不返回它 |

例如，`extensions/needs-search` 依赖其他宿主的搜索工具，`vendor/skills/position-sizer` 需要默认团队尚未配置的脚本执行器，都会被标记为 `ADAPTABLE`。这些静态规则只能识别已知要求，实际使用仍需验证。

### accepted_skills()：只把通过检查的方法交给 ADK

`accepted_skills()` 根据检查结果筛选并解析 Skill：

```python
reports = scan()
skills = {
    r["skill"]: load_skill_from_dir(ROOT / "skills" / r["skill"])
    for r in reports
    if r["status"] == "SUPPORTED"
}
```

随后，`build_team()` 核对每个角色需要的 Skill 是否齐全；缺少必需方法就报错。第三方原件放在 `vendor/skills/`，不会因导入文件而自动加入团队。

### offline-check：用合成数据检查团队能否构造

`offline-check` 用合成 DEMO 数据检查指标与交易周计算，并实际构造三个 Agent 和 Workflow。它不调用 Gemini；数据处理或团队构造失败时会报错。

在自己的项目中，可以沿用“诊断 → 检查 → 筛选 → 构造”的方式，替换业务数据、角色和工具，并让 `TOOLS` 与实际注册的工具保持一致。详细规则见[实现参考](docs/implementation.md#预检与兼容性)。

<a id="agent-workflow"></a>

## 05 · 在代码中创建 Agent、Workflow 与运行入口

### 读取 Skill，并为每个角色创建 SkillToolset

经过前面的 `accepted_skills()`，程序拿到了通过检查的 `Skill` 对象。此时文件已经在本地解析完成，模型还没有读到方法正文；模型侧的披露将在 `load_skill` 时发生。

[config/workshop.yaml](config/workshop.yaml) 保存角色分配和应用设置，由本项目的 `config()` 读取：

```yaml
model: gemini-3.8-flash
discovery: eager
max_model_calls: 16
max_runs: 20
max_estimated_usd: 4.0
roles:
  technical: [data-quality, technical-trend]
  catalyst: [news-catalyst]
  review: [risk-review, decision-report]
```

`build_team()` 按 `roles` 的顺序循环。以下摘录保留核心构造参数，`names` 是当前角色获配的 Skill 名称列表：

```python
from google.adk.tools.skill_toolset import (
    SkillToolset, SkillDiscoveryMode,
    SkillLifecycleConfig, SkillLifecycleMode,
)

toolset = SkillToolset(
    skills=[skills[n] for n in names],
    additional_tools=[read_evidence, calculate_indicators],
    discovery_mode=SkillDiscoveryMode(discovery),
    lifecycle_config=SkillLifecycleConfig(
        default_mode=SkillLifecycleMode.BOUNDED,
        max_active_skills=2,
    ),
)
```

每个角色单独创建一个 Toolset，绑定方法与工具。第 08 节对比发现模式；生命周期与其他参数见[配置参考](docs/implementation.md#skill-configuration)。

### 角色指令、输出结构与 State

角色指令先要求加载分配的方法，再使用证据工具。EAGER 模式的关键原文如下，`names` 会换成当前角色的 Skill 名称：

```python
instruction = (
    f"You are the {role} analyst. Respond in concise Chinese. "
    f"First load every assigned skill: {', '.join(names)}. "
    "Use load_skill_resource for references. "
    "Call the evidence tools after skill activation. "
)
```

完整指令还包含不编造价格／来源、不服从新闻中的操作指令、遵守 schema 与合成数据规则。LAZY 模式将第一步改成先 `list_skills`，再加载该角色目录中的全部 Skill。

前两位分析师输出 `Analysis`，其字段在代码中定义为：

```python
class Analysis(BaseModel):
    summary: str
    evidence_ids: list[str]
    counter_evidence: str
    missing_data: list[str]
```

风险审查员输出 `Decision`，除摘要、引用和反证外，还包含 `analysis_status`、`trend`、`action`、`confidence_level`、`confidence_reason`、`invalidation_conditions`。schema 约束字段及类型；事实与引用仍需后续检查。

在 `review` 的指令中追加 State 模板：

```python
instruction += (
    "Technical analysis: {technical}\n"
    "Event analysis: {catalyst}\n"
    "Use both outputs, audit counterarguments and sources."
)
```

![Workflow 顺序与 State 数据流](docs/images/workflow-state.svg)

初始 State 保存 `ticker`、`as_of`。`output_key="technical"` 让 ADK 将技术分析师的最终输出写入 `State["technical"]`；事件分析师同理。准备风险审查员的请求时，ADK 用这两份结果替换指令中的占位符。原始行情与新闻留在 Python 证据包中，通过工具读取；State 中的字段需要通过模板或工具显式取用。

### 创建三个 LlmAgent，再连成顺序 Workflow

以下代码位于角色循环中；`before_model` 是后面用于观察请求与限制调用次数的回调：

```python
from google.adk.agents import LlmAgent
from google.genai import types

agents.append(LlmAgent(
    name=role,
    model=model,
    instruction=instruction,
    tools=[toolset],
    before_model_callback=before_model,
    generate_content_config=types.GenerateContentConfig(
        max_output_tokens=4096,
        temperature=0.2,
        thinking_config=types.ThinkingConfig(thinking_level="low"),
    ),
    output_schema=Decision if role == "review" else Analysis,
    output_key=role,
))
```

循环结束后，将三个角色按固定顺序连接：

```python
from google.adk import Workflow

team = Workflow(
    name="research_team",
    edges=[("START", *agents)],  # technical → catalyst → review
    timeout=180,
)
```

### CLI 用 Runner 启动，Web 在当前执行轮次运行同一 Workflow

CLI 的关键接线如下，省略预算、记录与清理逻辑：

```python
sessions = InMemorySessionService()
session = await sessions.create_session(
    app_name="workshop", user_id="group",
    state={"ticker": bundle["ticker"], "as_of": bundle["as_of"]},
)
runner = Runner(
    node=team, app_name="workshop", session_service=sessions,
    artifact_service=InMemoryArtifactService(),
)
async for event in runner.run_async(
    user_id="group", session_id=session.id,
    new_message=types.Content(role="user", parts=[types.Part(text=
        f"Analyze {bundle['ticker']} for {bundle['target_week']}. "
        f"as_of={bundle['as_of']}; mode={bundle['mode']}. "
        "Load your skills before analysis."
    )]),
    run_config=RunConfig(max_llm_calls=cfg["max_model_calls"]),
):
    record_event(event)
```

Web 由原生 Dev UI 启动入口节点 `workshop`，参数识别后将 `ticker`、`as_of` 写入当前 State，再执行 `await ctx.run_node(team)`。这样三个角色的模型、工具和 Workflow span 都归入同一次 UI 执行，能在当前会话中查看。

从收到一条消息到完成回复的整轮执行称为一次 **invocation**。一次 invocation 包含三个角色，也可以包含多次 Gemini 请求和工具调用。完整运行还会确认必需 Skill 已加载，并将 `State["review"]` 交给 `validate_decision()`，最后保存报告。

| 代码入口 | 主要职责 |
| --- | --- |
| [cli.py](stock_research/cli.py) / [web.py](stock_research/web.py) | 命令行与 Web 确定性参数解析、运行入口 |
| [runtime.py](stock_research/runtime.py) | Tool、角色指令、Agent／Workflow／Runner、校验、预算与留档 |
| [compatibility.py](stock_research/compatibility.py) | Skill 检查、过滤、哈希与隔离导入 |
| [data.py](stock_research/data.py) / [labs.py](stock_research/labs.py) | 数据准备；不调用模型的机制实验 |

完整接线与预检规则见[实现参考](docs/implementation.md)。

`requirements.lock` 固定依赖版本；`skills.lock.json` 保存交付时的方法内容哈希与来源快照，运行时不会自动强制比对它。实际研究会重新计算所加载 Skill 的哈希并写入结果，方法改动后需要时同步更新快照。

<a id="run-research"></a>

## 06 · 运行团队：CLI 与 Web UI

### 先完成两级预检

```bash
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli offline-check
```

预期结果：

```json
{
  "adk": "2.13.0",
  "gemini_key_present": true,
  "skills": [
    {"skill": "data-quality", "status": "SUPPORTED"},
    {"skill": "decision-report", "status": "SUPPORTED"}
  ]
}
```

上例是 `doctor` 的输出节选；请确认五个核心 Skill 均为 `SUPPORTED`，并已找到 Key。`offline-check` 应显示 `model_called: false`，且 `agents` 包含 `technical`、`catalyst`、`review`。两个命令均不调用模型；API 是否可用在实际研究中验证。

### 两种运行方式

命令行（CLI）与浏览器界面（Web UI）执行同一套研究流程，使用相同的数据准备和校验规则，并共用 `runs/budget.json` 中的预算记录。CLI 通过命令参数发起任务；Web UI 通过发送 prompt 发起任务，还能在界面中查看 ADK 的执行事件与 Trace。后续实验均列出两种入口，选择一种执行即可。

### 启动 ADK Web UI

```bash
.venv/bin/adk web web_agents --port 8000 --no-reload --no_use_local_storage
```

如果在 **Google Cloud Shell** 启动，使用下面的命令，多加 `--allow_origins` 以允许 Cloud Shell Web Preview 的来源：

```bash
.venv/bin/adk web web_agents --port 8000 --no-reload --no_use_local_storage \
  --allow_origins 'regex:https://.*.cloudshell.dev'
```

然后通过 Cloud Shell 的 **Web Preview → Preview on port 8000** 打开。这里补充启动参数；Cloud Shell 安装、API 访问与 Web Preview 的完整链路尚未彩排。

本机运行时打开 [http://127.0.0.1:8000](http://127.0.0.1:8000)。两种环境都在左上角选择 **research**。服务保持运行，后续实验在同一界面发送 prompt。首次出现使用数据收集提示时按个人偏好选择。

每次研究点击 **NEW SESSION**。这样可以隔离旧证据、角色输出和 Skill 激活状态，便于比较实验。修改 Skill 或角色 YAML 后，新研究会重新读取文件；修改 Python 代码后需要重启服务。

Web 入口用代码读取 prompt 中的 `mode`（数据模式）、`ticker`（股票代码）和 `discovery`（Skill 发现模式），据此启动研究；这个参数识别步骤不调用模型。发送 `help` 可以查看输入格式。[ADK Web UI 文档](https://adk.dev/runtime/web-interface/)

### CLI 入口

```bash
.venv/bin/python -m stock_research.cli --help
```

研究使用 `run --mode ... --ticker ... --discovery ...`；机制实验使用 `lab <名称>`，后面会给出完整命令。CLI 每次研究都会自动创建新会话，结束后在终端显示本次结果的保存目录。

### 固定输入，完成一次研究

**Web UI**：点击 **NEW SESSION**，发送：

```text
研究 mode=fixture ticker=DEMO discovery=eager，给出证据、反证、失效条件和信心。
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli run --mode fixture --ticker DEMO --discovery eager
```

这两种入口都会真实调用 Gemini。`mode=fixture` 表示使用仓库提供的固定合成数据，`DEMO` 是这份数据专用的示例代码。下面是最终 `decision.json` 中应出现的字段，其余字段省略：

```json
{
  "data_mode": "fixture",
  "analysis_status": "insufficient_data",
  "trend": "unknown",
  "action": "HOLD",
  "confidence_level": "low"
}
```

这些值由最终校验程序强制设置：数据不足（`insufficient_data`）、趋势未知（`unknown`）、持有／观望（`HOLD`）、低信心（`low`）。因此，这个实验要检查的是三个角色能否加载 Skill、使用工具并生成报告，不能用它检验真实股票判断的好坏。

Web 对话末尾会显示校验后的 Markdown 报告和保存位置 `runs/<运行编号>`；CLI 在终端显示保存位置。两种入口都会把报告与执行记录写入该目录。

Events 中的 `review` 输出是模型生成的原始结果，之后还要执行数据质量规则。核对最终结论时，请以对话末尾的报告或 `decision.json` 为准。

### 切换真实股票

**Web UI**：新建会话，发送：

```text
研究 mode=live ticker=GOOGL discovery=eager，结合价格和新闻给出下周研究报告，列出反证与失效条件。
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli run --mode live --ticker GOOGL --discovery eager
```

行情通过 yfinance 获取，新闻来自 Google News RSS。数据按股票代码和纽约日期缓存，同一天再次研究会复用缓存。需要重新获取证据时，先在终端执行：

```bash
.venv/bin/python -m stock_research.cli fetch --ticker GOOGL --refresh
```

然后在 Web UI 中新建会话，或重新执行 CLI 研究命令。比较 Skill 修改前后的结果时，应保留同一份证据包，不要在两次实验之间刷新数据；检查两次 `decision.json` 中的 `provenance.data_sha256` 是否相同，以确认研究输入一致。

报告按第 02 节的定义计算目标交易周与参考价格；可在 `evidence.json` 中核对 `as_of`、`target_week` 和指标。

当前流程只读取 RSS 标题、发布时间等信息，没有核验新闻全文。因此，最终结果会标记为 `degraded`（证据不完整），信心最高为 `medium`（中）。没有新闻时也会标记证据不完整；行情获取失败或新获取的日线未更新到最近一个已收盘交易日时，研究会报错。

<a id="trace-requests"></a>

## 07 · 在 Web UI 中查看 Gemini 的请求与返回

完成第 06 节的研究后，按下面的步骤操作。截图来自 ADK 2.13.0 中合成 DEMO 的真实运行，红圈标出需要点击的位置。

### 第一步：在 Traces 中找到模型调用

点击 **Traces**，在 `research_team` 下找到 `technical → catalyst → review`。选择某个角色下的 **generate_content gemini…** 记录，即可查看这一次模型调用；右侧时间条显示耗时。

![点击 Traces，再选择 technical 下的 generate_content 模型调用；真实截图局部加红圈](docs/images/trace-workflow-guide.svg)

### 第二步：打开 Request 和 Response

选中模型调用后，点击左侧 **Event ID** 链接，进入对应事件：

![点击左侧 Events 表格中的 Event ID 链接；真实截图局部加红圈](docs/images/trace-event-link-guide.svg)

再使用左侧两个箭头按钮：**① Request 看发给模型的内容，② Response 看模型返回的内容**。

![模型事件的 Request 与 Response 按钮：① 输入箭头，② 输出箭头；真实截图局部加红圈](docs/images/trace-request-guide.svg)

| 面板 | 展开什么 | 观察什么 |
| --- | --- | --- |
| Request | `system_instruction` | 角色要求、Skill 使用说明；EAGER 模式下还有 Skill 名称与描述列表 |
| Request | `user_messages → parts` | 用户消息、此前的工具调用与返回；加载后的 Skill 正文在 `tool_call_response → response → instructions` 中 |
| Response | `tool_call` 或文本内容 | 模型要求调用哪个工具、传入什么参数，或输出了什么分析 |

截图是加载 Skill 后的 Request：可以读到 `data-quality` 正文，其中 `{ticker}`、`{as_of}` 已替换为本次研究的值，这是 `metadata.adk_inject_state: true` 的作用。

### 第三步：对比加载前后，再核对工具结果

1. 打开 `technical` 的**第一次模型调用**，查看 Request 中的角色要求和 Skill 目录。
2. 找到 `load_skill` 之后的**下一次模型调用**，再次打开 Request，确认消息中已有方法正文；随后可以在调用树中看到 `read_evidence`、`calculate_indicators` 等业务工具。
3. 在 Response 中找到模型提出的工具调用，再到 **Events** 查看同名工具的返回。模型提出调用，ADK 执行工具，结果会进入下一次 Request。
4. 打开 `review` 的首次 Request，找到 `Technical analysis:` 和 `Event analysis:`，确认前两位分析师的结果已传给审查员。

Web Trace 展示的是 ADK 整理后的请求与响应，适合检查上下文和调用过程。最终交付结果看对话末尾的 Markdown 报告或 `decision.json`；中间的 review 输出还会经过程序校验。

### 保存报告与执行依据

本次研究的文件保存在 `runs/<运行编号>/`：

| 文件 | 内容 |
| --- | --- |
| `report.md` / `decision.json` | 校验后的报告与结构化结果 |
| `evidence.json` | 证据、来源、截至时间与指标 |
| `trace.json` | 角色、Skill／工具调用及返回 |
| `requests.json` | 每次模型请求的工具名与系统说明摘要 |
| `usage.json` | token、调用次数、耗时与费用估算 |

`requests.json` 只保存摘要。按本文命令启动的 Web Session／Trace 在重启后会清除，需要回看的研究记录保留在 `runs/` 中。

<a id="skill-parameters"></a>

## 08 · Discovery：对比 EAGER 与 LAZY

Discovery 决定**模型何时看到可用 Skill 的名称与描述列表**。它不改变本地文件的解析时机；两种模式都要通过 `load_skill` 读取方法正文。

| 对比点 | EAGER | LAZY |
| --- | --- | --- |
| 首次请求 | 系统说明中直接包含 Skill 列表 | 系统说明中没有这份列表 |
| 获取方法 | 阅读列表 → `load_skill` | 按需调用 `list_skills` → `load_skill` |
| 开销 | 列表从首次请求起就占用输入 token | 推迟提供列表；若仍需列出，会增加工具调用，列表也会进入上下文 |

ADK 默认 LAZY。本项目每个角色只有一到两个 Skill，而且都需要使用，所以默认 EAGER。LAZY 实验还通过角色指令要求先调用 `list_skills`；这是项目约定，ADK 允许直接加载已知名称的 Skill。

实验时只需改 Web prompt 的 `discovery=` 或 CLI 的 `--discovery`。未指定时读取 [config/workshop.yaml](config/workshop.yaml) 的 `discovery`，最终传给 `SkillToolset(discovery_mode=...)`。

### 先看机制：不调用模型

在 Web UI 发送：

```text
lab discovery
```

或运行 CLI：

```bash
.venv/bin/python -m stock_research.cli lab discovery
```

实验用两种模式准备请求，**不发送给 Gemini**。在对话结果或 `runs/lab-discovery.json` 中查看 `modes`：EAGER 的 `system_instruction` 有 Skill 列表，`tools` 没有 `list_skills`；LAZY 正好相反。

### 再看实际调用：只改变发现模式

分别新建两个 Web 会话，依次发送下面两条 prompt；等第一次研究结束后，再运行第二次：

```text
研究 mode=fixture ticker=DEMO discovery=eager，给出证据、反证、失效条件和信心。
```

```text
研究 mode=fixture ticker=DEMO discovery=lazy，给出证据、反证、失效条件和信心。
```

CLI 对应：

```bash
.venv/bin/python -m stock_research.cli run --mode fixture --ticker DEMO --discovery eager
.venv/bin/python -m stock_research.cli run --mode fixture --ticker DEMO --discovery lazy
```

在 LAZY 会话中点击 **Traces**，找到角色下的 **list_skills**，再看后面的 `load_skill`：

![点击 Traces，查看 LAZY 模式中的 list_skills 记录；真实截图局部加红圈](docs/images/trace-lazy-guide.svg)

按第 07 节的方法，比较两个会话的首次 Request；再用各自的 `usage.json` 比较 token 与耗时。实际开销以运行结果为准，LAZY 不一定更省。

Skill 多到列表难以浏览时，可以进一步用 Registry 搜索少量相关方法，见下一节。其他[配置归属](docs/implementation.md#skill-configuration)与[生命周期实验](docs/implementation.md#skill-lifecycle)放在实现参考中，供扩展时查阅。

<a id="skill-registry"></a>

## 09 · Registry：从本地关键词搜索到 Google Cloud

### 本地 Registry：实现 search → load

当 Skill 很多时，可以先搜索相关方法，而不必把完整列表交给模型。ADK 的 `SkillRegistry` 为此提供两个接口：按查询返回候选列表，再按名称取得某个完整 Skill。本实验在 [labs.py](stock_research/labs.py) 中自定义 `LocalRegistry`，用本地字典 `skills` 中的五个已检查 Skill 实现这两个接口。`LocalRegistry` 是项目类名，ADK 提供的基类是 `SkillRegistry`：

```python
from google.adk.skills.skill_registry import SkillRegistry

class LocalRegistry(SkillRegistry):
    async def search_skills(self, *, query):
        return [
            s.frontmatter for s in skills.values()
            if query.lower() in (s.name + " " + s.description).lower()
        ][:3]

    async def get_skill(self, *, name):
        return skills[name]
```

这里的 `search_skills()` 在名称与描述中匹配查询字符串，最多返回三个 Skill 的名称、描述等 YAML 信息，供选择方法；`get_skill()` 按名称返回完整 Skill。数据来自本地内存字典，未连接向量数据库或外部托管服务。

将 Registry 配置给 `SkillToolset` 后，可以通过 ADK 工具完成搜索和加载：

```python
ts = SkillToolset(registry=LocalRegistry())
ctx = await context(agent)
result["search"] = await call(ts, ctx, "search_skills", {"query": "risk"})
result["loaded"] = await call(ts, ctx, "load_skill", {"skill_name": "risk-review"})
```

`call()` 是项目按名称执行 ADK 工具的[辅助函数](docs/implementation.md#lab-helpers)。第一步，ADK 的 `search_skills` 工具调用 Registry 的搜索方法，返回匹配 `risk` 的候选信息。第二步，`load_skill` 调用 Registry 的 `get_skill()` 取得 `risk-review`，把正文返回给调用方并激活这个 Skill。实验代码固定指定查询词和加载名称，不调用模型，也没有继续执行业务分析。

**Web UI prompt**：

```text
lab registry
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli lab registry
```

查看对话结果或 `runs/lab-registry.json`：`search` 中应出现 `risk-review` 的名称和描述，`loaded` 中应包含它的方法正文。由此可以核对，搜索阶段返回候选信息，加载阶段才返回正文。

EAGER／LAZY 决定何时向模型提供本地 Skill 列表；Registry 提供按查询筛选候选的能力。后者适合先缩小选择范围，再加载所需的方法。

### Google Cloud：用 GCPSkillRegistry 共享与管理 Skill

团队共享方法时，可以把 Skill 放进 **Google Cloud Agent Registry 的 Skills**，由云端管理来源、版本与访问权限，应用通过 `GCPSkillRegistry` 搜索和加载。这里介绍接入方式，仓库的研究团队仍使用本地 `skills/`，不要求开通云端服务。

| 步骤 | 平台或应用需要准备什么 | 与本地实验的对应关系 |
| --- | --- | --- |
| ① 发布方法 | 将 `SKILL.md`、`references/`、可选脚本打成 ZIP；ZIP 根目录直接包含 `SKILL.md`，在 Agent Registry 的 Skills 中注册，设置默认 revision 并激活 | 本地实验直接从文件夹加载 |
| ② 配置访问 | 启用 `agentregistry.googleapis.com`；运行身份具备读取权限，例如 `roles/agentregistry.viewer`；配置 ADC（Application Default Credentials） | 本地字典无需云端身份 |
| ③ 创建来源适配器 | 指定 Google Cloud project 与 location，创建 `GCPSkillRegistry` | 替换项目自定义的 `LocalRegistry()` |
| ④ 交给 Agent | 将 Registry 传给 `SkillToolset(registry=...)`，通过 `LlmAgent(tools=[toolset], ...)` 提供给模型 | 继续使用 `search_skills → load_skill` |

注册、版本维护所需权限与应用只读身份可以分别配置。具体步骤见 Google Cloud 官方的[设置 Agent Registry](https://docs.cloud.google.com/agent-registry/setup)、[注册 Skill](https://docs.cloud.google.com/agent-registry/register-skills)、[版本与下载权限](https://docs.cloud.google.com/agent-registry/manage-skill-revisions)和[Skills 架构](https://docs.cloud.google.com/agent-registry/skills-architecture)。

ADK 2.13.0 的最小接法如下，仅展示如何替换 Skill 来源：

```python
from google.adk.integrations.skill_registry import GCPSkillRegistry
from google.adk.tools.skill_toolset import SkillToolset

registry = GCPSkillRegistry(
    project_id="YOUR_PROJECT_ID",
    location="global",  # 与云端注册位置一致
)
toolset = SkillToolset(registry=registry)
```

`skills=[...]` 与 `registry=...` 也可以同时配置：加载时优先匹配本地 Skill；Registry 搜索结果会过滤本地同名项。

也可通过 `GOOGLE_CLOUD_PROJECT`、`GOOGLE_CLOUD_LOCATION` 提供默认值。本地开发常用 `gcloud auth application-default login` 准备 ADC；Cloud Shell 或部署环境使用其运行身份。云端身份与本项目 `.env` 中的 Gemini API Key 分别用于 Registry 访问和模型调用，接入 Registry 不要求更换 Gemini Developer API 后端。

模型调用 `search_skills` 得到候选信息，选择后通过 `load_skill` 请求完整方法。加载时使用搜索结果返回的注册资源 ID；自定义资源 ID 可能带 `private-` 前缀，不应假设它等于 `SKILL.md` 的 `name`。当前 `GCPSkillRegistry` 读取云端资源的默认 revision，再下载并解析 Skill 包，构造参数没有用于固定任意 revision 的 `revision_id`。

进入真实研究应用时，还要为 Toolset 配置方法所需的 `additional_tools`、脚本执行环境与生命周期，并复用应用自己的兼容性检查。Registry 提供方法来源，不会替宿主实现业务工具。本地 lab 的静态检查规则也不会自动套用到所有远程包。

本节按仓库固定的 ADK 2.13.0 接口与 Agent Registry 文档介绍；该版本实现连接 `agentregistry.googleapis.com`。旧版 ADK 集成说明中的 Vertex AI Skill Registry 用语和接口可能不同，升级时需要核对 SDK 与云端文档。本项目未配置或实测云 Registry，也没有自动回退本地的实现。

<a id="extend-skills"></a>

## 10 · 修改研究方法与扩展 Skill

### 修改 Skill：固定证据，比较结果

先按第 06 节完成一次真实股票研究，保留它的 `runs/<运行编号>` 目录，作为修改前的基线。再只修改 Skill 中的方法，使用同一股票、同一份证据、同一模型和同一发现模式重新研究。这样才能判断报告中的哪些变化可能来自方法改动。

#### 保守风险审查

编辑 [risk-review/SKILL.md](skills/risk-review/SKILL.md)，在开头 YAML 区块之后的正文中加入下面的规则，保留原有名称、描述和工具声明：

```text
若技术面与事件面冲突，优先 HOLD，并明确列出冲突。
若只有新闻标题，没有核验全文，信心不得超过中。
即使趋势向上，也必须说明追高风险与失效条件。
```

保存文件后，先检查修改是否破坏格式或团队构造：

```bash
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli offline-check
```

下面沿用第 06 节的 GOOGL／EAGER 基线。如果基线使用了其他股票或发现模式，请保持原参数。

**Web UI**：新建会话，重新发送基线 prompt：

```text
研究 mode=live ticker=GOOGL discovery=eager，结合价格和新闻给出下周研究报告，列出反证与失效条件。
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli run --mode live --ticker GOOGL --discovery eager
```

比较两次运行时，先确认 `decision.json` 中的 `provenance.data_sha256` 相同，保证证据一致；再检查 `skills_inspection` 中 `risk-review` 的 `sha256` 已变化，确认新方法被读取。然后在 `trace.json` 中确认风险审查员加载了 `risk-review`，并阅读报告如何处理冲突、解释证据、列出反证和失效条件。

BUY／SELL／HOLD 可能保持不变。是否采用了新规则，要结合报告的论证和执行记录判断；模型本身也可能产生不同表述，不能把所有文字变化都归因于 Skill 修改。

#### 其他方法改造

| 改造 | 编辑位置 | 观察重点 |
| --- | --- | --- |
| 调整趋势判断规则 | [technical-trend/references/method.md](skills/technical-trend/references/method.md) | 是否按新规则解释 20／60 日均线（SMA）、近期收益、相对强弱指标（RSI）与平均真实波幅（ATR），并给出对应的风险和失效条件 |
| 证据审查 | [news-catalyst/SKILL.md](skills/news-catalyst/SKILL.md) | 区分标题、评论与已核验事实，明确缺失数据 |
| 添加新方法 | 复制 Skill 文件夹，更新文件夹名、YAML 的 `name` 和 `description`，并把新名称加入 `config/workshop.yaml` 中某个角色的 Skill 列表 | 新 Skill 通过检查；执行记录中出现它的加载；报告采用了其中的规则 |

每次改造后，都先执行上面的两个检查命令，再在 Web UI 新建会话并发送基线 prompt，或重跑对应 CLI 命令。若新规则需要当前工具没有提供的数据，应补充数据工具或在报告中说明缺失，不能要求模型编造数值。

当前每个 Agent 最多同时激活两个 BOUNDED Skill。若给同一角色分配三个或更多 Skill，需要相应提高数量上限，或设计明确的加载、卸载顺序，否则后加载的方法可能淘汰仍需使用的方法。若方法需要访问新的外部数据系统，还需要在应用中实现并注册相应工具。

### 第三方 Skill：导入与适配

项目保留了固定版本的第三方 [Position Sizer](https://github.com/tradermonty/claude-trading-skills)，采用 MIT 许可证。原件位于 `vendor/skills/position-sizer`，用于根据账户资金和风险限制计算可买入股数。先检查并导入原件：

```bash
.venv/bin/python -m stock_research.cli import-skill vendor/skills/position-sizer
```

预期结果中的 `status: ADAPTABLE` 表示需要适配，`activated: false` 表示未加入研究团队。项目已包含同一份原件，因此导入时还会显示 `already_present: true`；同内容重复导入不会覆盖文件。默认股票研究团队没有脚本执行器，需要另外配置才能运行其中的计算脚本。

`import-skill` 会检查文件，并将允许导入的内容保存在 `vendor/skills/` 中，供后续审查和适配；它不会自动改写 Skill 或执行脚本。仓库另外提供了人工适配版 `extensions/position-sizer-adk`，保留计算脚本、参考资料与 MIT 许可证，将原宿主的操作说明改成 ADK 工具步骤：用 `load_skill_resource` 读取方法资料，用 `run_skill_script` 执行计算脚本，明确传入账户资金、入场价、止损价和风险比例。

`lab sizing` 为这个适配版补齐执行环境，并用固定参数运行脚本：

```python
script_skill = load_skill_from_dir(ROOT / "extensions/position-sizer-adk")
service = InMemoryArtifactService()
ts = SkillToolset(
    skills=[script_skill],
    code_executor=UnsafeLocalCodeExecutor(),
    save_output_artifacts=True,
)
ctx = await context(agent, artifacts=service)
await call(ts, ctx, "load_skill", {"skill_name": "position-sizer-adk"})
result["execution_result"] = await call(ts, ctx, "run_skill_script", {
    "skill_name": "position-sizer-adk",
    "file_path": "scripts/position_sizer.py",
    "args": ["--account-size", "10000", "--entry", "100",
             "--stop", "95", "--risk-pct", "1"],
})
```

`code_executor` 提供脚本执行能力；`save_output_artifacts=True` 让 ADK 将脚本生成的文件保存到上下文配置的 ArtifactService（产物存储服务）中，后续可以通过服务接口读取。这个实验既适配了方法说明，也配置了执行器和产物服务，因此能完成从执行到读回文件的整个过程。此处使用的 `UnsafeLocalCodeExecutor` 直接在本地运行代码，不提供沙箱；实验只加载仓库内的适配脚本。

**Web UI prompt**：

```text
lab sizing
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli lab sizing
```

在对话结果或 `runs/lab-sizing.json` 的 `saved` 中，查看从 ArtifactService 读回的 JSON 和 Markdown 文件内容。示例使用合成账户：资金 10,000 美元、单笔风险比例 1%、入场价 100 美元、止损价 95 美元。按固定风险比例法计算，应得到 **20 股、总风险 100 美元**：

```text
风险预算 = 10,000 × 1% = 100
每股风险 = 入场价 100 − 止损价 95 = 5
股数 = 风险预算 100 ÷ 每股风险 5 = 20
仓位金额 = 20 × 100 = 2,000
```

原脚本还包含基于波动幅度的 ATR 方法、Kelly 方法，以及仓位和行业敞口限制；这些不在本实验的演示范围内。本实验只验证固定风险比例计算和文件保存，不调用模型，也不提供趋势结论或连接券商。

### 可选：通过 npx 安装

如果希望体验 Skill 安装器，可以另用下面的命令。需要 Node.js 22.20+；前面的 Python 导入和脚本实验不依赖这一步：

```bash
npx --yes skills@1.7.4 add ./vendor/skills/position-sizer --agent universal --copy --yes
.venv/bin/python -m stock_research.cli import-skill .agents/skills/position-sizer
```

第一条命令把第三方原件复制到 `.agents/skills/`，第二条命令通过项目的检查流程将它导入 `vendor/skills/`。安装器负责放置文件；ADK 应用仍需完成兼容性检查、团队配置和脚本执行器配置。

上面的 `lab sizing` 始终运行 `extensions/position-sizer-adk` 中的适配版。即使重新安装并导入原件，这个实验和默认研究团队使用的 Skill 也不会改变。

### 脚本生成的文件如何保存和读回

`lab artifacts` 沿用 `lab sizing` 的执行器与 ArtifactService 配置，将 Skill 换为 `extensions/metrics-export`。它的脚本只写入一个内容固定的合成示例文件，便于检查“执行脚本 → 保存文件 → 读回内容”这一过程：

```python
Path("metrics.json").write_text(json.dumps({
    "example": True, "risk_budget": 100, "stop_distance": 5, "shares": 20,
}))
```

先加载 Skill，再执行脚本。脚本生成文件后，ADK 在启用 `save_output_artifacts` 时将其保存为 Artifact：

```python
await call(ts, ctx, "load_skill", {"skill_name": "metrics-export"})
result["execution_result"] = await call(ts, ctx, "run_skill_script", {
    "skill_name": "metrics-export", "file_path": "scripts/export.py",
})
```

实验随后列出 ArtifactService 中的文件，逐个读回内容；`lab sizing` 使用相同的读回步骤：

```python
scope = {"app_name": "lab", "user_id": "group", "session_id": ctx.session.id}
names = await service.list_artifact_keys(**scope)
result["saved"] = {}
for filename in names:
    item = await service.load_artifact(**scope, filename=filename)
    result["saved"][filename] = item.inline_data.data.decode()
```

`scope` 指定应用名、用户编号和会话编号，用来定位本次实验保存的文件。示例生成的文件内容直接保存在 `inline_data` 中，因此可以解码为文本；这里省略了其他内容类型的处理分支。最终的 `saved` 字典包含从服务中实际读回的文件内容，可用于确认文件已成功保存。

**Web UI prompt**：

```text
lab artifacts
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli lab artifacts
```

查看对话结果或 `runs/lab-artifacts.json`：`saved` 字典中的 `metrics.json` 内容应包含 `risk_budget: 100`、`stop_distance: 5`、`shares: 20`。这些值由上面的示例脚本固定写入，用于验证文件保存和读取。

这三个接口各负责一步：`load_skill_resource` 读取 Skill 已有的资源文件，`run_skill_script` 执行脚本，ArtifactService 保存脚本生成的文件。实验使用内存产物服务，进程结束后其中的文件不会保留；需要回看时，读取实验最后写到磁盘上的 `runs/lab-artifacts.json`。主研究流程的报告由应用直接写入 `runs/`，使用的是另一条保存路径。

<a id="cost-and-errors"></a>

## 11 · 成本、失败与实验记录

### 信心与预算

报告中的信心等级表示模型对证据充分程度和一致性的判断，并受程序的数据质量规则约束；它没有经过统计校准，不能换算成投资胜率。三个 Agent 使用同一模型、共享证据，即使结论一致，也不能视为三份相互独立的验证。阅读报告时仍需检查来源、反证和失效条件。

兼容性检查和五个 `lab` 实验都不调用模型。完整研究默认限制如下：

- 一次研究中，三个角色合计最多发起 16 次模型请求。模型每次读取工具结果后继续判断，也会占用一次请求。
- 同一仓库目录中的 CLI／Web 研究共用 `runs/budget.json`，最多运行 20 次，累计费用估算达到 4 美元后停止新任务；运行中达到费用阈值也会停止后续模型步骤。
- 每次开始运行前先在账本中登记一次，因此后续执行失败也会占用一次研究次数。失败时会尽可能保存已发生的调用和用量。

组内应等待前一次研究结束后再发起下一次。其他仓库目录或其他程序产生的费用不会自动记入这份账本。

费用估算使用运行代码中固定的费率：输入每百万 token 0.75 美元，输出每百万 token 3.75 美元，输出用量包含模型思考（thinking）token。这是应用的预算估算，实际收费以账户账单为准，免费层可能不产生费用。已经发送的请求无法由应用撤销，因此这个阈值不能保证账单绝不超过 4 美元。查询官方计费、额度与使用条件，可查看 [Gemini 价格](https://ai.google.dev/gemini-api/docs/pricing)、[配额](https://ai.google.dev/gemini-api/docs/rate-limits)和[账单说明](https://ai.google.dev/gemini-api/docs/billing)。

### 常见问题

| 现象 | 检查与处理 |
| --- | --- |
| Key 未配置，或 API 返回 401／403 | 先看 `doctor` 的 `gemini_key_present`；若已找到 Key，再检查 Key 是否有效、模型访问权限、地区限制，以及是否使用本项目要求的 Gemini Developer API |
| API 返回 429 | 查看错误中的额度或限流说明，等待相应配额恢复；组内一次只运行一个研究任务，避免连续重试 |
| UI 提示本会话已运行过研究 | 点击 NEW SESSION，再发送研究 prompt |
| UI 看不到 research | 确认在仓库根目录执行 `adk web web_agents ...` |
| Trace 暂无内容 | 等研究结束后点击刷新；若已重启服务，请改看 `runs/` 中保存的执行记录，内存中的 Trace 已清除 |
| 模型未加载必需 Skill，或最终输出字段不符合要求 | 查看本次运行目录中的 `failure.json`、`requests.json` 和 `trace.json`，定位缺少的加载步骤或字段错误；应用会将该次运行标记为失败 |
| 行情获取失败或缺少新闻 | 查看具体错误与数据警告；新闻缺失会降低结果质量，行情失败则停止研究。需要练习执行流程时，明确使用 `mode=fixture` 和 `ticker=DEMO` |
| Skill 未通过兼容性检查 | 查看 `doctor` 中对应 Skill 的 `status` 和 `reasons`，按原因修改后重新检查 |
| 提示 `runs/.running` 锁已存在 | 先确认组内是否有研究仍在执行；只有确定任务已结束、锁只是异常退出后的残留时，才清理这个文件 |

### 实验留档

保留修改前后的运行目录、Skill 文件差异和关键 Trace 截图。记录**改了什么、为什么改、执行记录是否表明新方法被使用、结果还有哪些局限**。比较之前先核对数据哈希；若两次使用了不同日期的市场数据，就无法单凭报告变化判断 Skill 修改的效果。

`.env`、实际行情缓存、个人运行记录和 `.adk/` 均不提交 Git。准备展示材料时，选取报告和支撑结论的必要执行记录，并检查截图中是否含有 Key。第三方来源与图片出处见[来源及许可](THIRD_PARTY_NOTICES.md)。
