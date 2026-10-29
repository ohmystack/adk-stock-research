"""Execute real ADK tools without an LLM. These are controlled experiments."""
from __future__ import annotations
import json
from .compatibility import ROOT, accepted_skills
from .runtime import environment

async def context(agent, invocation="turn-1", state=None, artifacts=None):
    from google.adk.agents.invocation_context import InvocationContext
    from google.adk.sessions import InMemorySessionService
    from google.adk.tools.tool_context import ToolContext
    service = InMemorySessionService()
    session = await service.create_session(app_name="lab", user_id="group", state=state or {})
    return ToolContext(InvocationContext(agent=agent, session=session, session_service=service,
        invocation_id=invocation, artifact_service=artifacts))

async def lab(name: str) -> dict:
    environment()
    from google.adk.agents import LlmAgent
    from google.adk.tools.skill_toolset import SkillToolset, SkillDiscoveryMode, SkillLifecycleConfig, SkillLifecycleMode
    from google.adk.models.llm_request import LlmRequest
    from google.adk.skills import models, load_skill_from_dir
    skills, _ = accepted_skills()
    agent = LlmAgent(name="lab_agent", model="gemini-3.8-flash")
    result = {"lab":name,"execution":"real ADK tools; programmatic control, no model request"}
    async def call(ts, ctx, tool_name, args):
        t = next(t for t in await ts.get_tools(ctx) if t.name == tool_name)
        return await t.run_async(args=args, tool_context=ctx)
    if name == "discovery":
        result["modes"] = {}
        for mode in SkillDiscoveryMode:
            ts = SkillToolset(skills=list(skills.values()),discovery_mode=mode)
            ctx = await context(agent)
            request = LlmRequest()
            await ts.process_llm_request(tool_context=ctx,llm_request=request)
            tools = [t.name for t in await ts.get_tools(ctx)]
            result["modes"][mode.value] = {"tools":tools,"system_instruction":request.config.system_instruction}
            await ts.close()
    elif name == "lifecycle":
        def risk_probe() -> str:
            """A tool available only while the risk skill is active."""
            return "risk checked"
        def report_probe() -> str:
            """A tool available only while the report skill is active."""
            return "report ready"
        variants = [models.Skill(frontmatter=models.Frontmatter(name=n,description=n,
            metadata={"adk_additional_tools":[tool]}),instructions=f"Use {tool} to perform {n}.")
            for n,tool in [("lab-risk","risk_probe"),("lab-report","report_probe"),("lab-glossary","risk_probe")]]
        ts = SkillToolset(skills=variants,additional_tools=[risk_probe,report_probe],
            lifecycle_config=SkillLifecycleConfig(default_mode=SkillLifecycleMode.BOUNDED,max_active_skills=1,
                skill_overrides={"lab-glossary":SkillLifecycleMode.EPHEMERAL}))
        ctx = await context(agent)
        steps = []
        async def snapshot(label, c):
            steps.append({"step":label,"active":ts.list_active_skills(c),"tools":[t.name for t in await ts.get_tools(c)]})
        loaded = await call(ts,ctx,"load_skill",{"skill_name":"lab-risk"})
        await snapshot("load risk",ctx)
        await call(ts,ctx,"load_skill",{"skill_name":"lab-report"})
        await snapshot("load report; bounded cap evicts risk",ctx)
        from google.genai import types
        request = LlmRequest(contents=[types.Content(role="model",parts=[types.Part.from_function_call(name="load_skill",args={"skill_name":"lab-risk"})]),
            types.Content(role="user",parts=[types.Part.from_function_response(name="load_skill",response=loaded)])])
        await ts.process_llm_request(tool_context=ctx,llm_request=request)
        result["pruned_history"] = request.contents[-1].parts[0].function_response.response
        await call(ts,ctx,"load_skill",{"skill_name":"lab-glossary"})
        await snapshot("ephemeral loaded in turn 1",ctx)
        # Carry pending state deltas across the explicit invocation boundary.
        ctx2 = await context(agent,"turn-2",ctx.state.to_dict())
        await snapshot("turn 2; ephemeral expired",ctx2)
        await call(ts,ctx2,"unload_skill",{"skill_name":"lab-report"})
        await snapshot("explicit unload",ctx2)
        result["steps"] = steps
        await ts.close()
    elif name == "registry":
        from google.adk.skills.skill_registry import SkillRegistry
        class LocalRegistry(SkillRegistry):
            async def get_skill(self, *, name): return skills[name]
            async def search_skills(self, *, query):
                return [s.frontmatter for s in skills.values() if query.lower() in (s.name+" "+s.description).lower()][:3]
        ts = SkillToolset(registry=LocalRegistry())
        ctx = await context(agent)
        result["search"] = await call(ts,ctx,"search_skills",{"query":"risk"})
        result["loaded"] = await call(ts,ctx,"load_skill",{"skill_name":"risk-review"})
        await ts.close()
    elif name in {"artifacts", "sizing"}:
        from google.adk.artifacts import InMemoryArtifactService
        from google.adk.code_executors.unsafe_local_code_executor import UnsafeLocalCodeExecutor
        service = InMemoryArtifactService()
        skill_name = "metrics-export" if name == "artifacts" else "position-sizer-adk"
        script_skill = load_skill_from_dir(ROOT / "extensions" / skill_name)
        # Deliberate opt-in to this bundled, tiny, reviewed script, not arbitrary imported skills.
        ts = SkillToolset(skills=[script_skill],code_executor=UnsafeLocalCodeExecutor(),save_output_artifacts=True)
        ctx = await context(agent,artifacts=service)
        await call(ts,ctx,"load_skill",{"skill_name":skill_name})
        arguments = {"skill_name":skill_name,"file_path":"scripts/export.py" if name == "artifacts" else "scripts/position_sizer.py"}
        if name == "sizing": arguments["args"] = ["--account-size","10000","--entry","100","--stop","95","--risk-pct","1"]
        result["execution_result"] = await call(ts,ctx,"run_skill_script",arguments)
        names = await service.list_artifact_keys(app_name="lab",user_id="group",session_id=ctx.session.id)
        result["saved"] = {}
        for filename in names:
            item = await service.load_artifact(app_name="lab",user_id="group",session_id=ctx.session.id,filename=filename)
            result["saved"][filename] = item.inline_data.data.decode() if item.inline_data else str(item)
        if not names: raise ValueError("script ran but no native Artifact was saved")
        await ts.close()
    else: raise ValueError("unknown lab")
    out = ROOT / "runs" / f"lab-{name}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,default=str))
    return result
