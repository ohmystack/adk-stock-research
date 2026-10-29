# 讲师备忘 · 100 分钟

主屏使用 [README.md](README.md)，现场不要从实现文件开始讲。中文图示覆盖开场、ADK 入门、Skill 渐进披露、团队职责与生命周期。

## 会前

- 在固定版本完成一次 `doctor`、真实 Gemini fixture、live 和 `lab lifecycle`。
- 查看 [VALIDATION.md](VALIDATION.md)，区别本地已测与 Cloud Shell 未测。
- 每组一套 Key／项目配额；不是每人一把 Key 就有五份配额。
- 为五人组明确运行、方法、数据、验证、展示分工。
- 不在投影中打开 `.env`；展示 runs 中的报告与必要证据。
- 保留一个已成功的 fixture 结果作为明确标注的回放备份。

## 35 分钟讲解节奏

| 分钟 | 展示内容 | 核心提问 |
| --- | --- | --- |
| 0–4 | 一份完整报告、证据和反证 | 好报告为什么不只有“买入”？ |
| 4–10 | ADK 与 Skill 入门图、团队架构 | 模型、框架、方法与工具分别负责什么？ |
| 10–16 | discovery 实验 | 列表在哪里出现？延迟发现是否一定更省？ |
| 16–25 | lifecycle 图与真实实验输出 | 一轮有多少模型调用？卸载后什么还在？ |
| 25–31 | 真实运行 trace、state 注入、脚本 Artifact | 加载文字、启用工具、执行脚本是怎样接起来的？ |
| 31–35 | 改 Skill 的位置、组预算和失败路径 | 只换方法能改变什么，何时需要新 Tool？ |

2026 年 4 月前已有基本加载与脚本，9 月的发现／生命周期和 10 月的产物／追踪是本次重点。不要把基础概念都称作新特性。

## 必演示命令

在项目根目录，已配置 Key 后：

```bash
.venv/bin/python -m stock_research.cli doctor
.venv/bin/python -m stock_research.cli lab discovery
.venv/bin/python -m stock_research.cli lab lifecycle
.venv/bin/python -m stock_research.cli lab artifacts
.venv/bin/python -m stock_research.cli lab sizing
.venv/bin/python -m stock_research.cli run --mode fixture
```

前五项不调用模型；最后一项真实调用 Gemini。原生脚本工具与 Artifact 保存已能在没有模型的情况下验证，不必为了讲机制反复烧 token。

## 65 分钟观众实践

先得到报告，再理解 Discovery 和生命周期，最后换 Skill。慢组只完成默认任务与保守审查员挑战；快组做第三方导入、Registry 或真实 EAGER／LAZY 对照。

只换 SKILL.md 后运行即可，项目每次重新检查并记录哈希。若增加新 Skill，需要在角色配置中映射；这不需要重写 Agent 代码。

数据失败时显示真实原因。DEMO 是原创合成数据；它是机制练习，不是历史美股预测。live 的事件数据仅 RSS 标题，未核验全文，信心有上限。

## 机制实验的讲解边界

- lifecycle lab 直接调用真实 ADK 工具，不是 Gemini 自主发现能力。
- 原生程序化 `SkillToolset.load_skill` 与模型调用的 load_skill 工具不同：前者不自动把指令正文写入模型对话。
- max_active_skills 只限制 bounded；ephemeral 在下一 invocation 失效。
- 卸载不能清除已读参考资料、事实或产物；指令清理也不是安全撤权的完整替代。
- 当前 Artifact lab 用 code-executor 路径，不能直接推论 Environment 相同行为。
- UnsafeLocalCodeExecutor 不提供安全隔离；只给确定的小脚本实验启用。
- Registry lab 是本地关键词检索；托管 Registry、向量搜索和云端部署尚未纳入。

## 救场

| 阻塞 | 当场继续方式 |
| --- | --- |
| 配额／Key | 先完成所有无 Key 机制实验，再由组内主实例尝试一次真实调用 |
| 网络 | 使用固定输入；报告中明确标记 mode，不伪装实时 |
| 模型没加载 Skill | 展示失败 trace，讨论描述和接线；不把失败当成完成 |
| 时间不足 | 第三方与 Registry 选做；保住一个报告、一个机制对照、一个改造 |
| 不可用 Skill | 演示跳过原因，回到课程内五个小 Skill |

## 展示评价

要求每组讲清：改动、理由、执行证据、局限。对照必须固定输入，不能用两天不同的数据强行证明 Skill 更有效。信心不是预测概率，不按谁更激进或谁“猜中”未来排名。
