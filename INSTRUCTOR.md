# 讲师备忘 · 100 分钟

主屏使用 [README.md](README.md)。正文顺序为 ADK／Skill → 环境 → 核心代码与预检 → CLI／Web 两种运行方式 → 首次研究与 Trace → Discovery／生命周期 → 修改方法与扩展。详细接线和检查规则保留在[实现参考](docs/implementation.md)。

## 会前

- 完成 `doctor`、`offline-check`，并通过 Web UI 运行一次 fixture 与 live。
- 启动 `.venv/bin/adk web web_agents --port 8000 --no-reload --no_use_local_storage`，选择 research。
- 保存成功运行的报告与 Trace 截图作为回放备份；重启 Web 服务后，内存中的 Session／Trace 不保留。
- 查看 [VALIDATION.md](VALIDATION.md)，区分本地已测与云端未测。
- 每组一套 Key／项目配额；不是每人一把 Key 就有五份配额。
- 不在投影中打开 `.env`，只展示报告与必要证据。

## 时间安排

| 时间 | 内容 | 产物 |
| --- | --- | --- |
| 00–8 分钟 | ADK、工具、Skill 与团队结构 | 理解方法与执行能力的区别 |
| 8–12 分钟 | 环境安装与 Key 配置 | 确认实验前提，不在此启动 UI |
| 12–25 分钟 | 核心代码、doctor／scan／offline-check、State 与 YAML | 解释检查、加载、数据流与复用方法 |
| 25–35 分钟 | 两种运行方式、首份报告、原生 Trace | 模型请求、调用过程、耗时 |
| 35–40 分钟 | EAGER／LAZY、生命周期 | 机制对照 |
| 40–55 分钟 | 环境与首次研究 | 每组一份报告 |
| 55–65 分钟 | Discovery、生命周期实验 | 状态变化记录 |
| 65–90 分钟 | 修改 Skill、固定输入对照 | 改动与执行证据 |
| 90–100 分钟 | 整理产物 | 报告、差异、关键截图 |

## 代码讲解重点

- 先说明 ADK 原生解析器负责什么，再展示项目在其上实现的能力画像、候选过滤和业务接线检查。
- doctor 是诊断报告，零退出码不代表所有方法可用；Key 存在不等于 API 验证。
- scan 逐个检查候选并保留理由，accepted_skills 才真正过滤加载；必需方法缺失时拒绝运行。
- offline-check 真正构造 ADK 团队但不调用模型，将数据／接线错误与模型执行错误分开。
- 结合 README 中的核心摘录、State 图与配置表讲复用入口，不到实验结尾再讲代码。

## UI 演示顺序

每次研究点击 **NEW SESSION**，隔离历史与 Skill 激活记录。已配置 Key 后，在 research 中发送：

```text
研究 mode=fixture ticker=DEMO discovery=eager，给出证据、反证、失效条件和信心。
```

1. 在最终 Markdown 报告中确认 fixture、HOLD、unknown、low；不要将前一条 review 的原始 JSON 误当成程序校验后的交付报告。
2. 切到 Traces，按 technical → catalyst → review 查看角色时序、模型和工具 span，观察总耗时及各段耗时。
3. 选择 technical 的模型 span，点击左侧 Event ID，再选 Request 输入箭头。折叠 system_instruction，展开 user_messages 中的 load_skill 返回，查看方法正文与 ticker／as_of 注入。
4. 对照该目录的 requests.json，查看加载前后工具声明。ADK 的 span Attributes 也包含工具定义与用量。
5. 新 Session 发送同一任务的 `discovery=lazy` 版本，找到各角色的 list_skills → load_skill；比较 requests 和 usage。
6. 新 Session 发送 README 的 live GOOGL prompt，核对真实来源、截至时间、目标交易周和标题证据降级。

正文仅保留三张真实截图：Workflow 耗时、加载后的请求内容、LAZY 目录调用；其他运行现场查看即可。

以下机制 prompt 可在 UI 直接发送，不调用 Gemini：

```text
lab discovery
lab lifecycle
lab sizing
lab artifacts
lab registry
```

每行独立发送。lab 输出由代码控制真实 ADK 工具操作，Trace 只有入口节点；不能把 JSON 中的状态序列称作模型自主决策。CLI 等价命令均在 README 对应步骤保留。

## 方法改造

每组可分工运行、Skill 设计、数据、验证、展示。完整模型研究从主实例串行发起。

先保留基线证据与报告，再修改 SKILL.md 或参考资料，执行 doctor／offline-check，在 UI 新建 Session 后发送同一基线 prompt。文件每次重新检查与构造，无需重启 Web 服务；修改 Python 代码才需重启。

添加 Skill 时需更新 roles 映射，同时检查 bounded 上限。比较两份 decision 的 data_sha256 与 Skill 哈希，防止把数据变化误归因于方法。

## 机制边界

- EAGER／LAZY 控制模型目录披露，本地 Skill 均先解析；LAZY 先 list 是项目 Prompt 的额外要求。
- max_active_skills 只限制 bounded；ephemeral 在下一 invocation 失效，一轮可包含多次模型调用。
- 卸载不清除已经读过的参考资料、事实、业务 State 或产物，也不删除目录。
- 脚本实验使用 code-executor 与 ArtifactService，UnsafeLocalCodeExecutor 不提供沙箱；只执行包内短脚本。
- Registry 是五个已检查 Skill 的本地关键词索引，无向量检索或托管服务。
- 原生 Trace 与项目保存的 requests／trace／usage 文件分别由框架和应用负责。

## 救场

| 阻塞 | 继续方式 |
| --- | --- |
| 配额／Key | 先完成无模型 lab，再由组内主实例尝试真实调用 |
| 网络／数据 | 显式切换 fixture，报告保留合成数据标记 |
| 模型跳过必要方法 | 查看失败 trace 和 requests，检查描述与角色要求 |
| UI 提示会话已研究 | 新建 Session，再发送 prompt |
| 时间不足 | 保留一个报告、一个机制对照、一个方法改造；扩展选做 |

展示要求：改动、理由、执行证据、局限。信心不是预测概率，不按未来收益排名。
