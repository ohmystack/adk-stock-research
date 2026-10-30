# 本地验证记录

日期：2026-10-29（Asia/Shanghai）。使用 Python 3.12.8、ADK 2.13.0、Google Gen AI SDK 2.34.0、Gemini 3.8 Flash；模型后端为 **Google AI Studio Key / Gemini Developer API**。

## 已通过

| 范围 | 验证结果 |
| --- | --- |
| 安装入口 | `bash scripts/setup.sh` 在本机复核通过；支持复用现有环境，自动寻找 Python 3.11+ |
| 核心 Skill | 五个目录由真实 ADK 解析；工具、资源与能力检查通过 |
| 自动测试 | **19 passed**；覆盖指标、节假日目标周、缺失证据、虚构引用、原生工具、三角色状态传递与导入 |
| CLI／YAML | 未传 --discovery 时读取 YAML；显式参数优先；三种参数组合均验证通过 |
| Discovery | 原生请求处理器验证 EAGER／LAZY 的目录与工具差异；无模型调用 |
| 生命周期 | bounded 淘汰、ephemeral 下一轮失效、显式卸载、历史指令替换均由真实 ADK 工具验证 |
| 原生脚本产物 | metrics-export 脚本生成文件，经 ArtifactService 保存、读回并核对内容 |
| 第三方适配 | position-sizer-adk 通过真实 ADK run_skill_script 执行；JSON／Markdown 原生 Artifact 读回通过；20 股计算符合预期 |
| npx | skills@1.7.4 + Node 24.22.1，在本机临时目录以 universal / copy 安装固定来源成功；实际目标 `.agents/skills/position-sizer` |
| npx → ADK | 从安装目录导入，识别为 ADAPTABLE，原因是默认运行配置无脚本后端；同内容导入幂等且不自动激活 |
| Registry | 原生 SkillRegistry 接口的本地关键词实现完成 search → load 验证 |
| 实时数据 | 通过指定代理取得 GOOGL 的 126 根完整日线和 Google News RSS 标题；目标交易周正确计算 |
| 文档资产 | 七张中文 SVG、合并后的 README 链接和 Markdown 结构检查 |

测试中的脚本化模型只用于验证 Runner／Workflow、工具和状态行为，显式禁止 HTTP。以下两项另外使用了真实 Gemini。

## 真实 Gemini 端到端

| 输入 | 模式 | 模型响应 | 工具调用 | 耗时 | 按付费标价估算 |
| --- | --- | --- | --- | --- | --- |
| 固定合成 DEMO | EAGER | 9 | 17 | 32.37 秒 | $0.019894 |
| 真实 GOOGL | EAGER | 11 | 20 | 34.00 秒 | $0.027347 |
| 合计 | — | **20** | **37** | — | **$0.047241** |

估算依据：输入 $0.75／百万 token、输出含 thinking $3.75／百万 token；不是账户实际账单，免费层实际可能为零。未使用 Search Grounding。

两次运行均实际加载必要 Skill，完成三角色状态传递、JSON 与引用校验。合成输入强制 HOLD／unknown／low；真实输入因只提供新闻标题而标记 degraded，信心最高 medium。这里不评价建议方向的投资有效性。

原始运行保留在本机 `runs/`，参考执行快照保留在本机 `docs/examples/`；这些目录与凭据、实际行情缓存均由 `.gitignore` 排除，不上传 GitHub。课程统一通过 HTTPS 仓库获取。

## 尚未验证／有意不包含

- **Cloud Shell 未验证**，按本轮要求暂不执行；不能将本地通过等同于云端通过。
- 第三方适配版由 ADK 工具实际执行过，但尚未让 Gemini 自主选择并运行它。
- 托管 Google Cloud Skill Registry、向量检索、Vertex AI、Cloud Run 未纳入本地验收。
- 新闻只使用 RSS 标题；未来事件日历、新闻全文与权威公告核验还未接入。
- 港股／A 股、通用跨领域预设、模型短审查、复杂预测回测未实现；核心范围为美股研究和零 token 静态能力检查。
- 兼容性检查识别已知要求，不能证明任意第三方 Skill 的语义兼容或代码安全。
- 费用限制覆盖同一目录内的本项目运行，不能替代平台硬额度，也不能汇总其他程序的消费。

依赖当前有少量 pandas 的弃用提示，相关检查通过；Skills 实验开关提示属预期行为，未隐藏它们。


## 2026-10-30 · README 与 Web UI

