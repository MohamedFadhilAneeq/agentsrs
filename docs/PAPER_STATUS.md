# AgentSRS — Paper Status

> **Last updated:** 2026-09-27. This is a status report, not a draft. Do not edit locked sections here — update this file to reflect actual current state.

---

## Current Status

| Component | Status |
|---|---|
| IEEE conference paper draft | **NOT STARTED** |
| Formal project report | **NOT STARTED** |
| Evaluation data (all 3 studies) | LOCKED and ready to use |
| Judge validation result | LOCKED (83%, 12 cases, 2026-09-26) |
| Threats-to-validity paragraph | Drafted — see below |

---

## Locked Sections

### Title
[TITLE TEXT NOT PROVIDED IN THIS SESSION — paste here when confirmed]

### Abstract
[ABSTRACT TEXT NOT PROVIDED IN THIS SESSION — paste here when confirmed]

> [!CAUTION]
> Do not reconstruct or paraphrase the abstract from memory. If the locked abstract was written in a prior session, retrieve it and paste the exact text here before using it anywhere.

---

## Ready Material (verified, locked)

### Headline result (unambiguous, no caveats needed)
- Ambiguity detection: Multi-Agent F1 **0.941** vs Single-Prompt **0.727**, delta **+0.214**
- This is the primary novel contribution. ReCompGPT does not attempt ambiguity detection.

### Completeness results (honest framing required)

| Study | n | Multi-Agent | Single-Prompt | Notes |
|---|---|---|---|---|
| Study 2 — description mode | 10 | F1 0.824, recall 1.000 | F1 0.875, recall 1.000 | Indicative only (n=10) |
| Study 3 — PURE benchmark | 102 | 74.5% match | 79.4% match ← wins overall | Both below ReCompGPT pass@1 81.4% |
| Study 3 — branch gaps | 20 | **60.0%** | 55.0% | Multi-agent wins this subset |
| Study 3 — L3 hard cases | 14 | **50.0%** | 42.9% | Multi-agent wins this subset |

**Honest framing required in the paper:**  
Single-prompt wins overall at n=102. Multi-agent wins specifically on branch/conditional gaps and hard L3 cases. Do not write "comparable" or "multi-agent wins completeness" — the correct sentence is: *"decomposition helps on structurally harder gaps, not uniformly."*

### Judge validation
- Manual spot-check: 12 stratified cases, 10/12 (83%) human agreement
- Errors balanced: 1 judge too lenient (medium conf), 1 judge too strict (high conf, synonym issue)
- No systematic directional bias detected

### Threats-to-Validity paragraph (ready to paste)
> *"A manual spot-check of 12 stratified judge decisions (6 matched, 6 rejected, spanning L1–L3 difficulty levels) found 83% human agreement with the LLM-as-judge. Of the two disagreements, one involved the judge accepting a thematically adjacent but semantically distinct prediction (too lenient, medium confidence); the other involved the judge rejecting a prediction that used a synonym found elsewhere in the same document (too strict, high confidence). The errors are in opposite directions, suggesting no systematic bias. This spot-check is a small-sample manual check, not a full inter-annotator study — the base paper used three human annotators with reported agreement scores; this work did not replicate that step due to resource constraints. The 74.5% match rate should be interpreted with this caveat."*

---

## Suggested Paper Structure (IEEE conference format)

Write sections in this order:

| # | Section | Key content | Ready? |
|---|---|---|---|
| 1 | Title | [locked — not available here] | — |
| 2 | Abstract | [locked — not available here] | — |
| 3 | Introduction | ReCompGPT Section IX gap quote; motivation for agents + ambiguity | Draft needed |
| 4 | Related Work | ReCompGPT, LLM-based RE tools, ambiguity detection literature | Draft needed |
| 5 | Methodology | 4-agent pipeline, system prompts (summarised), M-C method, LLM-as-judge design | Draft needed |
| 6 | Evaluation Setup | 3 datasets: eval_set.csv (60), description set (10), PURE (102); metrics | Draft needed |
| 7 | Results | Tables from RESULTS_REFERENCE.md; honest framing from above | Data ready |
| 8 | Discussion | Why multi-agent wins ambiguity; why single-prompt wins overall PURE; model-size gap | Draft needed |
| 9 | Threats to Validity | Paragraph above + spec-only limitation + n=10 + judge spot-check | Drafted |
| 10 | Conclusion | Summary + future work (action diffusion, larger judge validation) | Draft needed |

---

## Known Gaps Before Paper Can Be Submitted

- [ ] Abstract text — retrieve and paste into this file
- [ ] Title — retrieve and paste into this file  
- [ ] All 8 remaining sections — not drafted
- [ ] overall_score formula in report_module.py — either justify or explicitly exclude from paper claims