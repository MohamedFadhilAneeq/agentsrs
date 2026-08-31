"""Baseline for the multi-agent vs. single-prompt ablation.

Why this file exists: the critique on this project flagged that nobody had shown
the multi-agent decomposition (Agents 1-3 + report module) actually outperforms
one well-prompted LLM call doing everything at once. This is that single-call
baseline. Run both on the same test set and compare — the result either justifies
the multi-agent architecture or tells you to simplify.

Uses the same generate_json() retry logic as the multi-agent pipeline, so the
comparison isn't confounded by one side having better JSON-parsing robustness
than the other.

Usage:
    python -m backend.experiments.single_prompt_baseline
"""

import json
from backend.llm.client import LLMClient

SYSTEM_PROMPT = """You are a software requirements quality reviewer. For the given \
requirement, do ALL of the following in a single response:
1. Check completeness — is anything missing (an unhandled condition or incomplete action)?
2. Check ambiguity — vague terms, missing measurable detail, multiple interpretations?
3. If either issue is found, rewrite the requirement to fix it while preserving intent.

Respond ONLY with JSON:
{"complete": true|false, "completeness_issue": "... or null",
 "ambiguous": true|false, "ambiguity_issue": "... or null",
 "improved_requirement": "..."}"""


class SinglePromptBaseline:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, requirement_text: str) -> dict:
        return self.llm.generate_json(SYSTEM_PROMPT, requirement_text, temperature=0.2)


if __name__ == "__main__":
    import sys

    llm = LLMClient(provider=sys.argv[1] if len(sys.argv) > 1 else "groq")
    baseline = SinglePromptBaseline(llm)

    with open("backend/data/sample_srs.txt") as f:
        reqs = [line.strip() for line in f if line.strip()]

    for req in reqs:
        result = baseline.run(req)
        print(json.dumps({"requirement": req, "result": result}, indent=2))
