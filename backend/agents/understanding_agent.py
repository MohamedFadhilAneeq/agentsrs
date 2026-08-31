"""Agent 1 — Requirement Understanding.
Extracts structured elements (actor, action, condition, type) from a raw
requirement statement, following the condition+action definition used in
ReCompGPT. The `type` field (functional / non-functional) is consumed
downstream by Agent 2 — non-functional requirements get different ambiguity
handling, since they're inherently harder to make measurable (the base paper
flags NFR handling as a known weak point of its own method too)."""

from backend.llm.client import LLMClient

SYSTEM_PROMPT = """You are a Requirement Understanding Agent. Given a single software \
requirement statement, extract its structural elements.

Respond ONLY with JSON in this exact schema:
{"actor": "...", "action": "...", "condition": "...", "type": "functional" | "non-functional"}

If a field cannot be determined, use null. Do not include any text outside the JSON."""


class UnderstandingAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def run(self, requirement_text: str) -> dict:
        result = self.llm.generate_json(SYSTEM_PROMPT, requirement_text, temperature=0.1)
        if result.get("_parse_error"):
            return {"actor": None, "action": None, "condition": None, "type": None, **result}
        return result
