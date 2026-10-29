import asyncio
import copy
import json
import pytest
from stock_research.compatibility import ROOT, inspect_skill, accepted_skills
from stock_research.data import load_bundle, indicators, target_week
from stock_research.runtime import validate_decision
from stock_research.labs import lab

def test_skills_parse_with_real_adk():
    skills, reports = accepted_skills()
    assert len(skills) == 5
    assert all(r["status"] == "SUPPORTED" for r in reports)

@pytest.mark.parametrize("name,status",[("needs-search","ADAPTABLE"),("needs-desktop","UNSUPPORTED"),("metrics-export","ADAPTABLE")])
def test_runtime_capability_mismatch(name,status):
    assert inspect_skill(ROOT/"extensions"/name)["status"] == status

def test_symlink_rejected(tmp_path):
    folder = tmp_path/"bad"; folder.mkdir()
    (folder/"SKILL.md").symlink_to(ROOT/"skills/data-quality/SKILL.md")
    assert inspect_skill(folder)["status"] == "UNSUPPORTED"

def test_indicators_and_invalid_bars():
    rows = [{"date":f"2026-{i//28+1:02d}-{i%28+1:02d}","open":100,"high":101,"low":99,"close":100,"volume":1000} for i in range(70)]
    result = indicators(rows)
    assert result["sma20"] == 100 and result["rsi14"] == 50 and result["atr14"] == 2
    rows[-1]["date"] = rows[-2]["date"]
    with pytest.raises(ValueError): indicators(rows)

def test_target_week_holiday():
    week = target_week("2026-11-20T18:00:00-05:00")
    assert week == {"start":"2026-11-23","end":"2026-11-27","sessions":4}

def decision():
    return {"analysis_status":"complete","trend":"up","action":"BUY","confidence_level":"high",
        "confidence_reason":"test","summary":"test","evidence_ids":["P1"],"counter_evidence":"test","invalidation_conditions":["test"]}

def test_fixture_cannot_publish_real_recommendation():
    d=validate_decision(decision(),load_bundle("fixture","DEMO"))
    assert (d.action,d.trend,d.confidence_level) == ("HOLD","unknown","low")

def test_unknown_citations_rejected():
    d=decision();d["evidence_ids"]=["invented"]
    with pytest.raises(ValueError): validate_decision(d,load_bundle("fixture","DEMO"))

def test_missing_news_caps_confidence():
    b=load_bundle("fixture","DEMO");b["synthetic"]=False;b["news"]=[]
    d=validate_decision(decision(),b)
    assert d.confidence_level == "medium" and d.analysis_status == "degraded"

def test_native_lifecycle_and_history_pruning():
    r=asyncio.run(lab("lifecycle"))
    assert r["steps"][1]["active"] == ["lab-report"]
    assert r["steps"][2]["active"] == ["lab-report","lab-glossary"]
    assert r["steps"][3]["active"] == ["lab-report"]
    assert r["steps"][4]["active"] == []
    assert r["pruned_history"]["status"] == "unloaded"

def test_native_discovery_and_registry():
    r=asyncio.run(lab("discovery"))["modes"]
    assert "list_skills" in r["lazy"]["tools"] and "list_skills" not in r["eager"]["tools"]
    r=asyncio.run(lab("registry"))
    assert r["loaded"]["skill_name"] == "risk-review"

def test_native_script_artifact_roundtrip():
    r=asyncio.run(lab("artifacts"))
    assert json.loads(r["saved"]["metrics.json"])["shares"] == 20

def test_third_party_adk_script_roundtrip():
    r=asyncio.run(lab("sizing"))
    reports=[json.loads(v) for k,v in r["saved"].items() if k.endswith(".json")]
    assert reports[0]["final_recommended_shares"] == 20

def test_import_is_idempotent_and_never_activates():
    from stock_research.compatibility import import_skill
    r=import_skill(ROOT/"vendor/skills/position-sizer")
    assert r["status"] == "ADAPTABLE" and not r["activated"] and r["already_present"]

def test_real_runner_with_scripted_model(tmp_path,monkeypatch):
    """Exercise actual ADK Runner, dynamic tools and state; zero network/token usage."""
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    from pydantic import PrivateAttr
    import stock_research.runtime as rt
    cfg=rt.config()
    class ScriptedModel(BaseLlm):
        role: str
        _step: int = PrivateAttr(default=0)
        async def generate_content_async(self,llm_request,stream=False):
            self._step+=1
            if self._step == 1:
                parts=[types.Part.from_function_call(name="load_skill",args={"skill_name":n}) for n in cfg["roles"][self.role]]
            elif self._step == 2:
                parts=[types.Part.from_function_call(name="read_evidence",args={"section":"context"})]
            else:
                value=decision() if self.role=="review" else {"summary":"test","evidence_ids":["P1"],"counter_evidence":"test","missing_data":[]}
                parts=[types.Part(text=json.dumps(value))]
            yield LlmResponse(content=types.Content(role="model",parts=parts))
    original=rt.build_team
    import google.adk.agents as agent_module
    original_agent = agent_module.LlmAgent
    def fake_agent(**kwargs):
        kwargs["model"] = ScriptedModel(model="scripted-test",role=kwargs["name"])
        return original_agent(**kwargs)
    monkeypatch.setattr(agent_module,"LlmAgent",fake_agent)
    import httpx
    async def no_network(*args,**kwargs):
        raise AssertionError("offline integration test must never use HTTP")
    monkeypatch.setattr(httpx.AsyncClient,"send",no_network)
    def build(*args):
        team,ts,reports,model=original(*args)
        return team,ts,reports,"scripted-test"
    monkeypatch.setattr(rt,"build_team",build)
    monkeypatch.setattr(rt,"config",lambda:cfg)
    monkeypatch.setattr(rt,"ROOT",tmp_path)
    monkeypatch.setenv("GEMINI_API_KEY","not-a-real-key")
    out=asyncio.run(rt.run(load_bundle("fixture","DEMO"),"eager"))
    d=json.loads((out/"decision.json").read_text())
    assert d["action"]=="HOLD" and d["provenance"]["model"]=="scripted-test"
    assert (out/"trace.json").exists() and not (tmp_path/"runs/.running").exists()
