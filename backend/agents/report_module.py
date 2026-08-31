"""Report Generation Module.

Deliberately NOT an LLM agent — pure aggregation and scoring, per the project
critique (padding the "agent count" with non-AI steps was flagged as a weakness).

NOTE: the overall_score formula below (simple average of completeness % and
ambiguity %) is still a placeholder — the critique flagged this explicitly:
completeness and ambiguity are measured differently, so averaging them needs
to be justified, not assumed. Revisit before the final report — either define
a real weighted formula, or report the two dimensions separately.

ADDED: a per-category breakdown of ambiguity issues (vague_term /
missing_measurable_detail / multiple_interpretation), since Agent 2 now
returns a structured category instead of free text — this gives you a real
table for your paper's Results section instead of just one blended number.
"""

from collections import Counter
from typing import List, Dict


def build_report(results: List[Dict]) -> Dict:
    total = len(results)
    complete_count = sum(
        1 for r in results if r["quality"]["completeness"].get("complete") is True
    )
    unambiguous_count = sum(
        1 for r in results if r["quality"]["ambiguity"].get("ambiguous") is False
    )

    completeness_score = round(100 * complete_count / total, 1) if total else 0.0
    ambiguity_score = round(100 * unambiguous_count / total, 1) if total else 0.0
    overall_score = round((completeness_score + ambiguity_score) / 2, 1)  # TODO: justify or replace

    category_counts = Counter(
        r["quality"]["ambiguity"].get("category", "none")
        for r in results
        if r["quality"]["ambiguity"].get("ambiguous") is True
    )

    return {
        "overall_score": overall_score,
        "completeness_score": completeness_score,
        "ambiguity_score": ambiguity_score,
        "ambiguity_category_breakdown": dict(category_counts),
        "total_requirements": total,
        "requirements": results,
    }
