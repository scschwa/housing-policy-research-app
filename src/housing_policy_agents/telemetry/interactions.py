"""Artifact-backed agent and sub-agent interaction telemetry."""

from __future__ import annotations

import json
import re
import time
import traceback
from collections.abc import Mapping, Sequence
from dataclasses import asdict, is_dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

from pydantic import BaseModel

_SECRET_KEY_NAMES = {
    "api_key",
    "authorization",
    "openai_api_key",
    "password",
    "secret",
    "token",
}
_SECRET_PATTERN = re.compile(r"(?i)(?:bearer\s+|sk-)[A-Za-z0-9_.-]{12,}")


def _redact_text(value: str, max_chars: int) -> str:
    redacted = _SECRET_PATTERN.sub("[REDACTED]", value)
    if len(redacted) <= max_chars:
        return redacted
    return redacted[:max_chars] + "… [truncated]"


def _jsonable(value: Any, max_chars: int) -> Any:
    """Convert SDK/Pydantic objects to bounded, redacted JSON-compatible data."""
    if value is None or isinstance(value, bool | int | float):
        return value
    if isinstance(value, str):
        return _redact_text(value, max_chars)
    if isinstance(value, BaseModel):
        return _jsonable(value.model_dump(mode="json", exclude_none=True), max_chars)
    if is_dataclass(value):
        return _jsonable(asdict(cast(Any, value)), max_chars)
    if isinstance(value, Mapping):
        result: dict[str, Any] = {}
        for key, item in value.items():
            key_text = str(key)
            if key_text.lower() in _SECRET_KEY_NAMES:
                result[key_text] = "[REDACTED]"
            else:
                result[key_text] = _jsonable(item, max_chars)
        return result
    if isinstance(value, Sequence) and not isinstance(value, bytes | bytearray):
        return [_jsonable(item, max_chars) for item in value]
    if isinstance(value, bytes | bytearray):
        return _redact_text(value.decode("utf-8", errors="replace"), max_chars)
    return _redact_text(str(value), max_chars)


def _run_item_payload(item: Any, max_chars: int) -> dict[str, Any]:
    raw_item = getattr(item, "raw_item", item)
    agent = getattr(item, "agent", None)
    return {
        "type": getattr(item, "type", type(item).__name__),
        "agent": getattr(agent, "name", None),
        "raw_item": _jsonable(raw_item, max_chars),
    }


def _usage_payload(result_or_error: Any) -> dict[str, int]:
    totals = {
        "requests": 0,
        "input_tokens": 0,
        "cached_input_tokens": 0,
        "cache_write_tokens": 0,
        "output_tokens": 0,
        "reasoning_tokens": 0,
        "total_tokens": 0,
    }
    for response in getattr(result_or_error, "raw_responses", []):
        usage = getattr(response, "usage", None)
        if usage is None:
            continue
        totals["requests"] += int(getattr(usage, "requests", 0) or 0)
        totals["input_tokens"] += int(getattr(usage, "input_tokens", 0) or 0)
        totals["output_tokens"] += int(getattr(usage, "output_tokens", 0) or 0)
        totals["total_tokens"] += int(getattr(usage, "total_tokens", 0) or 0)
        input_details = getattr(usage, "input_tokens_details", None)
        output_details = getattr(usage, "output_tokens_details", None)
        totals["cached_input_tokens"] += int(
            getattr(input_details, "cached_tokens", 0) or 0
        )
        totals["cache_write_tokens"] += int(
            getattr(input_details, "cache_write_tokens", 0) or 0
        )
        totals["reasoning_tokens"] += int(
            getattr(output_details, "reasoning_tokens", 0) or 0
        )
    return totals


