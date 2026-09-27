# AgentSRS — File Map

**Audit date:** 2026-09-27

---

## Directory Tree

```
agentsrs/
│
├── .env                                         [gitignored]
├── .env.example
├── .gitignore
├── eval.bat
├── judge_check.py
├── README.md
├── requirements.txt
├── ReCompGPT_An_NL2NL_Framework_for_Automated_Requirements_Completeness.pdf  [gitignored]
│
├── .vscode/
│   └── settings.json
│
├── backend/
│   ├── __init__.py
│   ├── api.py
│   ├── main.py
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── quality_agent.py
│   │   ├── refinement_agent.py
│   │   ├── report_module.py
│   │   └── understanding_agent.py
│   │
│   ├── data/
│   │   ├── demo_srs_showcase.txt
│   │   ├── eval_set.csv
│   │   ├── eval_set_backup_20items.csv          [LEGACY]
│   │   ├── eval_set_completeness_with_description.csv
│   │   ├── ReGen.zip
│   │   ├── sample_srs.txt
│   │   ├── sample_srs_with_description.txt
│   │   └── pure_dataset/
│   │       ├── Access Module.json
│   │       ├── Audit Module.json
│   │       ├── Citizen Interface.json
│   │       ├── evaluation.py                   [LEGACY]
│   │       ├── re_data.json
│   │       ├── README.md
│   │       └── Shopping Cart.json
│   │
│   ├── experiments/
│   │   ├── __init__.py
│   │   ├── run_description_eval.py             [LEGACY]
│   │   ├── run_evaluation.py                   [LEGACY]
│   │   ├── run_full_eval.py
│   │   ├── run_pure_eval.py
│   │   ├── single_prompt_baseline.py
│   │   └── results/
│   │       ├── ablation_60.json                [LOCKED]
│   │       ├── desc_10.json                    [LOCKED]
│   │       ├── pure_102.json                   [LOCKED]
│   │       └── pure_summary.json               [LOCKED]
│   │
│   └── llm/
│       ├── __init__.py
│       └── client.py
│
├── docs/
│   ├── FILE_MAP.md                             (this file)
│   ├── HOW_TO_RUN.md
│   └── PROJECT_OVERVIEW.md
│
└── frontend/
    └── index.html
```

---

## File Table

