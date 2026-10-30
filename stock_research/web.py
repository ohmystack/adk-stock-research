"""Prompt routing for ADK Dev UI; research uses the same runtime as the CLI."""
from __future__ import annotations

import asyncio
import json
import re

from google.adk.workflow import node
from google.adk.agents.context import Context
from google.genai import types

from .runtime import config, environment, run
from .compatibility import ROOT

LABS = {"discovery", "lifecycle", "artifacts", "registry", "sizing"}
HELP = """研究示例：
研究 mode=fixture ticker=DEMO discovery=eager，给出证据、反证和信心。
研究 mode=live ticker=GOOGL discovery=eager，给出证据、反证和信心。

机制实验（不调用模型）：lab discovery / lab lifecycle / lab artifacts / lab registry / lab sizing

每次研究使用 New Session；修改 Skill 后也使用新会话，隔离历史与激活状态。
"""


def parse_prompt(text: str) -> dict:
    text = text.strip()
    if text in {"help", "帮助"}: return {"command":"help"}
    match = re.fullmatch(r"lab\s+(\w+)", text)
    if match:
        if match[1] not in LABS: raise ValueError("未知机制实验。" + HELP)
        return {"command":"lab", "name":match[1]}
    pairs = re.findall(r"([A-Za-z_]+)\s*=\s*([A-Za-z0-9_.-]+)", text)
    params = dict(pairs)
    if len(params) != len(pairs) or set(params)-{"mode","ticker","discovery"}:
        raise ValueError("参数重复或包含未知参数。" + HELP)
    mode, ticker = params.get("mode"), params.get("ticker", "")
    discovery = params.get("discovery", config().get("discovery", "eager"))
    if mode not in {"fixture","live"} or discovery not in {"eager","lazy"}:
        raise ValueError("请明确指定 mode=fixture/live 和 discovery=eager/lazy。" + HELP)
    if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}", ticker) or (mode == "fixture" and ticker != "DEMO"):
        raise ValueError("fixture 使用 DEMO；live 使用美股代码。" + HELP)
    return {"command":"research", "mode":mode, "ticker":ticker, "discovery":discovery}


@node(rerun_on_resume=True)
async def workshop(ctx: Context):
    """Research team and controlled Skill experiments."""
    environment()
    text = " ".join(p.text for p in ((ctx.user_content.parts if ctx.user_content else []) or []) if p.text)
    try:
        args = parse_prompt(text)
        if args["command"] == "help":
            answer = HELP
        elif args["command"] == "lab":
            from .labs import lab
            result = await lab(args["name"])
            answer = ("代码控制的真实 ADK 工具实验；未调用模型。\n\n```json\n" +
                json.dumps(result, ensure_ascii=False, indent=2, default=str) + "\n```\n\n" +
                f"结果：runs/lab-{args['name']}.json")
        else:
            # A fresh session prevents previous evidence and active Skills from
            # contaminating before/after experiments. No routing LLM is needed.
            if ctx.state.get("research_started"):
                raise ValueError("本会话已运行过研究。点击 New Session 后发送研究 prompt。")
            ctx.state["research_started"] = True
            from .data import load_bundle
            bundle = await asyncio.to_thread(load_bundle, args["mode"], args["ticker"])
            out = await run(bundle, args["discovery"], web_context=ctx)
            answer = (out / "report.md").read_text() + f"\n\n运行记录：`{out.relative_to(ROOT)}`"
        return types.Content(role="model", parts=[types.Part(text=answer)])
    except Exception as exc:
        # Preserve native child events and partial run files; never render a
        # failed run as a validated final report.
        return types.Content(role="model", parts=[types.Part(text=f"运行未完成：{exc}")])


root_agent = workshop
