# AgentSRS

A multi-agent LLM framework for automated software requirements quality analysis.
Extends **ReCompGPT** (Sheng, Wang & Liu — IEEE TSE Vol 51, Dec 2025) from
single-attribute completeness detection to a modular 4-agent pipeline covering
**completeness + ambiguity detection**, with a live web frontend and a full
evaluation suite.

---

## Architecture

`
Input Requirement
      |
      v
[Agent 1 — Understanding]    Extracts actor / action / condition / type (functional vs NFR)
      |
      v
[Agent 2A — Completeness]    Compares informal description vs formal spec (ReCompGPT M-C method)
[Agent 2B — Ambiguity]       Classifies ambiguity per ISO/IEC/IEEE 29148 taxonomy
      |
      v
[Agent 3 — Refinement]       Rewrites the requirement fixing all detected issues
      |
      v
[Report Module]              Pure Python aggregation — NOT an LLM agent
`

All agents use openai/gpt-oss-20b via Groq. Structured JSON output enforced at
every step.

---

## Setup

`ash
# 1 — Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/macOS

# 2 — Install dependencies
pip install -r requirements.txt

# 3 — Configure API keys
cp .env.example .env
# Edit .env and add your Groq API key (free at https://console.groq.com)
`

---

## Running

### Web frontend (recommended for demo)

`ash
uvicorn backend.api:app --reload --port 8000
# Open http://localhost:8000
`

Three tabs:
- **Single Requirement** — paste one requirement + optional description, see live agent trace
- **Full SRS File** — upload a .txt file (one requirement per line), analyse all at once
- **Evaluation Results** — static display of Study 1 & 2 results

### File format for full SRS upload

`
# Spec only (weaker completeness check):
The system shall allow a user to log in.

# Paired description + spec (recommended — enables ReCompGPT M-C method):
Users should be able to log in with email and password. If wrong credentials are entered they should be told. || The system shall allow a user to log in using their email and password.
`

### Command-line pipeline

`ash
python -m backend.main backend/data/sample_srs_with_description.txt groq
`

---

## Evaluation

Results from all three studies are saved under ackend/experiments/results/.

`ash
# Show saved evaluation results (instant)
.\eval.bat --show

# Show including PURE dataset Study 3
.\eval.bat --show --pure

# Re-run Study 1 + 2 (takes ~25 min, requires API keys)
.\eval.bat groq --force

# Run PURE dataset Study 3 (takes ~45 min first run, ~5 min for judge-only re-run)
.\eval.bat --pure groq
`

### Results summary

| Setting | Multi-Agent F1 | Single-Prompt F1 | Verdict |
|---|---|---|---|
| **Ambiguity** (n=30) | **0.941** | 0.727 | Multi-agent wins +0.214 |
| Completeness, description mode (n=10) | 0.824 | 0.875 | Comparable — both recall=1.0 |
| Completeness, spec-only (n=30) | 0.080 | 0.833 | Disclosed limitation (no description) |
| PURE benchmark match rate (n=102) | 74.5% | 79.4% | Below ReCompGPT GPT-4o (81.4%) |
| PURE branch gaps (n=20) | **60.0%** | 55.0% | Multi-agent wins on conditional gaps |

### PURE Dataset (Study 3)

Download from Zenodo (doi.org/10.5281/zenodo.15879027) and place as
ackend/data/ReGen.zip. The evaluation script loads it automatically.

**Note on metric:** Detection rate (did the model flag anything missing?) is NOT
comparable to ReCompGPT pass@k. We use an LLM-as-judge step to verify whether
the predicted gap semantically matches the specific removed requirement — this is
the correct metric.

---

## Project structure

`
backend/
  llm/client.py                  Unified LLM client — Groq with multi-key rotation
  agents/
    understanding_agent.py       Agent 1 — structural decomposition
    quality_agent.py             Agent 2 — completeness + ambiguity checks
    refinement_agent.py          Agent 3 — requirement rewriter
    report_module.py             Aggregation module (pure Python, not LLM)
  experiments/
    run_full_eval.py             Studies 1 & 2 — ablation + description mode
    run_pure_eval.py             Study 3 — PURE benchmark with LLM-as-judge
    single_prompt_baseline.py    Single-prompt ablation baseline
    results/                     Saved evaluation results (JSON)
  data/
    sample_srs_with_description.txt   Demo sample (description || spec format)
    demo_srs_showcase.txt             5-requirement showcase file
  main.py                        CLI pipeline runner
  api.py                         FastAPI app with CORS
frontend/
  index.html                     Single-file frontend (no build step)
eval.bat                         Windows helper to run evaluation studies
requirements.txt
.env.example                     Template for API key configuration
`

---

## Base paper

Sheng, J., Wang, Q. & Liu, Y. (2025). *ReCompGPT: An NL2NL Framework for
Automated Requirements Completeness Checking.* IEEE Transactions on Software
Engineering, Vol. 51.
DOI: [10.1109/TSE.2025.3613507](https://doi.org/10.1109/TSE.2025.3613507)

Section IX of the paper explicitly states: *"We also consider incorporating
agents into our method"* — direct justification for this work.
