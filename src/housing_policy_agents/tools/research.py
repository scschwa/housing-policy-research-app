"""Pluggable research backends for offline and live execution."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any, Protocol

from ..models import ResearchAssignment, SearchQuery, SourceRecord


class ResearchBackend(Protocol):
    name: str

    async def search(self, query: SearchQuery, assignment: ResearchAssignment) -> list[SourceRecord]:
        ...

    def agent_tools(self) -> list[Any]:
        ...


class FixtureResearchBackend:
    name = "offline_fixture"

    def __init__(self, fixture_path: Path) -> None:
        payload = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.scenario_id = payload["scenario_id"]
        self.sources = [SourceRecord.model_validate(item) for item in payload["sources"]]
        self.branch_sources: dict[str, list[str]] = payload.get("branch_sources", {})

    async def search(self, query: SearchQuery, assignment: ResearchAssignment) -> list[SourceRecord]:
        ids = self.branch_sources.get(assignment.branch.value, [item.source_id for item in self.sources])
        selected = [item for item in self.sources if item.source_id in ids]
        return selected[: assignment.max_sources]

    def agent_tools(self) -> list[Any]:
        return []


class LiveResearchBackend:
    name = "openai_web_search"

    def __init__(self, max_results: int = 5) -> None:
        self.max_results = max_results

    async def search(self, query: SearchQuery, assignment: ResearchAssignment) -> list[SourceRecord]:
        # Live research is performed by the specialist Agent through WebSearchTool.
        # This method remains part of the provider contract for cache and test adapters.
        return []

    def agent_tools(self) -> list[Any]:
        try:
            from agents import WebSearchTool

            return [WebSearchTool(search_context_size="medium")]
        except ImportError:
            return []


class ResearchCache:
    """Small JSON cache used to make live retrieval reproducible when enabled."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def key(self, query: SearchQuery) -> str:
        return sha256(query.model_dump_json().encode("utf-8")).hexdigest()

    def load(self, query: SearchQuery) -> list[SourceRecord] | None:
        path = self.root / f"{self.key(query)}.json"
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return [SourceRecord.model_validate(item) for item in payload]

    def save(self, query: SearchQuery, records: list[SourceRecord]) -> None:
        path = self.root / f"{self.key(query)}.json"
        path.write_text(json.dumps([item.model_dump(mode="json") for item in records], indent=2), encoding="utf-8")
