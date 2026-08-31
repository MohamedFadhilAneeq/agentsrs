"""
Draft evaluation harness for Review 2.

Runs BOTH the multi-agent pipeline and the single-prompt baseline against a
small, self-constructed evaluation set (backend/data/eval_set.csv), and
reports accuracy / precision / recall / F1 for completeness and ambiguity
detection separately, for both methods — this is the ablation comparison.

IMPORTANT — disclose this honestly in your report/paper:
This is a small (20-item), self-constructed, hand-labeled evaluation set,
built because the published ambiguity dataset (Talha, Tahir & Nadeem, 2025)
was not accessible in time. State this explicitly as a scoping decision.
This is a DRAFT-stage result — expand the set before your final submission.

Usage:
    python -m backend.experiments.run_evaluation groq
    python -m backend.experiments.run_evaluation local
"""

import csv
import json
import sys
import time

from backend.llm.client import LLMClient
from backend.agents.understanding_agent import UnderstandingAgent
from backend.agents.quality_agent import QualityAgent
from backend.experiments.single_prompt_baseline import SinglePromptBaseline


def load_eval_set(path="backend/data/eval_set.csv"):
    # utf-8-sig strips the BOM that Windows tools (e.g. PowerShell Set-Content)
    # write to UTF-8 files, which would otherwise corrupt the first column key.
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def to_bool(s: str) -> bool:
    return s.strip().lower() in ("true", "1", "yes")


def prf(tp: int, fp: int, fn: int):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def _score(predictions_and_truth):
    total = len(predictions_and_truth)
    correct = sum(1 for p, g in predictions_and_truth if p == g)
    tp = sum(1 for p, g in predictions_and_truth if p and g)
    fp = sum(1 for p, g in predictions_and_truth if p and not g)
    fn = sum(1 for p, g in predictions_and_truth if not p and g)
    return {
        "n": total,
        "accuracy": round(correct / total, 3) if total else 0.0,
        **prf(tp, fp, fn),
    }


def evaluate_multiagent(rows, llm):
    understanding = UnderstandingAgent(llm)
    quality = QualityAgent(llm)

    completeness_results, ambiguity_results = [], []

    for i, row in enumerate(rows):
        text = row["requirement_text"]
        gt = to_bool(row["ground_truth_issue_present"])
        print(f"  [{i+1}/{len(rows)}] {row['id']} ({row['task']})")

        if row["task"] == "completeness":
            structured = understanding.run(text)
            result = quality.check_completeness(structured, text)
            pred = result.get("complete") is False
            completeness_results.append((pred, gt))

        elif row["task"] == "ambiguity":
            structured = understanding.run(text)
            result = quality.check_ambiguity(text, structured.get("type"))
            pred = result.get("ambiguous") is True
            ambiguity_results.append((pred, gt))

        # Small delay to stay under Groq's RPM limit (each completeness row
        # makes 2 API calls; ambiguity rows also make 2; 60 rows = 120 calls).
        time.sleep(2)

    return {
        "completeness": _score(completeness_results),
        "ambiguity": _score(ambiguity_results),
    }


def evaluate_single_prompt(rows, llm):
    baseline = SinglePromptBaseline(llm)

    completeness_results, ambiguity_results = [], []

    for i, row in enumerate(rows):
        text = row["requirement_text"]
        gt = to_bool(row["ground_truth_issue_present"])
        print(f"  [{i+1}/{len(rows)}] {row['id']} ({row['task']})")
        result = baseline.run(text)

        if row["task"] == "completeness":
            pred = result.get("complete") is False
            completeness_results.append((pred, gt))

        elif row["task"] == "ambiguity":
            pred = result.get("ambiguous") is True
            ambiguity_results.append((pred, gt))

        time.sleep(2)

    return {
        "completeness": _score(completeness_results),
        "ambiguity": _score(ambiguity_results),
    }


if __name__ == "__main__":
    provider = sys.argv[1] if len(sys.argv) > 1 else "groq"
    llm = LLMClient(provider=provider)
    rows = load_eval_set()

    print(f"Loaded {len(rows)} evaluation items. Running multi-agent pipeline...")
    multi = evaluate_multiagent(rows, llm)

    print("Running single-prompt baseline...")
    single = evaluate_single_prompt(rows, llm)

    print("\n=== RESULTS ===")
    print(json.dumps({"multi_agent": multi, "single_prompt": single}, indent=2))
