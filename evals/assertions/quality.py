"""Promptfoo deterministic quality assertion."""

from __future__ import annotations

import json


def get_assert(output: str, context: dict) -> dict:
    try:
        package = json.loads(output)
        variant = package.get("variant", "hierarchical")
        final = package["final_report"]
        sections = {item["section_id"] for item in final["sections"]}
        source_ids = {item["source_id"] for item in package["source_ledger"]}
        cited = {
            source_id
            for section in final["sections"]
            for paragraph in section["paragraphs"]
            for source_id in paragraph["citation_ids"]
        }
        missing = cited - source_ids
        required = {"executive_summary", "us_baseline", "legal_implementation", "decision_matrix", "conclusions", "sources"}
        if variant == "single_agent_baseline":
            basic = {
                "schema_valid": True,
                "source_ids_resolve": not missing,
                "has_review": bool(package.get("adversarial_review")),
            }
            return {
                "pass": all(basic.values()),
                "score": 0.4 if all(basic.values()) else 0.0,
                "reason": json.dumps(
                    {"variant": variant, "baseline_components": basic, "full_network_gate": False}
                ),
            }
        components = {
            "schema_valid": True,
            "source_ids_resolve": not missing,
            "required_sections": required <= sections,
            "citation_coverage": all(
                paragraph["citation_ids"]
                for section in final["sections"]
                for paragraph in section["paragraphs"]
                if paragraph["substantive"]
            ),
            "has_review": bool(package.get("adversarial_review")),
        }
        score = sum(components.values()) / len(components)
        return {
            "pass": score >= 0.9,
            "score": score,
            "reason": json.dumps(
                {"variant": variant, "components": components, "missing_source_ids": sorted(missing)}
            ),
        }
    except Exception as exc:
        return {"pass": False, "score": 0.0, "reason": f"invalid package: {exc}"}
