"""Privacy-aware run metrics and lightweight event recording."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime

from ..models import RunMetrics

ProgressCallback = Callable[[str, dict[str, object]], None]


@dataclass
class EventRecorder:
    run_id: str
    on_record: ProgressCallback | None = None
    events: list[dict[str, object]] = field(default_factory=list)

    def record(self, event: str, **metadata: object) -> None:
        record = {"timestamp": datetime.now(UTC).isoformat(), "event": event, **metadata}
        self.events.append(record)
        if self.on_record:
            self.on_record(event, metadata)


@dataclass
class Stopwatch:
    started: float = field(default_factory=time.perf_counter)

    @property
    def elapsed_ms(self) -> int:
        return int((time.perf_counter() - self.started) * 1000)


def finish_metrics(metrics: RunMetrics, stopwatch: Stopwatch) -> RunMetrics:
    metrics.finished_at = datetime.now(UTC)
    metrics.latency_ms = stopwatch.elapsed_ms
    return metrics
