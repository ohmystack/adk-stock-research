---
name: position-sizer-adk
description: Calculate risk-based position sizing using the pinned upstream Python script.
---

# Position sizing · ADK adapter

Read references/sizing_methodologies.md with load_skill_resource. Use run_skill_script on scripts/position_sizer.py. Explicitly supply account-size, entry, stop, risk-pct as long options. The workshop lab uses synthetic inputs: 10000, 100, 95, 1. No quotes or broker access. This does not predict trends.

Adapted from tradermonty/claude-trading-skills, commit c9b84196a44a56a553293114fdae1f30bdd08c58. Script and reference unchanged; original MIT LICENSE included. Host-specific command instructions replaced with ADK tool instructions.