本机使用 ADK 2.13.0、Python 3.12.8、Gemini 3.8 Flash，运行 README 中的原生 `adk web web_agents --port 8000 --no-reload --no_use_local_storage`。

| 验证项 | 结果 |
| --- | --- |
| 文档结构 | README 从 1,137 行整理为约 590 行；实现与静态检查细节保留在 docs/implementation.md |
| Web 入口 | research 被原生 AgentLoader 发现；prompt 选择 fixture/live、ticker 与 eager/lazy |
| 原生 Trace | 在当前 UI invocation 中动态运行同一 Workflow；三个角色、模型与工具 span 归入本次 Session，调用树与耗时可见 |
| 请求查看 | 模型 span 的 Event ID 可跳到 Events 的 Request／Response；请求包含 load_skill 正文与 State 注入后的任务值 |
| UI 机制实验 | discovery、lifecycle、sizing、artifacts、registry 五个 prompt 均实际操作通过；不调用 Gemini |
| 实验隔离 | 同一 Session 重复研究提示 New Session；每次新研究重新检查并读取 Skill／YAML |
| CLI／Web 回归 | **28 passed**；实际 Runner 与脚本化模型覆盖两种入口、State 交接、必要 Skill、调用上限失败留档、账本计次与锁清理，禁止网络访问 |
| 文档与图片 | 本地链接、锚点、代码围栏检查通过；一张官方 PNG 和三张真实 UI PNG，有来源与许可证；README 共七处图片 |

### 真实 Gemini Web UI 运行

以下三次均通过浏览器输入 prompt 发起，结果通过最终程序校验。

| 输入 | Discovery | 模型响应 | 工具调用 | runtime 耗时 | 估算费用 |
| --- | --- | --- | --- | --- | --- |
| 合成 DEMO | EAGER | 9 | 17 | 28.23 秒 | $0.016508 |
| 合成 DEMO | LAZY | 13 | 21 | 39.46 秒 | $0.021883 |
| 真实 GOOGL | EAGER | 9 | 20 | 43.31 秒 | $0.022519 |

本轮费用估算合计 $0.060910；不是实际账单。EAGER／LAZY 使用相同合成输入；LAZY 三个角色各调用一次 list_skills。该次 LAZY 多了一次取证步骤，不能把全部耗时差异归因于 Discovery。

UI 时间线覆盖整个请求，runtime 的 usage 只计研究流程，因此截图 EAGER 的总延迟 28.68 秒与 usage 中 28.23 秒不同。正式报告应查看对话最后的 Markdown 或 decision.json；中间 review JSON 尚未经过数据质量后处理。

截图对应本机 runs/20261030T060712-f6f7d1 与 runs/20261030T061613-d172a5；live 记录为 runs/20261030T061712-729e68。原始记录、真实行情与凭据不提交 Git。

Cloud Shell／Web Preview 仍未验证。所有截图均为合成输入；本轮没有改写核心 Skill 的方法内容。


## 2026-10-30 · 代码讲解顺序与开发接续

- README 改为概念 → 环境 → 核心代码／预检／配置 → 两种运行方式 → 实验；Web UI 启动已移至代码之后。
- 正文详细展开 doctor、scan／inspect_skill、accepted_skills、offline-check 的做法、代码、返回语义与复用边界。
- 新增仓库内 AGENTS.md 与 docs/progress.md，整理最新约定、已完成范围、验证证据、跨设备步骤和未完成事项。
- 重新执行 pytest：**28 passed**；pip check 无依赖冲突。doctor 五个核心 Skill 均 SUPPORTED；offline-check 三角色构造通过且 model_called=false。
- 七份 Markdown 的链接、锚点、代码围栏与 23 段 Python／JSON／YAML 示例通过检查；发布候选内容与忽略规则检查通过。
- 本次没有新增 Gemini 请求；沿用上节已完成的真实 CLI／Web 运行证据。Cloud Shell／Web Preview 仍按要求暂缓。


## 2026-10-31 · README 机制实验代码

- 第 05／06／08 节补充五个 lab 的关键配置、ADK 调用与结果解释；仅修改文档，保留每个实验的 CLI 和 Web prompt。
- README 的 55 个代码围栏闭合；17 段 Python 通过 AST 语法检查，2 段 JSON、2 段 YAML 解析通过；42 处本地链接及锚点有效，五组 lab 命令均存在。`git diff --check` 通过。
- 尝试以下四项现有测试，覆盖 Discovery、生命周期、脚本 Artifact、Position Sizer 和 Registry：

