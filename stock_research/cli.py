from __future__ import annotations
import argparse
import asyncio
import json
import re
import sys
from pathlib import Path
from .compatibility import ROOT, scan, import_skill
from .runtime import environment

def main():
    environment()
    p = argparse.ArgumentParser(description="Gemini × ADK Skills Workshop")
    sub = p.add_subparsers(dest="command",required=True)
    sub.add_parser("doctor")
    sub.add_parser("offline-check")
    r = sub.add_parser("run")
    r.add_argument("--mode",choices=["fixture","live"],default="fixture")
    r.add_argument("--ticker",default="DEMO")
    r.add_argument("--discovery",choices=["eager","lazy"],default="eager")
    r.add_argument("--max-calls",type=int,help="Lower the configured per-run call limit")
    r = sub.add_parser("fetch"); r.add_argument("--ticker",default="GOOGL"); r.add_argument("--refresh",action="store_true")
    r = sub.add_parser("lab"); r.add_argument("name",choices=["discovery","lifecycle","registry","artifacts","sizing"])
    r = sub.add_parser("import-skill"); r.add_argument("path",type=Path)
    args = p.parse_args()
    try:
        if args.command == "doctor":
            import os
            import importlib.metadata as m
            result = {"python":sys.version.split()[0],"adk":m.version("google-adk"),
                "gemini_key_present":bool(os.getenv("GEMINI_API_KEY")),"proxy_enabled":bool(os.getenv("LOCAL_PROXY")),
                "skills":scan(),"note":"static capability checks; no model request"}
        elif args.command == "lab":
            from .labs import lab
            result = asyncio.run(lab(args.name))
        elif args.command == "import-skill": result = import_skill(args.path)
        elif args.command == "offline-check":
            from .data import load_bundle
            from .runtime import build_team
            bundle = load_bundle("fixture","DEMO")
            team, toolsets, reports, model = build_team(bundle,"eager")
            result = {"check":"ADK team construction, accepted skills, deterministic indicators and calendar",
                "model_called":False,"agents":[a.name for a in team.edges[0][1:]],"indicators":bundle["indicators"],"target_week":bundle["target_week"],"skills":reports}
            async def close():
                for t in toolsets.values(): await t.close()
            asyncio.run(close())
        else:
            from .data import load_bundle
            if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,14}",args.ticker): raise ValueError("invalid US ticker")
            if args.command == "fetch":
                b = load_bundle("live",args.ticker,refresh=args.refresh)
                result = {k:v for k,v in b.items() if k != "prices"}
            else:
                from .runtime import run
                bundle = load_bundle(args.mode,args.ticker)
                result = {"output":str(asyncio.run(run(bundle,args.discovery,args.max_calls)))}
        print(json.dumps(result,ensure_ascii=False,indent=2,default=str))
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}",file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__": sys.exit(main())
