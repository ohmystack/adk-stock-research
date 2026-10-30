# Sources & attribution

课程五个核心 Skill、实验脚本、SVG 图示与合成 DEMO 数据为本项目原创教学材料。行情不随仓库提供；使用者自行从数据提供方获取，并遵守其条款。

## ADK 官方组件图与 Web UI 截图

- `docs/images/adk-components.png` 来自 Google 的 [ADK Technical Overview](https://adk.dev/get-started/about/)，[原图](https://adk.dev/assets/adk-components.png)按原样保存，未修改。
- 上游 [google/adk-docs](https://github.com/google/adk-docs) 采用 [Apache License 2.0](https://github.com/google/adk-docs/blob/main/LICENSE)，许可证副本见 [ADK-LICENSE.txt](docs/images/ADK-LICENSE.txt)。
- `trace-workflow.png`、`trace-request.png`、`trace-lazy.png` 于 2026-10-30 从本机 ADK 2.13.0 Web UI 实际运行截取，使用 Gemini 3.8 Flash 和合成 DEMO 输入。分别展示顺序工作流与耗时、加载后的请求上下文、LAZY 发现步骤；未使用生成图片模拟界面。
- 截图中的框架界面来自 [google/adk-web](https://github.com/google/adk-web)，运行记录留在本机 `runs/`，不随仓库提交。

## Position Sizer · MIT

- 来源：[tradermonty/claude-trading-skills](https://github.com/tradermonty/claude-trading-skills)
- 固定 commit：`c9b84196a44a56a553293114fdae1f30bdd08c58`
- `vendor/skills/position-sizer/` 保存所需上游文件，完整 MIT 许可证见其中 LICENSE。
- `extensions/position-sizer-adk/` 保留原计算脚本与参考资料，只替换 SKILL.md 中的宿主操作说明，使用 ADK 原生工具。
- 上游 scripts/tests 未随包复制；本项目单独验证参数、产物与 ADK 执行链。
- 没有宣称上游原件已在 Gemini 上验证；本项目适配版的验证等级见 VALIDATION.md。

## Runtime dependencies

Google ADK、Google Gen AI SDK、yfinance、exchange-calendars 等依赖各自许可证适用。固定版本见 requirements.lock；项目通过包管理器安装，未把其源码复制到课程仓库。

## Primary references

- [ADK Skills](https://adk.dev/skills/)
- [ADK 2.13.0 Gemini adapter source](https://github.com/google/adk-python/blob/v2.13.0/src/google/adk/models/google_llm.py)
- [Google Cloud Agent Registry: setup](https://docs.cloud.google.com/agent-registry/setup)
- [Google Cloud Agent Registry: register skills](https://docs.cloud.google.com/agent-registry/register-skills)
- [Google Cloud Agent Registry: manage skill revisions](https://docs.cloud.google.com/agent-registry/manage-skill-revisions)
- [ADK 2.10 release: discovery / lifecycle](https://github.com/google/adk-python/releases/tag/v2.10.0)
- [ADK 2.12 release: script artifacts](https://github.com/google/adk-python/releases/tag/v2.12.0)
- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Vercel Skills CLI](https://github.com/vercel-labs/skills)
- [yfinance data-use notes](https://ranaroussi.github.io/yfinance/)
