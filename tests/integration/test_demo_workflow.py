import asyncio
import json
from pathlib import Path

from housing_policy_agents.agents.orchestrator import select_branches
from housing_policy_agents.config import AppConfig
from housing_policy_agents.models import ResearchProviderName, RunMode, UserResearchRequest
from housing_policy_agents.workflows.research_workflow import ResearchWorkflow

QUESTION = (
    "The United States is considering a policy that would permit qualifying borrowers to transfer "
    "an existing low-rate mortgage to a newly purchased primary residence. Evaluate consumer, legal, "
    "servicing, taxpayer, distributional, and international effects."
)


def test_fixture_workflow_persists_revised_package() -> None:
    fixture = Path(__file__).parents[1] / "fixtures" / "mortgage_portability.json"
    artifact_root = Path("work/test-artifacts")
    config = AppConfig(
        research_provider="offline", fixture_path=fixture, artifacts_dir=artifact_root
    )
    progress: list[str] = []
    request = UserResearchRequest(
        question=QUESTION,
        mode=RunMode.FAST,
        provider=ResearchProviderName.OFFLINE,
        accept_defaults=True,
    )
    package = asyncio.run(
        ResearchWorkflow(config).run(
            request,
            progress_callback=lambda event, metadata: progress.append(event),
        )
    )
    artifact = artifact_root / package.run_id
    assert package.final_report.revised is True
    assert package.final_report.revision_count == 1
    assert package.adversarial_review.release_recommendation.value == "revise"
    assert any(
        "prompt_injection" in flag
        for finding in package.specialist_findings
        for flag in finding.prompt_injection_flags
    )
    global_findings = [
        finding for finding in package.specialist_findings if finding.branch.value == "global_research"
    ]
    assert len(global_findings) == 1
    assert len(global_findings[0].country_comparisons) == 3
    assert len(package.manager_syntheses[-1].country_comparisons) == 3
    assert (artifact / "report.md").exists()
    loaded = json.loads((artifact / "package.json").read_text(encoding="utf-8"))
    assert loaded["run_id"] == package.run_id
    interaction_summary = json.loads(
        (artifact / "interaction_summary.json").read_text(encoding="utf-8")
    )
    interaction_index = json.loads(
        (artifact / "sub-agent-telemetry" / "index.json").read_text(encoding="utf-8")
    )
    assert interaction_summary["handoff_count"] >= 3
    assert interaction_index["handoffs"]
    assert (artifact / "sub-agent-telemetry").is_dir()
    assert progress[0] == "run_started"
    assert "branch_started" in progress
    assert "manager_finished" in progress
    assert progress[-1] == "artifacts_persisted"


def test_branch_selection_avoids_mortgage_operations_for_zoning() -> None:
    branches = set(
        select_branches("How should a city reform zoning and land use to increase housing supply?")
    )
    assert "government_sources" in {branch.value for branch in branches}
    assert "servicing" not in {branch.value for branch in branches}
    assert "loan_originator" not in {branch.value for branch in branches}
