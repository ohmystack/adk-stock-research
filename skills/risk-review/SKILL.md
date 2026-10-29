---
name: risk-review
description: Review risk, conflicting evidence and confidence in stock research.
metadata:
  adk_additional_tools: ["read_evidence"]
---

# risk-review

先调用 read_evidence(context) 与 read_evidence(news)。阅读两位分析师的结构化输出，检查引用、冲突、时效和反证。没有新闻不得高信心；证据不足为 HOLD、low；合成数据为 unknown 趋势。信心不是上涨概率。
