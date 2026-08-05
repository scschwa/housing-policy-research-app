"""Application configuration and bounded execution policy."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """Environment-backed configuration shared by CLI and workflow."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-5-mini"
    research_provider: Literal["offline", "web"] = "offline"
    allow_network: bool = False
    trace_include_sensitive_data: bool = False
    artifacts_dir: Path = Path("artifacts")
    fixture_path: Path = Path("tests/fixtures/mortgage_portability.json")
    max_turns_per_agent: int = Field(default=6, ge=1, le=20)
    max_searches: int = Field(default=6, ge=1, le=100)
    max_sources: int = Field(default=24, ge=1, le=200)
    max_branch_retries: int = Field(default=1, ge=0, le=5)
    max_concurrency: int = Field(default=6, ge=1, le=32)
    total_token_budget: int = Field(default=60_000, ge=1_000)
    total_research_time_seconds: int = Field(default=300, ge=10)
    min_source_diversity: int = Field(default=3, ge=1, le=20)
    min_primary_source_coverage: float = Field(default=0.80, ge=0, le=1)
    source_verification: bool = False
    enable_clarification: bool = True
    enable_manager_reconciliation: bool = True
    enable_adversarial_review: bool = True
    disabled_branches: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        if self.research_provider == "web" and not self.allow_network:
            raise ValueError("RESEARCH_PROVIDER=web requires ALLOW_NETWORK=true")

    @property
    def live_enabled(self) -> bool:
        return self.research_provider == "web" and self.allow_network and bool(self.openai_api_key)
