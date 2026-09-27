# AgentSRS — Limitations and Open Items

> **Audit date:** 2026-09-27. Every item below is verified against the real source files and evaluation results.

---

## 1. Known Disclosed Limitations

### 1.1 Completeness spec-only F1 = 0.080
**Source:** `ablation_60.json`, multi_agent completeness n=30  
**Status:** Expected by design. The completeness agent implements the ReCompGPT M-C method: it compares an informal description against the formal spec. Without a description, there is nothing to compare against. The agent correctly declines to speculate. This is not a bug — it is a disclosed constraint of the method.  
**Disclosed in:** evaluation results, frontend Tab 3 warn-box.

### 1.2 Study 2 n=10 (description-mode eval)
**Source:** `desc_10.json`  
**Status:** The description-mode completeness eval set has 10 items. Each single item shifts F1 by approximately 0.1. F1 0.824 (multi) and F1 0.875 (single) are indicative only. The recall=1.000 result (both methods catch every gap) is more robust than the F1 because it is not sensitive to precision variance at small n.  
**Disclosed in:** eval output labelled "indicative only."

### 1.3 PURE match rate below ReCompGPT pass@1 (74.5% vs 81.4%)
**Source:** `pure_summary.json`, `pure_102.json`  
**Status:** Expected. AgentSRS uses `openai/gpt-oss-20b` via Groq. ReCompGPT used GPT-4o. Both AgentSRS methods are single-pass, so both compare against pass@1 = 81.4% (not pass@3 = 93.8%). The gap is attributed to model capability, not pipeline design.  
**Disclosed in:** eval output and frontend Tab 3.

### 1.4 LLM-as-judge not fully human-verified
**Source:** `judge_check.py` spot-check result (2026-09-26)  
**Status:** The judge was validated by a manual spot-check of 12 stratified cases (6 matched, 6 rejected, spanning L1–L3). Human agreement: 83% (10/12). The two disagreements were in opposite directions (1 judge too lenient, 1 judge too strict) — no detected systematic bias. The base paper (ReCompGPT) used 3 human annotators with reported IAA scores; this project did not replicate that.  
**Threats-to-validity wording (ready to use):**  
> *"A manual spot-check of 12 stratified judge decisions found 83% human agreement with the LLM-as-judge (2 disagreements, balanced direction). This is a small-sample check, not a full inter-annotator study; unlike ReCompGPT which used 3 annotators, this work did not independently verify judge reliability at scale."*

### 1.5 overall_score is a placeholder
**Source:** `backend/agents/report_module.py` line ~33  
**Code comment:** `# TODO: justify or replace`  
**Status:** overall_score = simple average of completeness_score% and ambiguity_score%. The two dimensions are measured differently (one is a binary classification rate, the other derived from a different classification). Averaging them is unjustified. This field appears in the frontend report card but is not used in any evaluation claims.

### 1.6 Action diffusion not implemented
**Source:** ReCompGPT paper Section IV  
**Status:** The base paper includes an "action diffusion" step that expands incomplete requirements by diffusing missing actions from surrounding context. AgentSRS implements only the M-C (missing-component) comparison method. The diffusion step is absent. This is an explicit scope decision, not an oversight.

### 1.7 LLM non-determinism at temperature=0.2
**Status:** Even at temperature=0.2, the ambiguity agent returns different verdicts for the same input across runs. Observed in demo testing: the "upper threshold" example sometimes returns Unambiguous (~20% of runs). This is normal LLM behaviour. The evaluation F1 scores (measured over 30 cases) are robust to this variance; single-run demos are not.

### 1.8 Ollama code path unverified
**Source:** `backend/llm/client.py`  
**Status:** An Ollama provider code path (`_generate_ollama`) exists in the LLM client. The active configuration is Groq only. Whether Ollama works without code changes is unverified — it has not been tested in this project.

### 1.9 rich missing from requirements.txt (FIXED 2026-09-27)
**Source:** `requirements.txt`  
**Status:** FIXED. `rich>=13.0` added on 2026-09-27. Prior to this fix, a fresh install from requirements.txt would cause `eval.bat --show` to fail with an ImportError because `run_full_eval.py` and `run_pure_eval.py` both import `rich`. The `.conda` environment already had rich installed, masking this.

---

## 2. Open Items (Not Yet Done)

| Item | Status | Blocking? |
|---|---|---|
| IEEE conference paper draft | **NOT STARTED** | Yes — graded deliverable for Review 2 |
| Formal written project report | **NOT STARTED** | Yes — separate graded deliverable |
| Legacy eval scripts archived | Not done — `run_evaluation.py` and `run_description_eval.py` remain in `backend/experiments/` | No — safe to defer |
| overall_score formula justified | TODO in source — not resolved | No — not used in eval claims |
| Study 2 dataset size | 10 items; could be expanded | No — disclosed limitation |
| Ambiguity demo variance | LLM non-determinism; no fix available without deterministic model | No — disclosed |