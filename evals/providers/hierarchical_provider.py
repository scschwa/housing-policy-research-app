"""Promptfoo provider for the complete hierarchical network."""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from housing_policy_agents.config import AppConfig  # noqa: E402
from housing_policy_agents.models import (  # noqa: E402
    ResearchProviderName,
    RunMode,
    UserResearchRequest,
)
from housing_policy_agents.workflows.research_workflow import ResearchWorkflow  # noqa: E402


def call_api(prompt: str, options: dict, context: dict) -> dict:
    vars_ = context.get("vars", {})
    question = vars_.get("question", prompt)
    provider_config = options.get("config", {})
    is_live = bool(provider_config.get("live", False))
    started = time.perf_counter()
    config = AppConfig(
        research_provider="web" if is_live else "offline",
        allow_network=is_live,
        fixture_path=ROOT / "tests/fixtures/mortgage_portability.json",
        artifacts_dir=ROOT / "work/promptfoo-artifacts",
        enable_clarification=bool(provider_config.get("enable_clarification", True)),
        enable_manager_reconciliation=bool(
            provider_config.get("enable_manager_reconciliation", True)
        ),
        enable_adversarial_review=bool(provider_config.get("enable_adversarial_review", True)),
        disabled_branches=list(provider_config.get("disabled_branches", [])),
    )
    if is_live and not config.live_enabled:
        return {"error": "Live eval requires OPENAI_API_KEY and explicit network configuration."}
    request = UserResearchRequest(
        question=question,
        mode=RunMode.FAST,
        provider=ResearchProviderName.WEB if is_live else ResearchProviderName.OFFLINE,
        accept_defaults=True,
    )
    package = asyncio.run(ResearchWorkflow(config).run(request))
    output = json.dumps(package.model_dump(mode="json"))
    return {
        "output": output,
        "latencyMs": int((time.perf_counter() - started) * 1000),
        "tokenUsage": {"total": 0, "prompt": 0, "completion": 0, "numRequests": 0},
        "cost": 0.0,
        "metadata": {"variant": "hierarchical", "run_id": package.run_id, "branch_count": len(package.specialist_findings)},
    }
