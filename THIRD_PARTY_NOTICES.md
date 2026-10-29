# Sources & attribution

课程五个核心 Skill、实验脚本、图示与合成 DEMO 数据为本项目原创教学材料。行情不随分发包提供；使用者自行从数据提供方获取，并遵守其条款。

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
- [ADK 2.10 release: discovery / lifecycle](https://github.com/google/adk-python/releases/tag/v2.10.0)
- [ADK 2.12 release: script artifacts](https://github.com/google/adk-python/releases/tag/v2.12.0)
- [Gemini pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Vercel Skills CLI](https://github.com/vercel-labs/skills)
- [yfinance data-use notes](https://ranaroussi.github.io/yfinance/)
