# AgentSRS — Project Overview

> **Audit date:** 2026-09-27. All facts in this document are sourced from a verified filesystem and source-code audit. Where something is uncertain or unverified, it is explicitly marked.

---

## 1. What AgentSRS Is

AgentSRS is a multi-agent pipeline for analysing software requirements specifications (SRS). Given a requirement in natural-language text, the system runs it through a sequence of specialised LLM-backed agents that extract structured understanding, check for completeness and ambiguity, and produce a rewritten, improved requirement. Results are aggregated into a scored report by a pure-Python module (no LLM involved at that stage).

The system is exposed via a FastAPI backend (`backend/api.py`) and a single-file web frontend (`frontend/index.html`). It can also be driven from the command line through `backend/main.py`. The LLM layer (`backend/llm/client.py`) currently uses the Groq provider with multi-key round-robin rotation; an Ollama code path exists in the source but is not the active configuration.

The project was built to directly extend the research gap identified in the ReCompGPT paper (see Section 2 below). It adds ambiguity detection and a multi-agent decomposition that the base paper explicitly left as future work.

---

## 2. Base Paper and Research Gap

| Field | Detail |
|---|---|
| **Title** | ReCompGPT |
| **Authors** | Sheng, Wang & Liu |
| **Venue** | IEEE Transactions on Software Engineering (TSE), Vol 51, Dec 2025 |
| **DOI** | [10.1109/TSE.2025.3613507](https://doi.org/10.1109/TSE.2025.3613507) |

**Direct research gap (verbatim from Section IX of the paper):**
> *"We also consider incorporating agents into our method"*

This sentence is the stated motivation for AgentSRS: the base paper identified agent-based decomposition as a direction it did not pursue, and this project implements it.

### What the base paper does
- Completeness checking only
- Single-LLM pipeline
- Uses the **M-C (Missing-Component) method**: compares a requirement description against a specification to identify missing components
- Implements **action diffusion**: expands incomplete requirements by diffusing missing actions from surrounding context

### What AgentSRS adds beyond the base paper
- **Ambiguity detection** — novel addition not present in the base paper
- **Multi-agent decomposition** — separate agents for understanding, completeness, ambiguity, and refinement
- **Web frontend** — browser-based UI for interactive use

### What the base paper does that AgentSRS does NOT implement
- **Action diffusion** — the base paper's method of expanding incomplete requirements by diffusing missing actions from context is not implemented in AgentSRS. AgentSRS uses the M-C description-vs-spec comparison method from the paper but stops there; the diffusion step is absent.

---

## 3. Architecture

The pipeline runs in four sequential stages:

| Stage | File | Class / Function | Input | Output |
|---|---|---|---|---|
| **Stage 1** — Understanding | `backend/agents/understanding_agent.py` (28 lines) | `UnderstandingAgent.run(requirement_text)` | Raw requirement text | `{actor, action, condition, requirement_type}` |
| **Stage 2A** — Completeness | `backend/agents/quality_agent.py` (101 lines) | `QualityAgent.check_completeness(description, spec, req_type)` | Description, spec, req type | `{complete, issue, explanation}` |
| **Stage 2B** — Ambiguity | `backend/agents/quality_agent.py` (101 lines) | `QualityAgent.check_ambiguity(requirement_text, req_type)` | Requirement text, req type | `{ambiguous, issue, category, explanation}` |
| **Stage 3** — Refinement | `backend/agents/refinement_agent.py` (25 lines) | `RefinementAgent.run(original_text, issues)` | Original text + issues | `{rewritten_requirement}` |
| **Stage 4** — Report | `backend/agents/report_module.py` (49 lines) | `build_report(results)` | All stage results | Aggregated scores |

> [!NOTE]
> **Stage 4 is pure Python — no LLM call is made here.** `build_report` aggregates results from the previous stages. The `overall_score` field is explicitly marked TODO in the source at line 33 (comment: *'justify or replace'*; currently a simple average).

### Supporting files

| File | Purpose |
|---|---|
| `backend/llm/client.py` (234 lines) | `LLMClient` — Groq provider, `_rotate_key` for multi-key round-robin, `_generate_groq` and `_generate_ollama` methods |
| `backend/api.py` (74 lines) | FastAPI app — `SingleRequest` model for `/analyze-single`, `analyze_traced` for file upload, `analyze` for CLI |
| `backend/main.py` (275 lines) | `run_pipeline`, `run_single`, `run_pipeline_traced` |
| `frontend/index.html` (46 946 bytes) | Single-file web frontend |
| `eval.bat` | Routes `--pure` flag to `run_pure_eval`, else to `run_full_eval` |
| `judge_check.py` | Interactive judge spot-check tool (added 2026-09-26) |
| `requirements.txt` | `requests>=2.31`, `python-dotenv>=1.0`, `fastapi>=0.110`, `uvicorn>=0.29`, `python-multipart>=0.0.9` |

---

## 4. Implementation vs Base Paper

| Feature | AgentSRS | Base Paper (ReCompGPT) | Notes |
|---|---|---|---|
| M-C completeness check (description vs spec) | ✅ Implemented | ✅ Implemented | Core shared method |
| Ambiguity detection | ✅ Implemented | ❌ Not present | Novel addition in AgentSRS |
| Multi-agent decomposition | ✅ Implemented | ❌ Not present | Direct gap from Section IX |
| Web frontend | ✅ Implemented | ❌ Not present | Added for usability |
| Action diffusion | ❌ Not implemented | ✅ Implemented | Base paper expands incomplete requirements by diffusing missing actions from context; AgentSRS does not do this |
| Single-LLM pipeline | ❌ (replaced by multi-agent) | ✅ | By design |

---

## 5. Current Status

| Done ✅ | Not Done ❌ |
|---|---|
| Pipeline (all 4 stages) | IEEE conference paper draft — **NOT STARTED** |
| API (`backend/api.py`) | Formal written project report (graded deliverable for Review 2) — **NOT STARTED** |
| Web frontend (`frontend/index.html`) | |
| 3 evaluation studies | |
| Judge validation (`judge_check.py`) | |
| GitHub push | |