```bash
.venv/bin/python -m pytest -q tests/test_workshop.py -k 'native_lifecycle_and_history_pruning or native_discovery_and_registry or native_script_artifact_roundtrip or third_party_adk_script_roundtrip'
```

- 测试在收集阶段退出，尚未执行用例：导入 `pydantic_core._pydantic_core` 时，macOS 报 `code signature ... not valid for use in process: library load disallowed by system policy`。获授权在沙箱外重试，结果相同。
- 首轮文档检查通过，测试失败原因及后续环境修复、重跑结果见下。没有请求 Gemini 或抓取行情。

### macOS 隔离标记修复与回归

- 用户报告 `_yaml.cpython-312-darwin.so` 无法通过 Apple 验证。检查发现 `.venv`、PyYAML 与 pydantic_core 扩展携带相同的 `com.apple.quarantine`，来源字段为 `sharingd`；两个扩展均通过 `codesign --verify`，文件哈希与各自安装包的 RECORD 一致。
- 将原隔离属性备份至系统临时目录，然后仅对项目 `.venv` 执行 `xattr -d -r -s com.apple.quarantine .venv`，清除 13,224 处隔离标记；`-s` 作用于符号链接本身，不修改链接指向的外部 Python。保留其他扩展属性，没有重新签名或安装依赖。
- 原生导入验证通过：PyYAML 6.0.3／`yaml.__with_libyaml__ == True`，Pydantic 2.14.1／pydantic_core 2.50.1。`spctl --status` 返回 `assessments enabled`，系统安全检查保持启用。
- 修复后执行 `.venv/bin/python -m pytest -q`：**28 passed，5 warnings，7.41 秒**；覆盖五个 lab 及原有业务流程。警告为已有 pandas 弃用提示和 Skill 生命周期实验提示，本轮没有调用 Gemini。

## 2026-10-31 · README 全文可读性复核

- 通读全部九节，按读者理解概念、执行操作、观察结果的顺序优化说明。重点展开 Discovery 的列表与 token 开销、Session 与执行轮次、生命周期淘汰与卸载、预检范围、配置优先级、固定证据对照、第三方适配与脚本产物、预算计次和排错。
- 说明与当前 `runtime.py`、`compatibility.py`、`data.py`、`web.py`、`labs.py`、Skill 文件及已安装的 ADK 2.13.0 生命周期实现核对；未修改运行代码。
- README 的 55 个代码围栏闭合：17 段 Python 均通过 AST 解析，且与本轮调整前的语法树一致；2 段 JSON、2 段 YAML 均解析通过，解析值保持一致。18 段 Bash 示例通过参数分词检查，真实股票基线及修改后命令均显式使用 `--discovery eager`。
- 43 处本地链接、图片路径及章节锚点检查通过；章节改名后的导航与 Registry 跳转有效。Markdown 表格结构正确，五个 lab 的 CLI 命令和 Web UI prompt 均保留；`git diff --check` 通过。
- 本轮仅调整文档，未重跑 pytest、Gemini 研究或行情抓取；前面的自动测试和真实运行记录保留其原有日期与验证范围。

## 2026-10-31 · 演讲主线、Trace 与 Registry

- README 按研究任务设计、Skill 分工、工具、Agent／Workflow／Runner、运行、Trace、参数归属、Registry 和改造实验重新组织；保留此前预检说明与五组 lab 的 CLI／Web 入口。运行实现与依赖未改动。
- README 的 65 个代码围栏闭合；26 段 Python 通过 AST 解析，20 段 Bash 通过 `bash -n`，2 段 JSON 与 2 段 YAML 通过解析。检查覆盖七份主文档的本地链接、章节锚点和表格结构，五段 Skill 原文引文与源文件逐字匹配。
- 技术复核对照本地 ADK 2.13.0：请求创建、指令与 State 注入、SkillToolset 请求处理、动态工具、Gemini SDK 调用与 LlmResponse 返回链路一致；规范化 UI 的 tool_call／tool_call_response 与原始 ADK Event 的 function_call／function_response 分别说明。requests.json 明确标为回调摘要。
- 重画 architecture.svg，新增 request-pipeline.svg。两图通过 XML 解析，经 sharp 渲染 PNG 并逐张目视检查；临时预览留在 `/tmp`，未替代或伪造原有真实 Trace 截图。
- `doctor`：ADK 2.13.0，五个核心 Skill 均为 SUPPORTED。`offline-check`：model_called=false，technical／catalyst／review 与数据、指标、目标周构造通过；保留预期的生命周期实验功能提示。
- 已用本地 API 签名确认 GCPSkillRegistry 的 project_id／location／credentials 参数，SkillToolset 默认 LAZY，SkillLifecycleConfig 默认 PERSISTENT、BOUNDED 上限 5。Google Cloud Agent Registry 的注册、ADC、角色、版本和下载说明已查阅官方文档；没有启用 API、创建资源或接入云 Registry。
- `adk web --help` 与本地 CORS 实现确认 --allow_origins 支持 regex 前缀；README 与讲师备忘补充用户指定的 Cloud Shell 命令。Cloud Shell／Web Preview 端到端仍未验证。
- `git diff --check` 通过。本轮只更新文档与 SVG，未调用 Gemini，未重复全量代码回归；此前 28 passed 的运行事实保留在本文件上方。

