"""Guardrails kept separate from model-based judgment."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from ..models import UserResearchRequest


HOUSING_TERMS = {
    "housing", "mortgage", "homebuyer", "homeowner", "rent", "rental", "zoning",
    "foreclosure", "servicing", "underwriting", "insurance", "property tax", "land use",
}
INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?previous",
    r"system\s+prompt",
    r"developer\s+message",
    r"reveal\s+(your|the)\s+(hidden|secret|system)",
    r"follow\s+these\s+instructions\s+instead",
    r"disregard\s+the\s+research",
]
DISCRIMINATION_PATTERNS = [
    r"deny\s+.*\b(race|ethnicity|religion|nationality|disability)\b",
    r"exclude\s+.*\b(race|ethnicity|religion|nationality|disability)\b",
    r"target\s+.*\b(race|ethnicity|religion|nationality|disability)\b",
]
PII_PATTERNS = [r"\b\d{3}-\d{2}-\d{4}\b", r"\b(?:account|routing)\s*(?:number|#)\s*[:=]?\s*\d{6,}\b"]


@dataclass
class GuardrailDecision:
    allowed: bool
    reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def assess_request(request: UserResearchRequest) -> GuardrailDecision:
    text = request.question.lower()
    reasons: list[str] = []
    warnings: list[str] = []
    if not any(term in text for term in HOUSING_TERMS):
        reasons.append("request does not appear materially related to housing policy")
    if any(re.search(pattern, text) for pattern in DISCRIMINATION_PATTERNS):
        reasons.append("request appears to seek targeted exclusion or unlawful discrimination")
    if any(re.search(pattern, text) for pattern in PII_PATTERNS):
        reasons.append("request contains potentially sensitive personal data")
    if any(re.search(pattern, text) for pattern in INJECTION_PATTERNS):
        warnings.append("possible prompt injection detected in user input")
    return GuardrailDecision(not reasons, reasons, warnings)


def inspect_untrusted_text(text: str) -> list[str]:
    """Return flags without ever executing or obeying source instructions."""

    lowered = text.lower()
    return [
        f"prompt_injection:{index}"
        for index, pattern in enumerate(INJECTION_PATTERNS, start=1)
        if re.search(pattern, lowered)
    ]
