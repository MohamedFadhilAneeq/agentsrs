# AgentSRS — Results Reference

**Source:** Locked JSON files under `backend/experiments/results/`.
All numbers are sourced directly from those files. Do not edit without re-running the corresponding study.

---

## Study 1 — Ablation (60-item)

**Source file:** `backend/experiments/results/ablation_60.json`
**Run date:** 2026-08-21
**Dataset:** `backend/data/eval_set.csv` (self-constructed, n=60, 30 completeness + 30 ambiguity items)

### Completeness (n=30)

| System | Accuracy | Precision | Recall | F1 |
|--------|----------|-----------|--------|----|
| Multi-Agent | 0.233 | 0.250 | 0.048 | 0.080 |
| Single-Prompt | 0.733 | 0.741 | 0.952 | 0.833 |

### Ambiguity (n=30)

| System | Accuracy | Precision | Recall | F1 |
|--------|----------|-----------|--------|----|
| Multi-Agent | 0.933 | 0.941 | 0.941 | 0.941 |
| Single-Prompt | 0.600 | 0.593 | 0.941 | 0.727 |

---

## Study 2 — Description-Mode Completeness (10-item)

**Source file:** `backend/experiments/results/desc_10.json`
**Run date:** 2026-08-24
**Dataset:** `backend/data/eval_set_completeness_with_description.csv` (n=10)

| System | n | Accuracy | Precision | Recall | F1 |
|--------|---|----------|-----------|--------|----|
| Multi-Agent | 10 | 0.700 | 0.700 | 1.000 | 0.824 |
| Single-Prompt | 10 | 0.800 | 0.778 | 1.000 | 0.875 |

> **Note:** n=10 — treat as indicative only.

---

## Study 3 — PURE Benchmark (102 records)

**Source files:** `backend/experiments/results/pure_summary.json` + `backend/experiments/results/pure_102.json`
**Dataset:** PURE/ReGen benchmark (`backend/data/ReGen.zip`, `backend/data/pure_dataset/re_data.json`)
**Records:** 102 | **has_judge:** true

### Overall Results

| Metric | Multi-Agent | Single-Prompt |
|--------|-------------|---------------|
| Matched (human-aligned) | 76 / 102 = **74.5%** | 81 / 102 = **79.4%** |
| Pred: old/invalid detection rate | 95 / 102 = 93.1% | 95 / 102 = 93.1% |

**ReCompGPT baselines (for context):**

| Metric | Value |
|--------|-------|
| ReCompGPT pass@1 | 0.814 (81.4%) |
| ReCompGPT pass@3 | 0.938 (93.8%) |

> **Comparison note:** Both AgentSRS methods (multi-agent and single-prompt) are single-pass, so both should be compared against ReCompGPT **pass@1 (81.4%)**, not pass@3. pass@3 is listed for context only.

### Results by Level

| Level | n | Multi-Agent Matched | Single-Prompt Matched |
|-------|---|---------------------|-----------------------|
| L1 | 47 | 40 (85.1%) | 42 (89.4%) |
| L2 | 41 | 29 (70.7%) | 33 (80.5%) |
| L3 | 14 | 7 (50.0%) | 6 (42.9%) |

### Results by Gap Type

| Gap Type | n | Multi-Agent Matched | Single-Prompt Matched |
|----------|---|---------------------|-----------------------|
| action | 64 | 49 (76.6%) | 53 (82.8%) |
| action(obj) | 16 | 13 (81.3%) | 15 (93.8%) |
| action(constraint) | 1 | 1 | 1 |
| action(constraints) | 1 | 1 | 1 |
| branch | 20 | 12 (60.0%) ← **multi-agent wins** | 11 (55.0%) |

---

## Verification Status

| Study | Status | Notes |
|-------|--------|-------|
| Study 1 | **Locked.** Numbers sourced from JSON. | Dataset (`eval_set.csv`) is self-constructed. No independent replication. |
| Study 2 | **Locked.** Numbers sourced from JSON. | n=10 — treat as indicative only. |
| Study 3 | **Locked numerically.** | Judge validated by manual spot-check (2026-09-26): 12 stratified cases reviewed, 10/12 (83%) human agreement. Errors in both directions (1 judge too lenient, 1 judge too strict). Not a full inter-annotator study. |
