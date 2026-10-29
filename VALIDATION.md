# 本地验证记录

日期：2026-10-29（Asia/Shanghai）。使用 Python 3.12.8、ADK 2.13.0、Google Gen AI SDK 2.34.0、Gemini 3.8 Flash；模型后端为 **Google AI Studio Key / Gemini Developer API**。

## 已通过

| 范围 | 验证结果 |
| --- | --- |
| 安装入口 | `bash scripts/setup.sh` 在本机复核通过；支持复用现有环境，自动寻找 Python 3.11+ |
| 核心 Skill | 五个目录由真实 ADK 解析；工具、资源与能力检查通过 |
| 自动测试 | **16 passed**；覆盖指标、节假日目标周、缺失证据、虚构引用、原生工具、三角色状态传递与导入 |
| Discovery | 原生请求处理器验证 EAGER／LAZY 的目录与工具差异；无模型调用 |
| 生命周期 | bounded 淘汰、ephemeral 下一轮失效、显式卸载、历史指令替换均由真实 ADK 工具验证 |
| 原生脚本产物 | metrics-export 脚本生成文件，经 ArtifactService 保存、读回并核对内容 |
| 第三方适配 | position-sizer-adk 通过真实 ADK run_skill_script 执行；JSON／Markdown 原生 Artifact 读回通过；20 股计算符合预期 |
| npx | skills@1.7.4 + Node 24.22.1，在本机临时目录以 universal / copy 安装固定来源成功；实际目标 `.agents/skills/position-sizer` |
| npx → ADK | 从安装目录导入，识别为 ADAPTABLE，原因是默认运行配置无脚本后端；同内容导入幂等且不自动激活 |
| Registry | 原生 SkillRegistry 接口的本地关键词实现完成 search → load 验证 |
| 实时数据 | 通过指定代理取得 GOOGL 的 126 根完整日线和 Google News RSS 标题；目标交易周正确计算 |
| 文档资产 | 五张中文 SVG、合并后的 README 链接和 Markdown 结构检查 |

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
- 真实 Gemini 的完整 LAZY 三角色对照尚未执行；只验证了该模式的原生请求机制。活动前可用手册中的命令补测。
- 第三方适配版由 ADK 工具实际执行过，但尚未让 Gemini 自主选择并运行它。
- 托管 Google Cloud Skill Registry、向量检索、Vertex AI、Cloud Run、Web Preview 未纳入本地验收。
- 新闻只使用 RSS 标题；未来事件日历、新闻全文与权威公告核验还未接入。
- 港股／A 股、通用跨领域预设、模型短审查、复杂预测回测未实现；核心范围为美股研究和零 token 静态能力检查。
- 兼容性检查识别已知要求，不能证明任意第三方 Skill 的语义兼容或代码安全。
- 费用限制覆盖同一目录内的本项目运行，不能替代平台硬额度，也不能汇总其他程序的消费。

依赖当前有少量 pandas 的弃用提示，相关检查通过；Skills 实验开关提示属预期行为，未隐藏它们。
