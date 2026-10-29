---
name: data-quality
description: Check evidence freshness, complete trading bars, missing data and synthetic flags.
metadata:
  adk_inject_state: true
  adk_additional_tools: ["read_evidence"]
---

# data-quality

先调用 read_evidence(context) 和 read_evidence(prices)。检查截至时间、数据模式和样本数；合成数据只验证流程，不形成真实预测。缺失值明确写入 missing_data。不要把缺失解读成中性。

当前证券：{ticker}；证据截至：{as_of}。这是加载时的 state 注入快照。
