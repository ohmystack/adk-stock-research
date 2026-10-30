# 使用 Google ADK Skills 构建股票研究多 Agent 系统

**Google ADK Python × Gemini · 美股下周研究实践**

本项目用三个 Agent 和五个 Skill，完成从证据准备、价格与新闻分析到风险审查的美股下周研究，生成带来源、反证、信心与失效条件的报告。项目只做研究，不执行交易。

全文沿着一次研究展开：先明确输入与分工，准备工具，在代码中创建团队并运行，再通过 Web Trace 检查 ADK 怎样组织 Skill、请求 Gemini 和处理返回。最后调整参数、接触 Registry，并修改研究方法做对照。

[ADK 与 Skill](#adk-and-skill) · [任务设计与分工](#research-design) · [环境准备](#setup) · [函数与 Tool](#research-tools) · [Agent 与 Workflow](#agent-workflow) · [运行](#run-research) · [Trace 请求与返回](#trace-requests) · [参数与机制](#skill-parameters) · [Registry](#skill-registry) · [方法改造与扩展](#extend-skills) · [成本与排错](#cost-and-errors)

<a id="adk-and-skill"></a>

## 01 · ADK 与 Skill

### 从模型回答到 Agent 应用

**Gemini 负责理解与判断，ADK 组织应用的执行过程。** 股票研究还需要获取数据、调用计算工具、保存中间结果、交给其他角色审查，并形成最终报告。这些步骤由应用连接起来。

ADK（Agent Development Kit）是用于构建 Agent 应用的开源框架，支持工具、多 Agent 编排、会话、状态与执行追踪。本项目使用 Python、Gemini 和 ADK 原生 Workflow。[官方介绍](https://adk.dev/get-started/about/)

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

### 程序函数、业务工具与 Skill 工具分别负责什么

| 层次 | 本项目准备的能力 | 谁来调用 |
| --- | --- | --- |
| 数据准备函数 | `load_bundle()`、`indicators()`、`target_week()`：取数、校验日线、计算指标与交易周 | 应用在研究前直接调用 |
| 预检与业务控制函数 | `scan()`、`inspect_skill()`、`accepted_skills()`、`build_team()`、`validate_decision()` | 应用按固定流程调用 |
| 供模型使用的业务 Tool | `read_evidence(section)`、`calculate_indicators()`：读取本次任务的证据与计算结果 | 激活相关 Skill 后，模型通过函数调用使用 |
| ADK 提供的 Skill Tool | `load_skill`、`load_skill_resource`；LAZY 时的 `list_skills`；启用生命周期后的 `unload_skill` | 模型发现、加载、读取与卸载方法 |

主研究团队只给模型提供两个业务工具。[runtime.py](stock_research/runtime.py) 在 `build_team(bundle, ...)` 内定义它们，通过 Python 闭包绑定本次证据包。下面保留实际返回字段，省略 docstring：

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

`read_evidence("prices")` 返回指标与样本摘要；完整原始日线保留在 Python 的 `bundle["prices"]` 和运行产物 `evidence.json` 中。`calculate_indicators()` 返回已经算好的数值，每次工具调用无需模型重新计算。两个工具没有 `ticker` 参数，因为它们已经绑定本次研究对象。

Skill 的 `metadata.adk_additional_tools` 写的是工具名称；宿主还要在 `SkillToolset(additional_tools=[...])` 中注册实际函数。ADK 再根据激活的 Skill，把相应函数声明提供给 Gemini。**Skill 规定怎样研究，Python Tool 提供可执行的数据访问能力。**


### 加载 Skill 前，应用先检查什么

一次研究按下面的顺序执行。应用先准备证据、检查 Skill，再让模型使用通过检查的方法：

```text
CLI / Web prompt
  → load_bundle()：准备证据、用代码计算指标、确定下周交易日
  → scan() / inspect_skill()：检查 Skill 文件及其对工具和环境的要求
  → accepted_skills()：只保留通过检查的 Skill
  → build_team()：为各角色配置 Skill、工具和输出字段要求
  → Workflow：technical → catalyst → review
  → validate_decision()：校验引用、执行数据质量规则
  → runs/：保存报告、证据、Skill 内容哈希、请求摘要与用量
```

ADK 提供 Skill 格式解析、`SkillToolset`、会话与执行事件。下面的 `doctor`、`offline-check`、`scan()` 和加载规则由本项目实现，用于检查本应用能否支持这些 Skill。例如，一份 Skill 即使格式正确，也可能要求应用尚未提供的搜索工具或脚本执行器。

| 层次 | 实现位置 | 解决的问题 |
| --- | --- | --- |
| 环境诊断 `doctor` | [cli.py](stock_research/cli.py) | 解释本机环境、Key 是否存在、各方法为什么能用或不能用 |
| Skill 扫描 `scan()` | [compatibility.py](stock_research/compatibility.py) | 在模型看到 Skill 列表前逐项检查，并记录通过或拒绝的原因 |
| 加载筛选 `accepted_skills()` | [compatibility.py](stock_research/compatibility.py) | 只将通过检查的 Skill 交给 ADK；必需 Skill 缺失时明确报错 |
| 离线构造检查 `offline-check` | [cli.py](stock_research/cli.py) | 不调用模型，检查证据、指标、日历和团队能否正确构造 |
| 结果约束与留档 | [runtime.py](stock_research/runtime.py) | 校验引用与数据质量，保存执行依据并限制消耗 |

### doctor：把环境和兼容性变成可读报告

`doctor` 读取 Python／ADK 版本、判断 `.env` 加载后是否存在 Key，并调用 `scan()` 汇总方法检查结果。它不打印 Key，也不联网验证 Key 的权限、模型额度或地区可用性。

[cli.py](stock_research/cli.py) 的关键分支：

```python
result = {
    "python": sys.version.split()[0],
    "adk": m.version("google-adk"),
    "gemini_key_present": bool(os.getenv("GEMINI_API_KEY")),
    "skills": scan(),
    "note": "static capability checks; no model request",
}
```

这份报告帮助定位环境和待检查 Skill 的问题。即使缺少 Key 或发现不兼容的 Skill，命令也可以正常结束并输出 JSON。因此要查看报告中的字段：**退出码为 0 不代表所有 Skill 都可用，`gemini_key_present: true` 只表示找到了 Key，不表示 API 已通过验证**。真正发起研究时，应用还会检查必需 Skill 是否齐全，并验证模型能否按要求完成任务。

### scan() 与 inspect_skill()：在模型使用 Skill 前检查兼容性

`scan()` 默认扫描仓库的 `skills/` 文件夹，将每个非隐藏的直接子文件夹视为一个待检查的 Skill。它也支持传入其他扫描路径，但不会自动搜索电脑上其他已安装的 Skill。每个 Skill 独立检查，一个文件夹检查失败后仍会继续检查其他文件夹：

```python
def scan(root: Path | None = None) -> list[dict]:
    root = root or ROOT / "skills"
    return [
        inspect_skill(p)
        for p in sorted(root.iterdir())
        if p.is_dir() and not p.name.startswith(".")
    ]
```

`inspect_skill()` 检查文件和格式，并调用当前安装的 ADK 所提供的 `load_skill_from_dir()` 解析 Skill；随后检查 Skill 要求的工具和执行环境是否与本项目匹配。整个过程不调用模型，也不执行 Skill 中的操作或脚本。

| 检查 | 做法 | 为什么需要 |
| --- | --- | --- |
| 目录与内容 | 文件和子目录合计超过 250 项，或文件总大小超过 2,000,000 字节（约 2 MB）时拒绝；拒绝符号链接；根据相对路径与文件内容计算 SHA-256 哈希 | 控制检查规模，并用内容哈希标识本次使用的 Skill 版本 |
| Skill 格式 | 检查文件是否以 YAML 区块开头，调用 ADK 解析器，核对文件夹名与 YAML 的 `name` 是否一致 | 确保 Skill 符合 ADK 格式，且名称与存放位置对应 |
| 真实工具 | 将 `adk_additional_tools` 与 `TOOLS` 集合比较 | 方法要求的工具必须已在宿主注册 |
| 对特定宿主的依赖 | 检查 `WebSearch`／`Bash` 等专用工具名、Shell 预处理语法、专用权限字段，以及浏览器、连接器和安装要求 | 找出依赖其他应用能力、不能直接在本项目中使用的说明 |
| 脚本与资源 | Skill 含脚本、而当前未配置执行器时，标记为待适配；检查正文中识别到的资源路径是否存在、是否超出 Skill 文件夹 | 提前发现“有脚本但不能执行”或参考资料缺失 |
| 检查结论 | 返回状态、理由、内容哈希，并注明 `static only`（仅做静态检查） | 说明为什么接受或跳过某个 Skill，避免让模型反复试错 |

例如，下面用集合差找出 Skill 声明需要、但宿主尚未注册的工具：

```python
TOOLS = {"read_evidence", "calculate_indicators"}
tools = meta.get("metadata", {}).get("adk_additional_tools", [])
missing = set(tools) - TOOLS
if missing:
    reasons.append("missing registered tools: " + ", ".join(sorted(missing)))
```

用 `inspect_skill()` 检查扩展样例时，`extensions/needs-search` 因包含其他宿主的专用工具说明，结果为 `ADAPTABLE`；需要桌面／券商登录的样例为 `UNSUPPORTED`。`vendor/skills/position-sizer` 含有脚本，而默认研究团队没有脚本执行器，因此也需要适配。文件安装完成后，还需要通过这些检查才能判断当前应用能否使用它。

| 状态 | 后续处理 |
| --- | --- |
| SUPPORTED（通过检查） | 格式与已知能力要求匹配，可以用于构造团队；真实执行仍可能失败 |
| ADAPTABLE（需要适配） | 根据检查理由，补齐工具或脚本执行器，或修改宿主专用说明，再重新检查 |
| UNSUPPORTED（当前不可用） | 当前环境无法支持，或文件／格式检查失败，跳过该 Skill |
| UNKNOWN（尚未确定） | 为后续扩展预留；当前检查流程返回上面三种结果，没有调用模型进一步审查的步骤 |

这些规则主要依靠格式、工具名和文本模式做静态检查，可能误判，也可能漏掉自然语言中的要求。`SUPPORTED` 表示通过了已知检查；仍需阅读第三方内容，并在实际执行中确认它是否按预期工作。

### accepted_skills()：报告之后还要真正限制加载

生成检查报告后，应用还要据此决定把哪些 Skill 交给 ADK。`accepted_skills()` 只解析并返回状态为 `SUPPORTED` 的 Skill；此时尚未向模型提供方法正文：

```python
reports = scan()
skills = {
    r["skill"]: load_skill_from_dir(ROOT / "skills" / r["skill"])
    for r in reports
    if r["status"] == "SUPPORTED"
}
```

随后，`build_team()` 核对角色配置 `roles` 中要求的 Skill 是否全部存在。只要缺少一个必需 Skill，就会报错并停止研究。导入的第三方原件保存在 `vendor/skills/`，默认扫描范围则是 `skills/`，所以导入文件不会自动将其加入研究团队。

### offline-check：不调用模型，检查数据准备与团队构造

`offline-check` 使用合成 DEMO，调用真实的数据准备和团队构造函数：

```python
bundle = load_bundle("fixture", "DEMO")
team, toolsets, reports, model = build_team(
    bundle, config().get("discovery", "eager")
)
result = {
    "model_called": False,
    "agents": [a.name for a in team.edges[0][1:]],
    "indicators": bundle["indicators"],
    "target_week": bundle["target_week"],
    "skills": reports,
}
# 检查完成后逐个 await toolset.close()
```

`load_bundle()` 检查每日的开盘价、最高价、最低价、收盘价和成交量（OHLCV），并用代码计算技术指标与目标交易周。这些“确定性指标”由代码按固定公式计算，模型负责解释数值。`build_team()` 重新检查 Skill，为角色配置方法、工具和输出 schema（字段及类型要求），并创建实际的 ADK Agent 和 Workflow。数据检查或团队构造失败时，命令会报错。

这个入口检查到团队构造完成为止，不启动执行团队的 Runner，也不请求 Gemini 或生成研究报告。若它失败，可以先排查本地文件、数据和角色配置；若它通过而真实研究失败，再检查 API 访问和模型执行过程。

把这套检查迁移到其他项目时，需要一起修改三处：准备证据的函数、角色及其 Skill 配置、`TOOLS` 中列出的可用工具。尤其要让 `TOOLS` 与实际注册给 Agent 的工具保持一致。仍可沿用“诊断 → 筛选 → 构造 → 实际执行 → 最终校验”的顺序，并按需复用引用校验、共享预算账本和防止并发运行的锁。完整检查规则见[实现参考](docs/implementation.md#预检与兼容性)。

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

每个角色单独创建一个 Toolset。这里同时绑定方法、真实工具、目录披露方式与生命周期；这些参数的归属和可观察变化放在第 08 节展开。

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

上例是 `doctor` 的输出节选，省略了另外三个核心 Skill、内容哈希与检查理由。请确认五个核心 Skill 均为 `SUPPORTED`。另一个命令 `offline-check` 应显示 `model_called: false`，且 `agents` 包含 `technical`、`catalyst`、`review` 三个角色。

| 入口 | 检查范围 |
| --- | --- |
| `doctor` | Python／ADK 版本、Key 是否存在、Skill 兼容性报告 |
| `offline-check` | 合成数据能否处理、指标和交易周能否计算、Agent／Workflow 能否构造 |
| 实际研究 | API 是否可用、模型是否加载必需 Skill 并调用工具、报告及其引用能否通过校验 |

前两个命令都不调用模型。`doctor` 正常结束后仍需阅读检查结果；`offline-check` 通过后，才说明本地数据准备和团队构造没有发现问题。API 权限、额度和模型的实际表现，需要在研究运行中验证。详细规则见[实现与能力检查参考](docs/implementation.md#预检与兼容性)。

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

## 07 · 用 Web Trace 拆解 Skill 请求与返回

先看团队执行是否符合设计，再追踪一个 Agent 的“请求 → 模型返回 → 工具执行 → 下一次请求”。以下界面操作对应仓库固定的 ADK 2.13.0；截图来自合成 DEMO 的真实 Gemini 运行。

### 第一步：确认 Workflow 顺序与耗时

在对话区域切换到 **Traces**，展开 `workshop` 下的 `research_team`，再按时间查看三个同级角色：`technical → catalyst → review`。外层 `workshop` 是 Python 入口节点，负责参数解析与调用团队；其中有三个 LLM Agent。

![ADK Web UI 真实执行的 Workflow 与耗时](docs/images/trace-workflow.png)

调用树中的每条记录称为一个 **span**。展开角色，能看到模型步骤（截图中为 `generate_content gemini…`）、`load_skill`、证据工具和结构化结果提交。条形时间线与 **Duration** 表示该步骤的耗时。

先核对三个角色顺序，再核对每个角色是否加载了第 02 节分配的方法。图中的调用次数和耗时属于那一次历史运行；模型可能合并多个工具调用，实际时长以本次 Trace 为准。

### 第二步：理解 ADK 在请求中加了什么

![单个 Skill Agent 的请求组装、Gemini 返回与工具调用循环](docs/images/request-pipeline.svg)

ADK 每次准备模型步骤时构造一个 `LlmRequest`。对本项目而言，请求主要由三部分组成：

| 请求部分 | 从哪里来 | 在这里找什么 |
| --- | --- | --- |
| `config.system_instruction` | 角色指令、State 模板替换、ADK 的角色标识与输出要求、Skill 使用指南；EAGER 时还有名称／描述目录 | 搜索 `technical`、`load_skill`、`available_skills`；Review 中搜索 `Technical analysis:` |
| `contents` | 用户消息、此前模型输出、工具调用 `function_call` 与工具返回 `function_response` | `load_skill` 的 `instructions`、参考资料、证据工具返回值 |
| `config.tools` 及生成配置 | 输出 schema 的提交工具、Skill 基础工具、激活 Skill 所需的业务工具；温度、输出长度、thinking 等配置 | 前后两次请求的函数声明如何变化 |

这几层来自不同位置：项目的角色指令要求“先加载分配到的全部 Skill”；ADK 的 Skill 使用指南解释发现与加载规则；Skill 正文规定具体研究方法。**加载后的正文位于工具返回消息中，进入后续请求的 `contents`。** EAGER 首次提供的是名称与描述目录。

### 第三步：比较 technical 加载 Skill 前后的 Request

1. 选择 `technical` 的第一次模型 span，点击左侧 **Event ID** 定位事件，再选择 **Request** 输入箭头图标。查看系统说明中的角色要求、Skill 使用指南和 EAGER 目录；此时尚未加载方法正文。
2. 在 **Events** 中找到 `load_skill`，检查参数 `skill_name` 和工具返回中的 `skill_name`、`instructions`、`frontmatter`。加载动作还会更新 ADK 维护的 Skill 激活状态。
3. 选择加载后的下一次模型 span，打开 **Request**。界面将消息展示为 `user_messages`，展开其中的 `parts`，找到 `type: tool_call_response` 的项，再看 `response → instructions` 中的 Skill 正文。
4. 查看 `data-quality` 正文中的证券与截至时间：`{ticker}`、`{as_of}` 已被替换为本次 State 的值。这是该 Skill 的 `metadata.adk_inject_state: true` 在加载时生效。

![加载后的 Skill 正文与 State 注入出现在后续模型请求中](docs/images/trace-request.png)

再对照工具声明。当前 EAGER 配置下，可按工具名称核对，忽略排列顺序：

```text
激活前：set_model_response, load_skill, load_skill_resource, unload_skill
仅激活 data-quality 时：再增加 read_evidence
两个 Skill 都激活后：包含 read_evidence, calculate_indicators
```

`additional_tools=[read_evidence, calculate_indicators]` 注册了候选工具实现；ADK 根据已激活 Skill 的 `metadata.adk_additional_tools` 决定本次向模型开放哪些工具。若模型在一次响应中加载两个 Skill，下一次请求可能直接出现两个业务工具。

`set_model_response` 是 ADK 为当前 `output_schema` 流程提供的结构化结果提交工具。它和应用的两个证据工具有不同来源。

### 第四步：把模型 Response 与工具 Response 对起来

在模型 span 的 **Response** 输出箭头中找工具调用，例如 `read_evidence`。规范化界面显示为 `type: tool_call`，核对其中的 `name`、`arguments`；原始 ADK 事件中对应 `function_call`、`args`。随后在 **Events** 看同名调用的 `function_response`：这是 ADK 分发到 Python 后得到的实际返回。下一次模型请求的 `contents` 会带上这段结果，模型据此继续分析。

这条循环同样适用于 Skill：Gemini 提出 `load_skill` → ADK 执行加载 → 返回方法正文 → Gemini 在下一步按方法使用证据工具。一次研究通常会产生多次模型请求。

在角色结束后查看 State 更新：`technical` 和 `catalyst` 应有结构化分析。打开 `review` 的首次 Request，搜索 `Technical analysis:`、`Event analysis:`，确认两份分析已经填进审查指令。

最后回到对话末尾的 Markdown 报告，或查看 `decision.json`。Events 中的 `review` 原始结果之后，还会经过 Python `validate_decision()`；fixture 的最终结果必须是 `insufficient_data / HOLD / unknown / low`。

### 第五步：找到实际发往 Gemini 的请求与返回位置

下面是已安装 ADK 包中与本次请求有关的源码入口，路径从 `google/adk/` 开始。它们用于定位加工环节，具体函数与内部文件可能随 ADK 版本变化：

| 加工环节 | ADK 2.13.0 源码入口 | 作用 |
| --- | --- | --- |
| 创建每个模型步骤 | `flows/llm_flows/base_llm_flow.py` · `_run_one_step_async()` | 创建并准备 `LlmRequest` |
| 基础配置与角色指令 | `flows/llm_flows/basic.py`；`prompt/_instructions.py` | 写入模型配置、角色指令，替换 State 模板 |
| 消息历史与 schema | `flows/llm_flows/context/_contents.py`；`prompt/_schema.py` | 填入消息／工具结果，加入结构化输出要求 |
| Skill 指南、目录与正文 | `tools/skill_toolset.py` · `process_llm_request()`、`LoadSkillTool.run_async()` | 准备 Skill 系统说明；加载正文、注入 State、记录激活状态 |
| 本步动态工具 | `tools/skill_toolset.py` · `get_tools()`；`flows/llm_flows/tools/_agent_tools.py` | 按激活状态解析工具，并生成函数声明 |
| 调用模型与处理返回 | `flows/llm_flows/core/_model_call.py` → `models/google_llm.py` · `Gemini.generate_content_async()` | 请求交给 Google Gen AI SDK；返回转换为 `LlmResponse` |

其中 `prompt/` 在表内均指 `flows/llm_flows/prompt/`。如果要在本机定位最终模型适配器：

```bash
.venv/bin/python - <<'PY'
import inspect
from google.adk.models.google_llm import Gemini
print(inspect.getsourcefile(Gemini))
PY
```

打开输出的文件，找到 `generate_content_async()`，也可查看 [ADK 2.13.0 的 Gemini 适配器源码](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/models/google_llm.py)。当前非流式路径的核心调用可简化为下面这样，省略 instrumentation 包装、重试及适配逻辑：

```python
response = await api_models.generate_content(
    model=model,
    contents=llm_request.contents,
    config=llm_request.config,
)
llm_response = LlmResponse.create(response)
```

这里的 `api_models` 来自 Google Gen AI SDK 的异步模型客户端。SDK 收到的核心输入是 `model`、`contents` 和 `config`；Skill 没有独立的模型调用通道。模型适配器在调用前还会处理请求兼容性与 HTTP 配置，返回后由 ADK 转成事件，继续工具循环或完成角色输出。

需要区分三种可观察内容：

| 在哪里看 | 保存了什么 | 用来回答什么问题 |
| --- | --- | --- |
| 本项目 `requests.json` | `before_model_callback` 保存的 Agent 名、工具名称、系统说明 | 本次有哪些工具？EAGER 目录或 Review 模板是否已进入系统说明？ |
| Web **Request / Response** 与 span **Attributes** | ADK 采集的模型请求／响应追踪表示；Request 界面规范化显示 `system_instruction`、`user_messages` | 正文和证据怎样进入上下文？模型返回了什么调用或文本？ |
| `Gemini.generate_content_async()` 中的 SDK 调用 | 真正交给 Google Gen AI SDK 的 `model / contents / config` 与返回 | 最终在哪个代码边界发给 Gemini、在哪里接回结果？ |

`requests.json` 是摘要，没有完整消息历史、函数 schema 或模型返回。Web Trace 也经过格式化与敏感字段清理，不是原始 HTTP 报文。当前 span Attributes 中可找 `gcp.vertex.agent.llm_request`、`gcp.vertex.agent.llm_response`；这些是 ADK 沿用的追踪字段名，本项目仍使用 Gemini Developer API。

### 保存报告与执行依据

| 文件 | 内容 |
| --- | --- |
| `report.md` / `decision.json` | 校验后的报告／结构化结果，含数据模式、Skill 哈希与模型版本等信息 |
| `evidence.json` | 本次证据包、来源、截至时间与确定性指标 |
| `trace.json` | 项目从 ADK 事件提取的角色、Skill／工具调用与返回值 |
| `requests.json` | 每次模型请求的工具名与系统说明摘要 |
| `usage.json` | 输入／输出 token、模型响应数、工具调用数、耗时与费用估算 |

Web 原生 Trace 由 ADK 采集；这些磁盘文件由项目整理保存。按本文命令启动时，Session／Trace 在服务内存中，重启会清除；需要保留的实验依据使用 `runs/` 中的文件。

<a id="skill-parameters"></a>

## 08 · 参数放在哪里：Skill、Toolset、Agent 与应用配置

前面已经运行了完整团队。现在改变单个参数，再在 Trace 或机制实验中观察影响。先按配置对象区分归属：

| 配在哪里 | 参数 | 控制什么 | 本项目怎样使用 |
| --- | --- | --- | --- |
| 单个 `SKILL.md` 的 frontmatter | `name`、`description` | 该 Skill 的名称与发现信息 | 五个核心方法各自声明 |
| 单个 Skill 的 `metadata` | `adk_additional_tools` | 该 Skill 激活后需要开放的宿主工具名称 | `technical-trend` 申请两个业务工具 |
| 单个 Skill 的 `metadata` | `adk_inject_state` | 加载正文时是否替换 `{state_key}` | `data-quality` 注入 `ticker`、`as_of` |
| `SkillToolset(...)` | `skills`、`additional_tools` | 当前角色的方法对象、宿主提供的真实工具实现 | 每个角色分别配置 |
| `SkillToolset(...)` | `discovery_mode` | 本地方法名称与描述何时披露 | 项目默认 EAGER；ADK 默认 LAZY |
| `SkillToolset(...)` | `registry` | 通过搜索／按名称获取 Skill 的来源 | 第 09 节本地实验与云端接法 |
| `SkillToolset(...)` | `code_executor`、`save_output_artifacts` | 脚本执行及输出文件保存 | 仅脚本 lab 显式配置 |
| `SkillLifecycleConfig(...)`，作为 Toolset 的 `lifecycle_config` | `default_mode`、`max_active_skills`、`skill_overrides` | 默认生命周期、BOUNDED 数量上限、指定 Skill 的模式覆盖 | 主团队 BOUNDED、每角色 2 个；lab 演示覆盖 |
| `LlmAgent(...)` | `instruction`、`tools`、`output_schema`、`output_key` | 角色职责、工具入口、输出结构、结果写入哪个 State 键 | 三个角色各自配置 |
| `LlmAgent(generate_content_config=...)` | `max_output_tokens`、`temperature`、`thinking_config` | Gemini 生成行为 | Python 中设置输出上限 4096、温度 0.2、thinking 为 low |
| `Workflow(...)` / `RunConfig(...)` | `timeout` / `max_llm_calls` | 工作流超时／一次运行的模型调用上限 | 180 秒／YAML 的上限；项目回调再做团队共享计数 |
| `config/workshop.yaml` | `roles`、`model`、`discovery`、预算项 | 项目应用设置，经 Python 转为上述对象 | 应用自定义 YAML |
| 环境变量 | `ADK_ENABLE_SKILL_LIFECYCLE=1` | ADK 生命周期功能开关 | `environment()` 在启动时设置 |
| `adk web` 命令行 | `--allow_origins` | Web 服务允许的跨来源访问 | Cloud Shell 启动命令传入来源正则 |

### 同样写“工具”，两处配置的值不同

单个 Skill 在 [technical-trend/SKILL.md](skills/technical-trend/SKILL.md) 中声明需要什么：

```yaml
name: technical-trend
description: Analyze stock price trend using deterministic technical indicators.
metadata:
  adk_additional_tools: ["calculate_indicators", "read_evidence"]
```

这段位于 `SKILL.md` 开头的 `---` 区块内，值是**工具名称字符串**。Toolset 中 `additional_tools=[read_evidence, calculate_indicators]` 的值则是**实际 Python 函数**。名称必须匹配；只改 Skill 文件不会创建新工具。

`data-quality` 另外声明 `metadata.adk_inject_state: true`，使正文中的 `{ticker}`、`{as_of}` 在 `load_skill` 时替换成 State 快照。Review 的 `{technical}`／`{catalyst}` 位于 `LlmAgent.instruction`，是在准备角色指令时替换。两者的配置位置与生效时机不同。

### 应用参数怎样传到 ADK

- 模型优先读取环境变量 `GEMINI_MODEL`，其次是 YAML 的 `model`；当前代码只接受 `gemini-3.8-flash`，更换前需同步调整模型限制与费用估算。
- 发现模式优先读取 CLI 的 `--discovery` 或 Web 的 `discovery=`，其次是 YAML 的 `discovery`，再传给 `SkillToolset(discovery_mode=...)`。
- YAML 的 `roles` 转为每角色的 `skills=[...]`；保留 `technical → catalyst → review` 的名称与顺序，Review 模板依赖前两份输出。
- YAML 的 `max_model_calls` 默认 16；CLI `--max-calls` 可以调低，不能调高。三个角色共享此上限，工具返回后再次调用模型也计入。

下面两组实验分别改变 **Toolset 的发现模式**和 **传给 Toolset 的生命周期配置**，不需要修改 Skill 的研究正文。

### Discovery：模型何时看到可用 Skill 列表

Discovery（发现模式）决定**模型何时看到可用 Skill 的名称与描述列表**，从而知道有哪些方法可选。下面的 EAGER 和 LAZY 都只讨论这份列表何时进入模型上下文；Skill 正文和参考资料仍通过工具按需读取。本地 Skill 文件在构造团队时就已经完成检查和解析。

| 对比点 | EAGER（直接提供列表） | LAZY（按需获取列表） |
| --- | --- | --- |
| 首次模型请求 | 系统说明（system instruction）直接包含可用 Skill 的名称与描述 | 系统说明不包含这份列表 |
| 如何获取列表 | 模型直接阅读系统说明；不提供 `list_skills` 工具 | 模型可以调用 `list_skills`，从工具返回结果中读取列表 |
| 本项目中的步骤 | 阅读列表 → `load_skill` 加载正文 → 分析 | `list_skills` 获取列表 → `load_skill` 加载正文 → 分析 |
| 上下文开销 | 第一次请求就包含整份列表；列表越长，占用的输入 token 越多 | 第一次请求较小；调用 `list_skills` 后，返回的列表同样会进入上下文、占用 token |
| 适用情况 | Skill 数量少、列表稳定，而且多数任务都需要使用这些方法 | Skill 较多，或许多任务无需使用 Skill，可以省去获取列表的步骤 |

LAZY 将获取列表推迟到需要时。如果任务最终仍调用了 `list_skills`，这份列表的上下文开销依然存在，还会增加一次获取列表的工具调用。因此需要结合实际任务比较 token 和耗时。

ADK 默认使用 LAZY。本项目中每个角色只分配一到两个 Skill，而且研究明确要求使用它们，所以默认选择 EAGER。为了便于实验对比，本项目还在 LAZY 模式的角色指令中要求先调用 `list_skills`。这是项目的额外要求；ADK 本身允许模型在已知 Skill 名称时直接调用 `load_skill`。

#### 不调用模型的机制对照

下面五个 `lab` 实验（`discovery`、`lifecycle`、`sizing`、`artifacts`、`registry`）都由代码按固定步骤调用实际的 ADK 接口，不请求 Gemini。这种方式可以直接观察框架行为，避免模型临时选择不同步骤而影响比较。

下面的代码摘录保留关键调用，省略导入和部分准备、清理、保存结果的代码。要运行完整实验，请使用每节给出的 CLI 命令或 Web UI prompt。

摘录中的 `skills` 是 `accepted_skills()` 返回的 Skill 字典，以名称为键；`result` 是保存实验输出的字典。`ctx` 是 ADK 的工具上下文（`ToolContext`），提供当前会话、执行轮次和 State 等信息。项目用 `context()` 辅助函数为实验创建它。另一个辅助函数 `call()` 按名称从 `SkillToolset` 中找到工具并执行：

```python
async def call(ts, ctx, tool_name, args):
    tool = next(t for t in await ts.get_tools(ctx) if t.name == tool_name)
    return await tool.run_async(args=args, tool_context=ctx)
```

这里的 `await` 表示等待异步操作完成。每次调用哪个工具、传入什么参数，都由实验代码指定。

Discovery 实验分别用 EAGER 和 LAZY 配置同一批 Skill，让 `SkillToolset` 为一个初始为空的模型请求（`LlmRequest`）补充系统说明和工具配置：

```python
for mode in SkillDiscoveryMode:  # EAGER、LAZY 各执行一次
    ts = SkillToolset(skills=list(skills.values()), discovery_mode=mode)
    ctx = await context(agent)
    request = LlmRequest()
    await ts.process_llm_request(tool_context=ctx, llm_request=request)
    result["modes"][mode.value] = {
        "tools": [t.name for t in await ts.get_tools(ctx)],
        "system_instruction": request.config.system_instruction,
    }
    await ts.close()
```

`process_llm_request()` 负责准备请求内容，本实验不会把请求发送给模型。比较两种模式的 `system_instruction`，可以检查 Skill 名称与描述列表是否已经写入系统说明；比较 `get_tools()` 返回的工具名，可以检查是否提供 `list_skills`。

**Web UI prompt**：

```text
lab discovery
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli lab discovery
```

查看对话结果或 `runs/lab-discovery.json` 中的 `modes`：EAGER 的 `system_instruction` 包含 Skill 名称与描述，`tools` 中没有 `list_skills`；LAZY 的系统说明没有这份列表，`tools` 中则包含 `list_skills`。这说明两种模式的差别已经体现在请求准备阶段，无需调用模型就能观察。

#### 真实模型对照

在 Web UI 中分别新建两个会话，依次发送下面两条 prompt，等待第一份研究结束后再运行第二份：

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

![LAZY 模式中的 list_skills 与后续 Skill 加载](docs/images/trace-lazy.png)

这次对比会真实调用 Gemini。在 LAZY 运行的 **Traces／Events** 中，检查各角色是否先调用 `list_skills`，再调用 `load_skill`。然后比较两次运行目录中的 `requests.json`，查看各角色首次请求的系统说明；最后比较 `usage.json` 的输入／输出 token 数和耗时。两次使用相同的合成数据与 Skill，只改变发现模式，具体开销以运行结果为准。

Skill 数量很多时，`list_skills` 仍会返回很长的列表。若希望按关键词只返回少量相关方法，可以使用 Registry（Skill 检索接口），见[Registry](#skill-registry)。

### 生命周期：方法加载后保持多久

生命周期配置决定 Skill 加载后保持激活的时间，以及何时自动失效或需要手动卸载。它管理每个 Agent 当前激活的 Skill，以及这些 Skill 为模型提供的方法正文和额外工具；已经保存的分析结论、报告和生成文件会继续保留。

先区分两个范围：**会话（Session）**可以包含多轮交互；**一轮执行（invocation）**指从收到一条用户消息到处理完成的全过程，其中可以包含多次模型请求和工具调用。以下表格中的“下一轮”，指在同一会话中处理下一条消息。本项目的完整研究每次都使用新会话；后面的机制实验会用代码模拟同一会话状态延续到下一轮的情况。

![Skill 的加载、淘汰、临时有效与卸载](docs/images/lifecycle.svg)

| 模式 | 加载后保持多久 | 是否受 `max_active_skills` 数量上限约束 |
| --- | --- | --- |
| PERSISTENT（持续有效） | 在当前会话中保持激活，直到调用 `unload_skill` 卸载 | 否；也不会因其他 Skill 超过上限而被淘汰 |
| BOUNDED（数量受限） | 在当前会话中保持激活；超出上限时，按最近一次加载的先后顺序，先淘汰较早加载的 BOUNDED Skill | 是；每个 Agent 分别计算 |
| EPHEMERAL（本轮有效） | 在加载它的这一轮执行中持续有效；同一会话开始下一轮执行时失效，需要时可重新加载 | 否；不会挤占 BOUNDED Skill 的数量名额 |

ADK 的默认模式是 PERSISTENT，默认 BOUNDED 上限为 5。本项目通过 `ADK_ENABLE_SKILL_LIFECYCLE=1` 开启生命周期功能，并将研究团队配置为 BOUNDED、上限 2：每个 Agent 最多同时激活两个 BOUNDED Skill。PERSISTENT 和 EPHEMERAL 不计入这个上限，各 Agent 的数量也互不影响。

再次调用 `load_skill` 加载已激活的 BOUNDED Skill，会把它移到最近加载的位置。例如上限为 2，依次加载 A、B、再次加载 A、加载 C，最终淘汰的是 B。

下面的机制实验把上限改为 1，便于观察第二个 BOUNDED Skill 加载后，第一个如何被淘汰。

`default_mode`、`max_active_skills`、`skill_overrides` 写在 `SkillLifecycleConfig` 中，再通过 `SkillToolset(lifecycle_config=...)` 传入：

```python
ts = SkillToolset(
    skills=variants,
    additional_tools=[risk_probe, report_probe],
    lifecycle_config=SkillLifecycleConfig(
        default_mode=SkillLifecycleMode.BOUNDED,
        max_active_skills=1,
        skill_overrides={"lab-glossary": SkillLifecycleMode.EPHEMERAL},
    ),
)
```

`variants` 包含实验在内存中创建的三个演示 Skill。`lab-risk` 和 `lab-glossary` 都在 `metadata.adk_additional_tools` 中声明需要 `risk_probe`，`lab-report` 则声明需要 `report_probe`。两个 probe 是只返回文字的 Python 函数，用来观察模型可调用的工具列表如何随 Skill 激活状态变化。

配置中的 `additional_tools` 提供工具实现；激活哪个 Skill，就向模型提供该 Skill 声明需要的工具。`skill_overrides` 单独把 `lab-glossary` 设为 EPHEMERAL，其他两个沿用默认的 BOUNDED。

实验先在第一轮中依次加载三个 Skill，再模拟进入第二轮，最后手动卸载仍激活的方法：

```python
ctx = await context(agent, "turn-1")
await call(ts, ctx, "load_skill", {"skill_name": "lab-risk"})
await call(ts, ctx, "load_skill", {"skill_name": "lab-report"})  # 超过上限，淘汰 lab-risk
await call(ts, ctx, "load_skill", {"skill_name": "lab-glossary"})

# 将 State 传给新的工具上下文，用不同的执行轮次编号模拟下一轮
ctx2 = await context(agent, "turn-2", ctx.state.to_dict())
active = ts.list_active_skills(ctx2)  # lab-glossary 已失效，只剩 lab-report
await call(ts, ctx2, "unload_skill", {"skill_name": "lab-report"})
```

实验在每一步用 `ts.list_active_skills(ctx)` 查看当前激活的 Skill，用 `await ts.get_tools(ctx)` 查看模型此时可以调用的工具。示例中的 `"turn-1"`、`"turn-2"` 是传给 `context()` 的执行轮次编号。该辅助函数为第二轮创建新的上下文，并传入上一轮的 State，从而模拟状态保留、执行轮次变化的情况。

**Web UI prompt**：

```text
lab lifecycle
```

**CLI**：

```bash
.venv/bin/python -m stock_research.cli lab lifecycle
```

在对话结果或 `runs/lab-lifecycle.json` 中核对：

| 步骤 | 激活列表 | 工具变化 |
| --- | --- | --- |
| 第一轮：加载 `lab-risk` | `lab-risk` | 出现 `risk_probe` |
| 第一轮：加载 `lab-report` | `lab-report` | `lab-risk` 被淘汰，`risk_probe` 消失，出现 `report_probe` |
| 第一轮：加载 `lab-glossary` | `lab-report`、`lab-glossary` | 再次出现 `risk_probe`；EPHEMERAL 不占 BOUNDED 名额，所以 `lab-report` 保留 |
| 开始第二轮执行 | `lab-report` | `lab-glossary` 失效，`risk_probe` 消失，`report_probe` 保留 |
| 手动卸载 `lab-report` | 无激活 Skill | `report_probe` 消失 |

这里的“工具消失”指该工具从后续模型请求的可调用工具列表中移除；`load_skill` 等基础工具仍然可用。如果另一个激活的 Skill 也声明了同一个工具，这个工具仍会保留。

实验还检查卸载对方法正文的影响：构造一个保留旧 `load_skill` 返回内容的模型请求，再调用 `ts.process_llm_request(...)`。输出中的 `pruned_history` 应包含 `"skill_name": "lab-risk"`、`"status": "unloaded"` 等字段，表示请求历史中的这份方法正文已替换为简短的卸载通知。

这个替换发生在准备后续模型请求时，不会删除会话中保存的原始执行事件，也不会清空已读取的参考资料、其他工具返回结果或分析结论。Skill 卸载后仍可被发现，并可再次加载。

整个实验由代码控制，**不调用 Gemini**。Web 对话结果会显示上述完整状态序列；Trace 只记录实验入口节点，详细步骤请看对话结果或 JSON 文件。EPHEMERAL 的有效范围覆盖整轮执行中的所有模型和工具调用。

修改 Skill 文件后，需要新建研究会话，让应用重新检查文件并构造 Skill。本项目没有开启运行过程中的自动重验证，正在执行的任务不会自动采用文件改动。

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

`call()` 是第 08 节介绍的工具执行辅助函数。第一步，ADK 的 `search_skills` 工具调用 Registry 的搜索方法，返回匹配 `risk` 的候选信息。第二步，`load_skill` 调用 Registry 的 `get_skill()` 取得 `risk-review`，把正文返回给调用方并激活这个 Skill。实验代码固定指定查询词和加载名称，不调用模型，也没有继续执行业务分析。

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