## 2026-10-31 · 为什么使用 ADK

- README 第 01 节新增 Codex／Claude Code + Skills 与 ADK 的选择说明，放在 ADK 定义之后、核心组件之前。三角色顺序、State 传递、证据校验、合成数据 HOLD 和预算规则已与 `stock_research/runtime.py` 核对。
- 查阅 ADK Technical Overview、OpenAI 官方 Skills／Codex SDK 文档与 Anthropic Agent SDK 概览；保留现成 Agent 可直接运行合适 Skills、两种 SDK 也能构建应用的说明，未将业务校验和预算限制归为 ADK 自动提供的功能。
- README 的 65 个代码围栏内容与本轮修改前逐字一致；新增概念说明顺序、Markdown 标题间距与围栏闭合检查通过，`git diff --check` 通过。
- 本轮仅修改 README、进度和验证记录，未运行 pytest、Gemini 或行情抓取。

## 2026-10-31 · README 精简与截图指引

- 第 04 节突出 ADK 的 Skill 支持边界和可复用的应用检查；offline-check 删除代码摘录。第 07 节改为 Web UI 操作；第 08 节只保留 Discovery，详细配置、生命周期与 SDK 边界转入实现参考。同步讲师说明、开发约定、图片来源与相关链接。
- 七份 Markdown 的本地链接、锚点、代码围栏和表格检查通过；Python 摘录通过 AST 解析，Bash 通过 bash -n，JSON／YAML 通过解析。五段 Skill 引文仍与源文件匹配，五个 lab 在主文档或实现参考中均保留 CLI／Web 入口。
- 四张标注 SVG 通过 XML 解析和 sharp PNG 渲染，并逐张目视检查红圈位置。SVG 嵌入的 PNG 与原始 trace-workflow.png／trace-request.png／trace-lazy.png 逐字节一致，仅裁剪显示区域和叠加操作标记。
- 检查确认第 07 节没有源码或命令片段，第 08 节不再包含参数归属表和生命周期正文；git diff --check 通过。运行实现和依赖未修改，未重跑 pytest、Gemini 或行情抓取。

## 2026-10-31 · 英文 README 活动快照

- 新增 `README.en.md`，完整翻译现有 11 节，标题层级与 11 个显式章节锚点保持一致；中英文 README 提供互相切换的语言入口。按用户后续要求，维护规则只记录在 AGENTS.md 等内部文档，不在中英文 README 中声明。
- 53 个代码块顺序与类型匹配：20 段 Python 的 AST 与中文版本一致；18 段 Bash 逐字一致并通过 `bash -n`；2 段 JSON、1 段 YAML 的解析值一致。Skill 原文节选标明为英文译文。
- README、英文版、AGENTS、progress 与本文共 106 处本地链接及锚点检查通过；原有外链与 8 处图片引用保留，图片文件未改动。英文正文无遗漏的中文段落，保留实现参考中已有的中文锚点。
- 9 条中英文 Web prompt 通过现有 `parse_prompt()`，解析结果逐项一致。只进行文档检查与确定性参数解析，未重跑 pytest、Gemini 研究或行情抓取。

## 2026-10-31 · 前置阅读入口

- 中文 README 在 English 下方、正文之前增加推荐前置阅读链接；链接文字为“Workshop: 用 ADK 玩转 Skill”，目标地址使用用户提供的飞书 URL。位置、Markdown 格式与 `git diff --check` 检查通过。
