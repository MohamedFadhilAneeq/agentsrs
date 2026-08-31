"""Agent 2 — Quality Analysis.
Runs two sub-checks: Completeness (adapted from ReCompGPT) and Ambiguity
(grounded in ISO/IEC/IEEE 29148 quality attributes).

CHANGE FROM PREVIOUS VERSION — description-vs-spec comparison:
The original version only compared a requirement against the OTHER requirements
in the same file. ReCompGPT's actual method compares a formal SPECIFICATION
against an informal DESCRIPTION (the source text a spec was derived from) —
that's what lets it catch gaps nothing in the spec set hints at. Our first test
run missed the paper's own worked example (a temperature-alarm requirement)
precisely because there was no description to compare against — only other
specs. `check_completeness` now accepts an optional `description` argument.
When provided, it does the real description-vs-spec comparison. When not
provided, it falls back to the old spec-vs-spec-set behavior — so this stays
backward compatible with data that doesn't have paired descriptions.

CHANGE — structured ambiguity categories:
`check_ambiguity` now returns a `category` field (one of a fixed set) instead
of only a free-text issue string, so results are countable/tabulable for a
results table rather than needing manual re-reading of every explanation.
"""

from backend.llm.client import LLMClient

COMPLETENESS_SYSTEM_PROMPT_WITH_DESCRIPTION = """You are a Completeness-Checking \
sub-agent, adapted from the ReCompGPT method. You are given an informal DESCRIPTION \
(what the stakeholder actually said) and a formal SPECIFICATION (what was written \
down). Compare them: is anything mentioned in the description that is missing from \
the specification (a global gap), or under-detailed in the specification (a local \
gap)? Also consider whether an implied "otherwise" case is missing even if the \
description doesn't explicitly say it (e.g. an action is triggered but never \
resolved, stopped, or reported).

Respond ONLY with JSON:
{"complete": true|false, "issue": "short description or null", "explanation": "..."}"""

COMPLETENESS_SYSTEM_PROMPT_SPEC_ONLY = """You are a Completeness-Checking sub-agent, \
adapted from the ReCompGPT method. No informal description is available for this \
requirement, so compare it only against the rest of the specification set for \
context. Identify whether anything is missing — an unhandled condition (e.g. an \
"otherwise" case never specified) or an incomplete action (e.g. something is \
triggered but never resolved, stopped, or reported).

NOTE: without a description, this check can only catch gaps that are hinted at \
elsewhere in the spec set — it cannot catch gaps that were never mentioned anywhere.

Respond ONLY with JSON:
{"complete": true|false, "issue": "short description or null", "explanation": "..."}"""

AMBIGUITY_SYSTEM_PROMPT = """You are an Ambiguity-Checking sub-agent, grounded in \
ISO/IEC/IEEE 29148 quality attributes. Given a single requirement (and its type, \
functional or non-functional), check for ambiguity and classify it into exactly \
one category:
- "vague_term": subjective/unmeasurable words (e.g. "fast", "user-friendly", "appropriate", "secure")
- "missing_measurable_detail": an implied metric with no number/threshold given
- "multiple_interpretation": the sentence can reasonably be read more than one way
- "none": not ambiguous

Non-functional requirements need a measurable metric (time, count, rate, etc.) to
be considered unambiguous — a non-functional requirement with no number is almost
always "missing_measurable_detail".

Respond ONLY with JSON:
{"ambiguous": true|false, "category": "vague_term"|"missing_measurable_detail"|"multiple_interpretation"|"none",
 "issue": "short description or null", "explanation": "..."}"""


class QualityAgent:
    def __init__(self, llm: LLMClient):
        self.llm = llm

    def check_completeness(
        self, structured_req: dict, context: str, description: str | None = None
    ) -> dict:
        if description:
            system_prompt = COMPLETENESS_SYSTEM_PROMPT_WITH_DESCRIPTION
            prompt = (
                f"Description (informal source text):\n{description}\n\n"
                f"Specification (formal requirement):\n{structured_req}"
            )
        else:
            system_prompt = COMPLETENESS_SYSTEM_PROMPT_SPEC_ONLY
            prompt = f"Requirement: {structured_req}\n\nFull requirement set for context:\n{context}"

        return self.llm.generate_json(system_prompt, prompt, temperature=0.2)

    def check_ambiguity(self, requirement_text: str, requirement_type: str | None = None) -> dict:
        prompt = f"Requirement: {requirement_text}\nType: {requirement_type or 'unknown'}"
        return self.llm.generate_json(AMBIGUITY_SYSTEM_PROMPT, prompt, temperature=0.2)

    def run(
        self,
        requirement_text: str,
        structured_req: dict,
        context: str,
        description: str | None = None,
    ) -> dict:
        return {
            "completeness": self.check_completeness(structured_req, context, description),
            "ambiguity": self.check_ambiguity(requirement_text, structured_req.get("type")),
        }
