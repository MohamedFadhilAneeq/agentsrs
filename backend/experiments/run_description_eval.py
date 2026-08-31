"""
Evaluates completeness detection in the REAL description-vs-spec mode (the
mode ReCompGPT actually uses), on the 10 items that already have hand-labeled
ground truth, now paired with informal descriptions.

This directly answers the open question from the first evaluation run: does
the multi-agent completeness check actually work as designed when given the
input it was built for, rather than the crippled spec-only fallback?

Place this file at: backend/experiments/run_description_eval.py
Place the CSV at:    backend/data/eval_set_completeness_with_description.csv

Usage:
    python -m backend.experiments.run_description_eval groq
"""

import csv
import json
import sys
import time

from backend.llm.client import LLMClient
from backend.agents.understanding_agent import UnderstandingAgent
from backend.agents.quality_agent import QualityAgent
from backend.experiments.single_prompt_baseline import SinglePromptBaseline


def load_rows(path="backend/data/eval_set_completeness_with_description.csv"):
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def to_bool(s: str) -> bool:
    return s.strip().lower() in ("true", "1", "yes")


def prf(tp, fp, fn):
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}


def score(pairs):
    total = len(pairs)
    correct = sum(1 for p, g in pairs if p == g)
    tp = sum(1 for p, g in pairs if p and g)
    fp = sum(1 for p, g in pairs if p and not g)
    fn = sum(1 for p, g in pairs if not p and g)
    return {"n": total, "accuracy": round(correct / total, 3) if total else 0.0, **prf(tp, fp, fn)}


def run(provider="groq"):
    llm = LLMClient(provider=provider)
    understanding = UnderstandingAgent(llm)
    quality = QualityAgent(llm)
    baseline = SinglePromptBaseline(llm)

    rows = load_rows()
    multi_pairs, single_pairs = [], []

    for i, row in enumerate(rows):
        print(f"\n[{i+1}/{len(rows)}] {row['id']}")
        gt = to_bool(row["ground_truth_issue_present"])

        structured = understanding.run(row["requirement_text"])
        multi_result = quality.check_completeness(
            structured, context="", description=row["description"]
        )
        multi_pred = multi_result.get("complete") is False
        multi_pairs.append((multi_pred, gt))
        print(f"  [multi-agent]   pred={multi_pred} gt={gt}  issue={multi_result.get('issue')}")

        single_result = baseline.run(row["requirement_text"])
        single_pred = single_result.get("complete") is False
        single_pairs.append((single_pred, gt))
        print(f"  [single-prompt] pred={single_pred} gt={gt}  issue={single_result.get('completeness_issue')}")

        if i < len(rows) - 1:
            time.sleep(2)

    print("\n=== DESCRIPTION-VS-SPEC COMPLETENESS RESULTS ===")
    print(json.dumps({
        "multi_agent": score(multi_pairs),
        "single_prompt": score(single_pairs),
    }, indent=2))


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "groq")
