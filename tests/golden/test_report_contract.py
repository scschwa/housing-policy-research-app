from pathlib import Path

from housing_policy_agents.models import FinalResearchPackage


def test_saved_demo_package_has_required_sections() -> None:
    packages = sorted(Path("artifacts").glob("*/package.json"))
    if not packages:
        return
    package = FinalResearchPackage.model_validate_json(packages[-1].read_text(encoding="utf-8"))
    section_ids = {section.section_id for section in package.final_report.sections}
    assert {"executive_summary", "decision_matrix", "sources", "conclusions"} <= section_ids
