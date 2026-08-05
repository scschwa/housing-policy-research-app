"""Privacy-aware run metrics and lightweight event recording."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..models import RunMetrics


@dataclass
class EventRecorder:
    run_id: str
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, event: str, **metadata: object) -> None:
        self.events.append({"timestamp": datetime.now(timezone.utc).isoformat(), "event": event, **metadata})


@dataclass
class Stopwatch:
    started: float = field(default_factory=time.perf_counter)

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)


def finish_metrics(metrics: RunMetrics, stopwatch: Stopwatch) -> RunMetrics:
    metrics.finished_at = datetime.now(timezone.utc)
    metrics.latency_ms = stopwatch.elapsed_ms
    return metrics
