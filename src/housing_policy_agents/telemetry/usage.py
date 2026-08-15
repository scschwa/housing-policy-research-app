"""Per-agent usage aggregation and transparent cost estimates."""

from __future__ import annotations

from typing import Any

from ..config import AppConfig
from ..models import AgentUsageRecord, UsageReport
from .interactions import InteractionTelemetry


def _estimated_cost(
    *,
    input_tokens: int,
    cached_input_tokens: int,
    output_tokens: int,
    config: AppConfig,
) -> float | None:
    input_rate = config.openai_input_cost_per_million_usd
    output_rate = config.openai_output_cost_per_million_usd
    if input_rate is None or output_rate is None:
        return None
    cached_rate = config.openai_cached_input_cost_per_million_usd
    effective_cached_rate = input_rate if cached_rate is None else cached_rate
    uncached_input = max(0, input_tokens - cached_input_tokens)
    return round(
        (
            uncached_input * input_rate
            + cached_input_tokens * effective_cached_rate
            + output_tokens * output_rate
        )
        / 1_000_000,
        6,
    )


def build_usage_report(
    *,
    run_id: str,
    telemetry: InteractionTelemetry,
    config: AppConfig,
    wall_clock_ms: int,
) -> UsageReport:
    records: list[AgentUsageRecord] = []
    for interaction in telemetry.interactions:
        usage: dict[str, Any] = interaction.get("usage", {})
        metadata: dict[str, Any] = interaction.get("metadata", {})
        input_tokens = int(usage.get("input_tokens", 0))
        cached_tokens = int(usage.get("cached_input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        records.append(
            AgentUsageRecord(
                interaction_id=str(interaction["interaction_id"]),
                agent=str(interaction["agent"]),
                stage=str(interaction["stage"]),
                model=str(metadata.get("model")) if metadata.get("model") else None,
                status=str(interaction.get("status", "unknown")),
                requests=int(usage.get("requests", 0)),
                input_tokens=input_tokens,
                cached_input_tokens=cached_tokens,
                cache_write_tokens=int(usage.get("cache_write_tokens", 0)),
                output_tokens=output_tokens,
                reasoning_tokens=int(usage.get("reasoning_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
                duration_ms=int(interaction.get("duration_ms", 0)),
                approximate_cost_usd=_estimated_cost(
                    input_tokens=input_tokens,
                    cached_input_tokens=cached_tokens,
                    output_tokens=output_tokens,
                    config=config,
                ),
            )
        )

    costs = [record.approximate_cost_usd for record in records]
    cost_available = bool(records) and all(cost is not None for cost in costs)
    if config.openai_input_cost_per_million_usd is None or config.openai_output_cost_per_million_usd is None:
        pricing_note = (
            "USD cost was not estimated because OPENAI_INPUT_COST_PER_MILLION_USD and "
            "OPENAI_OUTPUT_COST_PER_MILLION_USD are not both configured. Token counts are exact "
            "when supplied by the Agents SDK."
        )
    elif config.openai_cached_input_cost_per_million_usd is None:
        pricing_note = (
            "USD cost is approximate and uses the configured regular input rate for cached input "
            "because OPENAI_CACHED_INPUT_COST_PER_MILLION_USD is not configured."
        )
    else:
        pricing_note = "USD cost is approximate and uses the configured per-million-token rates."

    return UsageReport(
        run_id=run_id,
        model=config.openai_model if config.live_enabled else "fixture-deterministic",
        records=records,
        requests=sum(record.requests for record in records),
        input_tokens=sum(record.input_tokens for record in records),
        cached_input_tokens=sum(record.cached_input_tokens for record in records),
        cache_write_tokens=sum(record.cache_write_tokens for record in records),
        output_tokens=sum(record.output_tokens for record in records),
        reasoning_tokens=sum(record.reasoning_tokens for record in records),
        total_tokens=sum(record.total_tokens for record in records),
        wall_clock_ms=wall_clock_ms,
        cumulative_agent_ms=sum(record.duration_ms for record in records),
        approximate_cost_usd=(
            round(sum(float(cost) for cost in costs if cost is not None), 6)
            if cost_available
            else None
        ),
        pricing_note=pricing_note,
    )