| File | Size | Status | Description |
|------|------|--------|-------------|
| `.env` | 912 B | **Gitignored** | API keys (Groq). Never commit. |
| `.env.example` | 368 B | Active | Template for `.env`. Committed. |
| `.gitignore` | 238 B | Active | Excludes `.env`, `.conda/`, `*.pdf`, `__pycache__`. |
| `.vscode/settings.json` | 135 B | Active | Editor settings. Not project-critical. |
| `backend/__init__.py` | 0 B | Active | Package marker. |
| `backend/agents/__init__.py` | 0 B | Active | Package marker. |
| `backend/agents/quality_agent.py` | 5149 B | Active | `QualityAgent`: `check_completeness()` and `check_ambiguity()`. Contains `COMPLETENESS_SYSTEM_PROMPT_WITH_DESCRIPTION`, `COMPLETENESS_SYSTEM_PROMPT_SPEC_ONLY`, `AMBIGUITY_SYSTEM_PROMPT`. |
| `backend/agents/refinement_agent.py` | 1138 B | Active | `RefinementAgent.run()`: rewrites a requirement to fix detected issues. |
| `backend/agents/report_module.py` | 1970 B | Active | `build_report()`: pure-Python aggregation, no LLM. `overall_score` is marked TODO (simple average). |
| `backend/agents/understanding_agent.py` | 1285 B | Active | `UnderstandingAgent.run()`: extracts actor/action/condition/type from raw requirement text. |
| `backend/api.py` | 2326 B | Active | FastAPI app. Routes: `/analyze-single` (`SingleRequest` model), file upload route. |
| `backend/data/demo_srs_showcase.txt` | 1459 B | Active | 5 `description\|\|spec` paired requirements for Tab 2 demo. Verified demo file. |
| `backend/data/eval_set.csv` | 10497 B | Active | 60-item ablation dataset (Study 1). Active. |
| `backend/data/eval_set_backup_20items.csv` | 3277 B | **Legacy** | 20-item backup of an earlier eval set. No longer referenced by current scripts. Safe to delete. |
| `backend/data/eval_set_completeness_with_description.csv` | 3511 B | Active | 10-item description-mode dataset (Study 2). Active. |
| `backend/data/pure_dataset/Access Module.json` | 729 B | Active | Part of local PURE dataset subset (4 documents extracted from ReGen.zip). |
| `backend/data/pure_dataset/Audit Module.json` | 1068 B | Active | Part of local PURE dataset subset. |
| `backend/data/pure_dataset/Citizen Interface.json` | 906 B | Active | Part of local PURE dataset subset. |
| `backend/data/pure_dataset/evaluation.py` | 15260 B | **Legacy** | Original PURE evaluation script from the dataset authors. Not called by current eval pipeline. |
| `backend/data/pure_dataset/re_data.json` | 136252 B | Active | Full PURE dataset in JSON (all 31 documents). Used by `run_pure_eval.py` and `judge_check.py`. |
| `backend/data/pure_dataset/README.md` | 8044 B | Active | PURE dataset documentation. |
| `backend/data/pure_dataset/Shopping Cart.json` | 701 B | Active | Part of local PURE dataset subset. |
| `backend/data/ReGen.zip` | 3385234 B | Active | Full PURE/ReGen dataset archive. Source for `run_pure_eval.py` and `judge_check.py`. |
| `backend/data/sample_srs.txt` | 322 B | Active | 3-line sample for CLI demo (spec-only format). |
| `backend/data/sample_srs_with_description.txt` | 693 B | Active | 3-line sample for CLI demo (`description\|\|spec` format). |
| `backend/experiments/__init__.py` | 0 B | Active | Package marker. |
| `backend/experiments/results/ablation_60.json` | 655 B | **Locked** | Study 1 saved results. |
| `backend/experiments/results/desc_10.json` | 289 B | **Locked** | Study 2 saved results. |
| `backend/experiments/results/pure_102.json` | 101962 B | **Locked** | Study 3 per-case results, 102 records, judge fields included. |
| `backend/experiments/results/pure_summary.json` | 1573 B | **Locked** | Study 3 summary metrics. |
| `backend/experiments/run_description_eval.py` | 3241 B / 90 lines | **Legacy** | Older standalone description-mode eval script. Not called by `eval.bat` or `run_full_eval.py`. Superseded by `run_full_eval.py`. Safe to archive. |
| `backend/experiments/run_evaluation.py` | 4781 B / 134 lines | **Legacy** | Older standalone ablation eval script. Not called by `eval.bat` or `run_full_eval.py`. Superseded by `run_full_eval.py`. Safe to archive. |
| `backend/experiments/run_full_eval.py` | 23987 B / 596 lines | Active | Runs Studies 1 and 2; `--show` flag displays saved results. Called by `eval.bat` when `--pure` is NOT the first arg. Imports `rich`. |
| `backend/experiments/run_pure_eval.py` | 26834 B / 554 lines | Active | Runs Study 3 (PURE benchmark + LLM-as-judge). Called by `eval.bat` when `--pure` IS the first arg. Imports `rich`. |
| `backend/experiments/single_prompt_baseline.py` | 1970 B / 51 lines | Active | `SinglePromptBaseline` class. Used by `run_full_eval.py` and `run_description_eval.py` as the comparison baseline. |
| `backend/llm/__init__.py` | 0 B | Active | Package marker. |
| `backend/llm/client.py` | 9709 B | Active | `LLMClient`: Groq provider, multi-key round-robin (`_rotate_key`), retry on JSON parse failure. Ollama code path exists but is not the active config. |
| `backend/main.py` | 10316 B | Active | CLI pipeline runner: `run_pipeline()`, `run_single()`, `run_pipeline_traced()`. |
| `docs/HOW_TO_RUN.md` | — | Active | Running instructions. (Sibling of this file.) |
| `docs/PROJECT_OVERVIEW.md` | — | Active | Project overview. (Sibling of this file.) |
| `eval.bat` | 203 B | Active | Routes: `--pure` as first arg → `run_pure_eval.py`; else → `run_full_eval.py`. Sets `PYTHONUTF8=1`. |
| `frontend/index.html` | 46946 B | Active | Entire web frontend, single file. Tab 1: `/analyze-single`. Tab 2: file upload. Tab 3: static eval results display. |
| `judge_check.py` | 6699 B | Active | Interactive spot-check tool for manually verifying judge decisions. Loads `pure_102.json` + `ReGen.zip`. |
| `README.md` | 5484 B | Active | GitHub-facing project README. |
| `ReCompGPT_An_NL2NL_Framework_for_Automated_Requirements_Completeness.pdf` | 2569135 B | **Gitignored** | Local copy of base paper. Gitignored (`*.pdf` rule). |
| `requirements.txt` | 87+ B | Active | `requests>=2.31`, `python-dotenv>=1.0`, `fastapi>=0.110`, `uvicorn>=0.29`, `python-multipart>=0.0.9`, `rich>=13.0`. |

---

## Files Flagged for Cleanup

| File | Reason |
|------|--------|
| `backend/data/eval_set_backup_20items.csv` | Legacy 20-item backup of an earlier eval set. No longer referenced by any current script. Safe to delete. |
| `backend/experiments/run_description_eval.py` | Older standalone description-mode eval script. Superseded by `run_full_eval.py`. Not called by `eval.bat`. Safe to archive. |
| `backend/experiments/run_evaluation.py` | Older standalone ablation eval script. Superseded by `run_full_eval.py`. Not called by `eval.bat`. Safe to archive. |