class InteractionTelemetry:
    """Collect bounded live exchanges and persist them as inspectable artifacts."""

    def __init__(
        self,
        *,
        run_id: str,
        enabled: bool = True,
        include_content: bool = True,
        max_chars: int = 30_000,
    ) -> None:
        self.run_id = run_id
        self.enabled = enabled
        self.include_content = include_content
        self.max_chars = max_chars
        self._started = time.perf_counter()
        self.interactions: list[dict[str, Any]] = []
        self.handoffs: list[dict[str, Any]] = []

    def begin(
        self,
        *,
        agent: str,
        stage: str,
        input_payload: Any,
        metadata: Mapping[str, Any] | None = None,
    ) -> str | None:
        if not self.enabled:
            return None
        interaction_id = f"interaction-{len(self.interactions) + 1:04d}"
        self.interactions.append(
            {
                "interaction_id": interaction_id,
                "agent": agent,
                "stage": stage,
                "status": "running",
                "started_at": time.time(),
                "metadata": _jsonable(dict(metadata or {}), self.max_chars),
                "input": (
                    _jsonable(input_payload, self.max_chars)
                    if self.include_content
                    else {"content_capture": False}
                ),
            }
        )
        return interaction_id

    def complete(self, interaction_id: str | None, result: Any) -> None:
        if interaction_id is None:
            return
        record = self._find(interaction_id)
        record.update(
            {
                "status": "completed",
                "finished_at": time.time(),
                "duration_ms": self._duration_ms(record),
                "final_output": (
                    _jsonable(result.final_output, self.max_chars)
                    if self.include_content
                    else {"content_capture": False}
                ),
                "transcript": self._transcript(result),
                "raw_responses": self._raw_responses(result),
                "usage": _usage_payload(result),
                "usage_by_response": [
                    _usage_payload(SimpleNamespace(raw_responses=[response]))
                    for response in getattr(result, "raw_responses", [])
                ],
                "response_ids": [
                    getattr(response, "response_id", None)
                    for response in getattr(result, "raw_responses", [])
                ],
            }
        )

    def fail(
        self,
        interaction_id: str | None,
        error: BaseException,
        raw_responses: Sequence[Any] | None = None,
    ) -> None:
        if interaction_id is None:
            return
        record = self._find(interaction_id)
        captured_responses = list(raw_responses or getattr(error, "raw_responses", []))
        response_holder = SimpleNamespace(raw_responses=captured_responses)
        record.update(
            {
                "status": "failed",
                "finished_at": time.time(),
                "duration_ms": self._duration_ms(record),
                "error": {
                    "type": type(error).__name__,
                    "message": _redact_text(str(error), self.max_chars),
                    "traceback": _redact_text(traceback.format_exc(), self.max_chars),
                },
                "transcript": self._transcript(error),
                "raw_responses": self._raw_responses(response_holder),
                "response_ids": [
                    getattr(response, "response_id", None) for response in captured_responses
                ],
                "usage": _usage_payload(response_holder),
                "usage_by_response": [
                    _usage_payload(SimpleNamespace(raw_responses=[response]))
                    for response in captured_responses
                ],
            }
        )

    def record_local(
        self,
        *,
        agent: str,
        stage: str,
        duration_ms: int,
        status: str = "completed",
        model: str = "fixture-deterministic",
    ) -> None:
        """Record a deterministic non-SDK agent stage in the same usage ledger."""
        if not self.enabled:
            return
        now = time.time()
        self.interactions.append(
            {
                "interaction_id": f"interaction-{len(self.interactions) + 1:04d}",
                "agent": agent,
                "stage": stage,
                "status": status,
                "started_at": now - (duration_ms / 1000),
                "finished_at": now,
                "duration_ms": duration_ms,
                "metadata": {"model": model, "local_execution": True},
                "input": {"content_capture": False, "local_execution": True},
                "final_output": {"content_capture": False, "local_execution": True},
                "transcript": [],
                "raw_responses": [],
                "response_ids": [],
                "usage": _usage_payload(None),
                "usage_by_response": [],
            }
        )

    def handoff(
        self,
        *,
        source: str,
        target: str,
        stage: str,
        payload: Mapping[str, Any] | None = None,
    ) -> None:
        if not self.enabled:
            return
        self.handoffs.append(
            {
                "handoff_id": f"handoff-{len(self.handoffs) + 1:04d}",
                "source": source,
                "target": target,
                "stage": stage,
                "payload": (
                    _jsonable(dict(payload or {}), self.max_chars)
                    if self.include_content
                    else {"content_capture": False}
                ),
                "timestamp": time.time(),
            }
        )

    def persist(self, artifact_dir: Path) -> None:
        """Write root summary plus one directory per recorded interaction."""
        summary = self._summary()
        (artifact_dir / "interaction_summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        telemetry_dir = artifact_dir / "sub-agent-telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)
        index: list[dict[str, Any]] = []
        for position, record in enumerate(self.interactions, start=1):
            slug = re.sub(r"[^a-z0-9]+", "-", record["agent"].lower()).strip("-")
            directory = telemetry_dir / f"{position:03d}-{slug}"
            directory.mkdir(parents=True, exist_ok=True)
            request = {
                "interaction_id": record["interaction_id"],
                "agent": record["agent"],
                "stage": record["stage"],
                "metadata": record["metadata"],
                "input": record["input"],
            }
            result = {
                key: value
                for key, value in record.items()
                if key not in {"input", "metadata", "transcript"}
            }
            (directory / "request.json").write_text(
                json.dumps(request, indent=2), encoding="utf-8"
            )
            (directory / "transcript.json").write_text(
                json.dumps(record.get("transcript", []), indent=2), encoding="utf-8"
            )
            (directory / "result.json").write_text(
                json.dumps(result, indent=2), encoding="utf-8"
            )
            index.append(
                {
                    "interaction_id": record["interaction_id"],
                    "agent": record["agent"],
                    "stage": record["stage"],
                    "status": record["status"],
                    "path": directory.relative_to(artifact_dir).as_posix(),
                }
            )
        (telemetry_dir / "index.json").write_text(
            json.dumps({"interactions": index, "handoffs": self.handoffs}, indent=2),
            encoding="utf-8",
        )

    def _find(self, interaction_id: str) -> dict[str, Any]:
        for record in self.interactions:
            if record["interaction_id"] == interaction_id:
                return record
        raise KeyError(interaction_id)

    @staticmethod
    def _duration_ms(record: Mapping[str, Any]) -> int:
        return int((record.get("finished_at", time.time()) - record["started_at"]) * 1000)

    def _transcript(self, result_or_error: Any) -> list[dict[str, Any]]:
        if not self.include_content:
            return [{"content_capture": False}]
        items = getattr(result_or_error, "new_items", [])
        return [_run_item_payload(item, self.max_chars) for item in items]

    def _raw_responses(self, result_or_error: Any) -> list[Any]:
        if not self.include_content:
            return [{"content_capture": False}]
        return [
            _jsonable(response, self.max_chars)
            for response in getattr(result_or_error, "raw_responses", [])
        ]

    def _summary(self) -> dict[str, Any]:
        statuses = [record["status"] for record in self.interactions]
        return {
            "run_id": self.run_id,
            "enabled": self.enabled,
            "include_content": self.include_content,
            "max_chars_per_value": self.max_chars,
            "interaction_count": len(self.interactions),
            "completed_count": statuses.count("completed"),
            "failed_count": statuses.count("failed"),
            "running_count": statuses.count("running"),
            "handoff_count": len(self.handoffs),
            "agents": sorted({record["agent"] for record in self.interactions}),
            "stages": sorted({record["stage"] for record in self.interactions}),
            "elapsed_ms": int((time.perf_counter() - self._started) * 1000),
            "usage": {
                key: sum(
                    int(record.get("usage", {}).get(key, 0))
                    for record in self.interactions
                )
                for key in (
                    "requests",
                    "input_tokens",
                    "cached_input_tokens",
                    "cache_write_tokens",
                    "output_tokens",
                    "reasoning_tokens",
                    "total_tokens",
                )
            },
            "failed_interactions": [
                {
                    "interaction_id": record["interaction_id"],
                    "agent": record["agent"],
                    "stage": record["stage"],
                    "error": record.get("error"),
                }
                for record in self.interactions
                if record["status"] == "failed"
            ],
        }


