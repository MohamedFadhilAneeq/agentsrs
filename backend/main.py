"""AgentSRS pipeline orchestrator.

Supports an optional informal "description" per requirement, needed for the
real ReCompGPT-style completeness check (see quality_agent.py). Input file
format: each line is either
    plain requirement text                     (no description available)
or
    description text || requirement text       (paired -- enables the full check)

Run from the project root:
    python -m backend.main backend/data/sample_srs.txt groq
    python -m backend.main backend/data/sample_srs_with_description.txt groq
"""

import json
import sys
import time

from backend.llm.client import LLMClient
from backend.agents.understanding_agent import (
    UnderstandingAgent,
    SYSTEM_PROMPT as _UA_PROMPT,
)
from backend.agents.quality_agent import (
    QualityAgent,
    COMPLETENESS_SYSTEM_PROMPT_WITH_DESCRIPTION as _COMP_WITH_DESC,
    COMPLETENESS_SYSTEM_PROMPT_SPEC_ONLY as _COMP_SPEC_ONLY,
    AMBIGUITY_SYSTEM_PROMPT as _AMB_PROMPT,
)
from backend.agents.refinement_agent import (
    RefinementAgent,
    SYSTEM_PROMPT as _RA_PROMPT,
)
from backend.agents.report_module import build_report


def load_requirements(path: str) -> list[dict]:
    items = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            sep = " || "
            if sep in line:
                description, text = line.split(sep, 1)
                items.append({"text": text.strip(), "description": description.strip()})
            else:
                items.append({"text": line, "description": None})
    return items


def run_pipeline(srs_path: str, provider: str = "groq") -> dict:
    llm = LLMClient(provider=provider)
    understanding = UnderstandingAgent(llm)
    quality = QualityAgent(llm)
    refinement = RefinementAgent(llm)

    items = load_requirements(srs_path)
    context = "\n".join(item["text"] for item in items)

    results = []
    for item in items:
        req_text = item["text"]
        description = item["description"]

        structured = understanding.run(req_text)
        quality_findings = quality.run(req_text, structured, context, description=description)

        issues = {}
        if quality_findings["completeness"].get("complete") is False:
            issues["completeness"] = quality_findings["completeness"].get("issue")
        if quality_findings["ambiguity"].get("ambiguous") is True:
            issues["ambiguity"] = quality_findings["ambiguity"].get("issue")

        if issues:
            refined = refinement.run(req_text, issues)
        else:
            refined = {"improved_requirement": req_text, "changes_made": []}

        results.append(
            {
                "original": req_text,
                "description_used": description is not None,
                "structured": structured,
                "quality": quality_findings,
                "refined": refined,
            }
        )

    return build_report(results)


# -- Trace-aware functions (used by the transparency frontend) -----------------

