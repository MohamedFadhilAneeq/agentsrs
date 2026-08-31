"""Agent 3 — Requirement Refinement.
Rewrites a flagged requirement to resolve the issues Agent 2 detected, while
preserving the original intent and scope (no new functionality added)."""

from backend.llm.client import LLMClient

SYSTEM_PROMPT = """You are a Requirement Refinement Agent. You receive an original \
requirement and a list of detected quality issues (completeness and/or ambiguity). \
Rewrite the requirement to resolve every listed issue while preserving its original \
intent and scope. Do not introduce new functionality that wasn't implied by the original.

Respond ONLY with JSON:
{"improved_requirement": "...", "changes_made": ["...", "..."]}"""


class RefinementAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, original_text: str, issues: dict) -> dict:
        prompt = f"Original requirement: {original_text}\n\nDetected issues: {issues}"
        result = self.llm.generate_json(SYSTEM_PROMPT, prompt, temperature=0.3)
        if result.get("_parse_error"):
            return {"improved_requirement": original_text, "changes_made": [], **result}
        return result
