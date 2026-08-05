"""Runtime context passed to workflow components."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import AppConfig


@dataclass
class RunContext:
    config: AppConfig
    run_id: str
    trace_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    retries: dict[str, int] = field(default_factory=dict)
    validation_failures: list[str] = field(default_factory=list)
    tool_calls: int = 0