def _run_single_impl(
    requirement_text: str,
    description,
    understanding: UnderstandingAgent,
    quality: QualityAgent,
    refinement: RefinementAgent,
) -> dict:
    """Run all agents on one requirement and return a full step-by-step trace."""
    trace = []

    # Step 1: Understanding Agent
    structured = understanding.run(requirement_text)
    trace.append({
        "step": "1",
        "agent": "Understanding Agent",
        "description": (
            "Extracts structural elements -- actor (who triggers), action (what the system does), "
            "condition (when/if it applies), and type (functional vs. non-functional) -- from "
            "the raw requirement text. Output is passed to both Quality sub-agents."
        ),
        "system_prompt": _UA_PROMPT,
        "user_prompt": requirement_text,
        "output": structured,
        "status": "error" if structured.get("_parse_error") else "ok",
        "status_label": "Parse Error" if structured.get("_parse_error") else "Done",
        "passes_to": "Quality Agent (both sub-checks)",
    })

    # Step 2A: Completeness
    if description:
        comp_sys = _COMP_WITH_DESC
        comp_user = (
            f"Description (informal source text):\n{description}\n\n"
            f"Specification (formal requirement):\n{structured}"
        )
        comp_mode = "description-vs-spec  (primary -- ReCompGPT M-C method)"
    else:
        comp_sys = _COMP_SPEC_ONLY
        comp_user = (
            f"Requirement: {structured}\n\n"
            f"Full requirement set for context:\n{requirement_text}"
        )
        comp_mode = "spec-only  (fallback -- no description provided)"

    comp_result = quality.check_completeness(structured, requirement_text, description)
    comp_issue = comp_result.get("complete") is False
    trace.append({
        "step": "2A",
        "agent": "Quality Agent -- Completeness Sub-Check",
        "description": (
            "Compares the informal description against the formal specification to find "
            "missing edge cases, unhandled conditions, or incomplete actions. Implements "
            "the ReCompGPT M-C gap detection method. Falls back to spec-set comparison "
            "when no description is available (weaker mode)."
        ),
        "mode": comp_mode,
        "system_prompt": comp_sys,
        "user_prompt": comp_user,
        "output": comp_result,
        "status": "issue" if comp_issue else "clean",
        "status_label": "Incomplete -- Issue Found" if comp_issue else "Complete",
        "passes_to": "Refinement Agent (issues dict)",
    })

    # Step 2B: Ambiguity
    req_type = structured.get("type")
    amb_user = f"Requirement: {requirement_text}\nType: {req_type or 'unknown'}"
    amb_result = quality.check_ambiguity(requirement_text, req_type)
    amb_issue = amb_result.get("ambiguous") is True
    trace.append({
        "step": "2B",
        "agent": "Quality Agent -- Ambiguity Sub-Check",
        "description": (
            "Detects language ambiguity grounded in ISO/IEC/IEEE 29148 quality attributes. "
            "Classifies into exactly one category: vague_term (e.g. fast, secure), "
            "missing_measurable_detail (implied metric with no number), "
            "multiple_interpretation (sentence reads two ways), or none."
        ),
        "system_prompt": _AMB_PROMPT,
        "user_prompt": amb_user,
        "output": amb_result,
        "status": "issue" if amb_issue else "clean",
        "status_label": (
            f"Ambiguous -- {amb_result.get('category', '').replace('_', ' ')}"
            if amb_issue else "Not Ambiguous"
        ),
        "passes_to": "Refinement Agent (issues dict)",
    })

    # Step 3: Refinement
    issues = {}
    if comp_issue:
        issues["completeness"] = comp_result.get("issue")
    if amb_issue:
        issues["ambiguity"] = amb_result.get("issue")

    if issues:
        ra_user = f"Original requirement: {requirement_text}\n\nDetected issues: {issues}"
        refined = refinement.run(requirement_text, issues)
        ra_status, ra_label = "ok", "Refined"
    else:
        ra_user = "(no issues detected -- refinement skipped)"
        refined = {"improved_requirement": requirement_text, "changes_made": []}
        ra_status, ra_label = "skipped", "Skipped -- No Issues Found"

    trace.append({
        "step": "3",
        "agent": "Refinement Agent",
        "description": (
            "Rewrites the requirement to resolve all detected quality issues while "
            "preserving original intent and scope. No new functionality is added. "
            "Skipped entirely when both Quality sub-checks pass."
        ),
        "system_prompt": _RA_PROMPT,
        "user_prompt": ra_user,
        "output": refined,
        "status": ra_status,
        "status_label": ra_label,
        "passes_to": "Report Module (aggregation)",
    })

    return {
        "original": requirement_text,
        "description": description,
        "trace": trace,
        "has_issues": bool(issues),
        "issues": issues,
        "_report_input": {
            "original": requirement_text,
            "description_used": description is not None,
            "structured": structured,
            "quality": {"completeness": comp_result, "ambiguity": amb_result},
            "refined": refined,
        },
    }


def run_single(requirement_text: str, description=None, provider: str = "groq") -> dict:
    """Run the full pipeline on one requirement and return trace + single-item report."""
    llm = LLMClient(provider=provider)
    result = _run_single_impl(
        requirement_text, description,
        UnderstandingAgent(llm), QualityAgent(llm), RefinementAgent(llm),
    )
    report = build_report([result.pop("_report_input")])
    return {**result, "report": report}


def run_pipeline_traced(srs_path: str, provider: str = "groq") -> dict:
    """Run the pipeline on every requirement in a file; return per-req traces + overall report."""
    llm = LLMClient(provider=provider)
    understanding = UnderstandingAgent(llm)
    quality = QualityAgent(llm)
    refinement = RefinementAgent(llm)

    items = load_requirements(srs_path)
    traced = []
    report_inputs = []

    for i, item in enumerate(items):
        result = _run_single_impl(
            item["text"], item["description"],
            understanding, quality, refinement,
        )
        report_inputs.append(result.pop("_report_input"))
        traced.append(result)
        if i < len(items) - 1:
            time.sleep(2)

    return {
        "requirements": traced,
        "report": build_report(report_inputs),
    }


if __name__ == "__main__":
    srs_path = sys.argv[1] if len(sys.argv) > 1 else "backend/data/sample_srs.txt"
    provider = sys.argv[2] if len(sys.argv) > 2 else "groq"
    report = run_pipeline(srs_path, provider=provider)
    print(json.dumps(report, indent=2))