async def run_agent_with_telemetry(
    *,
    context: Any,
    agent: Any,
    runner_input: str,
    input_payload: Any,
    agent_name: str,
    stage: str,
    max_turns: int,
    run_config: Any,
) -> Any:
    """Run one Agents SDK call while preserving success/failure exchange data."""
    from agents import Runner
    from agents.lifecycle import RunHooksBase

    class UsageCaptureHooks(RunHooksBase[Any, Any]):
        def __init__(self) -> None:
            self.raw_responses: list[Any] = []

        async def on_llm_end(
            self,
            context_wrapper: Any,
            running_agent: Any,
            response: Any,
        ) -> None:
            del context_wrapper, running_agent
            self.raw_responses.append(response)

    telemetry = context.interaction_telemetry
    if telemetry is None:
        return await Runner.run(
            agent,
            runner_input,
            max_turns=max_turns,
            run_config=run_config,
        )
    metadata = {"model": getattr(run_config, "model", None), "max_turns": max_turns}
    if telemetry.include_content:
        metadata["agent_instructions"] = getattr(agent, "instructions", None)
    interaction_id = telemetry.begin(
        agent=agent_name,
        stage=stage,
        input_payload=input_payload,
        metadata=metadata,
    )
    hooks = UsageCaptureHooks()
    try:
        result = await Runner.run(
            agent,
            runner_input,
            max_turns=max_turns,
            hooks=hooks,
            run_config=run_config,
        )
    except Exception as exc:
        telemetry.fail(interaction_id, exc, raw_responses=hooks.raw_responses)
        raise
    telemetry.complete(interaction_id, result)
    return result
