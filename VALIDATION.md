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
