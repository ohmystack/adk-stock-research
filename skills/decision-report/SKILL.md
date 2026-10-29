---
name: decision-report
description: Write concise stock decision report with BUY SELL HOLD and uncertainty.
metadata:
  adk_additional_tools: ["read_evidence"]
---

# decision-report

读取 references/report-policy.md。综合已有技术分析和事件分析；输出严格符合 JSON schema 的最终建议。不要增加虚构证据编号；至少保留一个真实引用和一个失效条件。避免重复调用数据工具。
