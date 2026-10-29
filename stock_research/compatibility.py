"""Conservative, zero-token capability gate; never executes imported content."""
from __future__ import annotations
import hashlib
import json
import re
import shutil
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
TOOLS = {"read_evidence", "calculate_indicators"}

def fingerprint(folder: Path) -> str:
    digest = hashlib.sha256()
    for p in sorted(folder.rglob("*")):
        if p.is_symlink():
            raise ValueError(f"symbolic links are not accepted: {p.name}")
        if p.is_file():
            digest.update(p.relative_to(folder).as_posix().encode())
            digest.update(b"\0" + p.read_bytes())
    return digest.hexdigest()

def inspect_skill(folder: Path, *, script_backend: bool = False) -> dict:
    result = {"skill": folder.name, "status": "UNKNOWN", "reasons": [],
              "validation": "static only; not an execution guarantee"}
    try:
        files = list(folder.rglob("*"))
        if len(files) > 250 or sum(p.stat().st_size for p in files if p.is_file()) > 2_000_000:
            raise ValueError("file count/size exceeds workshop review limit")
        result["sha256"] = fingerprint(folder)
        text = (folder / "SKILL.md").read_text()
        parts = text.split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError("SKILL.md must start with YAML frontmatter")
        meta = yaml.safe_load(parts[1])
        from google.adk.skills import load_skill_from_dir
        load_skill_from_dir(folder)  # Parse with the installed ADK, not our own approximation.
        if meta.get("name") != folder.name:
            raise ValueError("directory must match frontmatter name")
        reasons = result["reasons"]
        tools = meta.get("metadata", {}).get("adk_additional_tools", [])
        missing = set(tools) - TOOLS
        if missing:
            reasons.append("missing registered tools: " + ", ".join(sorted(missing)))
        if re.search(r"\b(WebSearch|WebFetch|Bash|AskUserQuestion)\b|!`", text):
            reasons.append("host-specific tool/preprocessing syntax requires an adapter")
        if re.search(r"\b(playwright|puppeteer|selenium|MCP)\b|\b(?:pip|npm) install\b|浏览器自动化", text, re.I):
            reasons.append("browser, connector, or runtime installation requirements are not available in the default tool profile")
        if "disable-model-invocation" in meta or "allowed-tools" in meta:
            reasons.append("host-specific invocation/permission semantics require review")
        if re.search(r"desktop login|桌面登录|broker login", text, re.I):
            result["status"] = "UNSUPPORTED"
            reasons.append("this runtime has no desktop/broker login capability")
        scripts = [p for p in (folder / "scripts").rglob("*") if p.is_file()] if (folder / "scripts").exists() else []
        if scripts and not script_backend:
            reasons.append("scripts present; default runtime has no script executor")
        # Only recognized ADK resource roots are portable in this workshop.
        for reference in re.findall(r"(?:references|assets|scripts)/[\w./-]+", parts[2]):
            path = folder / reference.rstrip(".")
            if ".." in Path(reference).parts or not path.exists():
                reasons.append(f"resource missing or outside skill: {reference}")
        if result["status"] != "UNSUPPORTED":
            result["status"] = "ADAPTABLE" if reasons else "SUPPORTED"
        if not reasons:
            reasons.append("ADK parsing and known capability checks passed; semantic requirements may still need review")
    except Exception as exc:
        result["status"] = "UNSUPPORTED"
        result["reasons"].append(f"{type(exc).__name__}: {str(exc)[:300]}")
    return result

def scan(root: Path | None = None) -> list[dict]:
    root = root or ROOT / "skills"
    return [inspect_skill(p) for p in sorted(root.iterdir()) if p.is_dir() and not p.name.startswith(".")]

def accepted_skills():
    from google.adk.skills import load_skill_from_dir
    reports = scan()
    return {r["skill"]: load_skill_from_dir(ROOT / "skills" / r["skill"])
            for r in reports if r["status"] == "SUPPORTED"}, reports

def import_skill(source: Path) -> dict:
    source = source.resolve()
    report = inspect_skill(source)
    # Vendor is quarantine: importing never silently activates content.
    if any(p.is_symlink() for p in source.rglob("*")):
        raise ValueError("symlinked source rejected")
    if report["status"] == "UNSUPPORTED":
        return report
    dest = ROOT / "vendor" / "skills" / source.name
    if dest.exists():
        if fingerprint(dest) == fingerprint(source):
            return report | {"installed_to":str(dest),"activated":False,"already_present":True}
        raise ValueError("vendor destination exists; choose a new name/version")
    shutil.copytree(source, dest)
    (dest.parent / f"{source.name}.inspection.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report | {"installed_to": str(dest), "activated": False}
