"""Promptfoo shallow baseline provider."""

from __future__ import annotations

import json
import time


def call_api(prompt: str, options: dict, context: dict) -> dict:
    started = time.perf_counter()
    question = context.get("vars", {}).get("question", prompt)
    output = {
        "variant": "single_agent_baseline",
        "question": question,
        "final_report": {
            "title": "Baseline housing policy memo",
            "sections": [
                {"section_id": "executive_summary", "title": "Executive summary", "paragraphs": [{"text": "The baseline identifies possible benefits and costs but does not reconcile specialist evidence.", "citation_ids": ["S-001"], "claim_ids": [], "substantive": True}]},
                {"section_id": "conclusions", "title": "Conclusions", "paragraphs": [{"text": "Further analysis is needed.", "citation_ids": ["S-001"], "claim_ids": [], "substantive": True}]},
            ],
        },
        "source_ledger": [{"source_id": "S-001"}],
        "adversarial_review": {"findings": [], "release_recommendation": "approve_with_caveats"},
    }
    return {
        "output": json.dumps(output),
        "latencyMs": int((time.perf_counter() - started) * 1000),
        "tokenUsage": {"total": 0, "prompt": 0, "completion": 0, "numRequests": 0},
        "cost": 0.0,
        "metadata": {"variant": "single_agent_baseline"},
    }
