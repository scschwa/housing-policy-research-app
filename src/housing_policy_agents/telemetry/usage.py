"""Per-agent usage aggregation and transparent cost estimates."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from ..config import AppConfig
from ..models import AgentUsageRecord, UsageReport
from .interactions import InteractionTelemetry
from .pricing import (
    PRICING_CATALOG_VERSION,
    PRICING_SOURCE_URL,
    ModelPricing,
    resolve_model_pricing,
)


@dataclass(frozen=True)
class _CostEstimate:
    amount_usd: float | None
    pricing: ModelPricing | None
    long_context_applied: bool = False
    used_override: bool = False


def _effective_pricing(model: str | None, config: AppConfig) -> tuple[ModelPricing | None, bool]:
    catalog_pricing = resolve_model_pricing(model)
    override_values = (
        config.openai_input_cost_per_million_usd,
        config.openai_cached_input_cost_per_million_usd,
        config.openai_cache_write_cost_per_million_usd,
        config.openai_output_cost_per_million_usd,
    )
    used_override = any(value is not None for value in override_values)

    if catalog_pricing is None:
        input_rate = config.openai_input_cost_per_million_usd
        output_rate = config.openai_output_cost_per_million_usd
        if input_rate is None or output_rate is None:
            return None, used_override
        custom_model = model or "configured-model"
        return (
            ModelPricing(
                model=custom_model,
                input_per_million_usd=input_rate,
                cached_input_per_million_usd=(
                    config.openai_cached_input_cost_per_million_usd
                    if config.openai_cached_input_cost_per_million_usd is not None
                    else input_rate
                ),
                cache_write_per_million_usd=(
                    config.openai_cache_write_cost_per_million_usd
                    if config.openai_cache_write_cost_per_million_usd is not None
                    else input_rate
                ),
                output_per_million_usd=output_rate,
                source_url="environment configuration",
                verified_on=PRICING_CATALOG_VERSION,
            ),
            True,
        )

    return (
        replace(
            catalog_pricing,
            input_per_million_usd=(
                config.openai_input_cost_per_million_usd
                if config.openai_input_cost_per_million_usd is not None
                else catalog_pricing.input_per_million_usd
            ),
            cached_input_per_million_usd=(
                config.openai_cached_input_cost_per_million_usd
                if config.openai_cached_input_cost_per_million_usd is not None
                else catalog_pricing.cached_input_per_million_usd
            ),
            cache_write_per_million_usd=(
                config.openai_cache_write_cost_per_million_usd
                if config.openai_cache_write_cost_per_million_usd is not None
                else catalog_pricing.cache_write_per_million_usd
            ),
            output_per_million_usd=(
                config.openai_output_cost_per_million_usd
                if config.openai_output_cost_per_million_usd is not None
                else catalog_pricing.output_per_million_usd
            ),
        ),
        used_override,
    )


def _estimate_chunk(usage: dict[str, Any], pricing: ModelPricing) -> tuple[float, bool]:
    input_tokens = int(usage.get("input_tokens", 0))
    cached_tokens = int(usage.get("cached_input_tokens", 0))
    cache_write_tokens = int(usage.get("cache_write_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    uncached_input = max(0, input_tokens - cached_tokens - cache_write_tokens)
    long_context = bool(
        pricing.long_context_threshold_tokens is not None
        and input_tokens > pricing.long_context_threshold_tokens
    )
    input_multiplier = pricing.long_context_input_multiplier if long_context else 1.0
    output_multiplier = pricing.long_context_output_multiplier if long_context else 1.0
    amount = (
        (
            uncached_input * pricing.input_per_million_usd
            + cached_tokens * pricing.cached_input_per_million_usd
            + cache_write_tokens * pricing.cache_write_per_million_usd
        )
        * input_multiplier
        + output_tokens * pricing.output_per_million_usd * output_multiplier
    ) / 1_000_000
    return amount, long_context


def _estimated_cost(
    *,
    interaction: dict[str, Any],
    model: str | None,
    config: AppConfig,
) -> _CostEstimate:
    usage: dict[str, Any] = interaction.get("usage", {})
    token_count = int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0))
    pricing, used_override = _effective_pricing(model, config)
    if pricing is None:
        return _CostEstimate(0.0 if token_count == 0 else None, None, False, used_override)

    chunks: list[dict[str, Any]] = interaction.get("usage_by_response", []) or [usage]
    estimates = [_estimate_chunk(chunk, pricing) for chunk in chunks]
    return _CostEstimate(
        amount_usd=round(sum(amount for amount, _ in estimates), 8),
        pricing=pricing,
        long_context_applied=any(applied for _, applied in estimates),
        used_override=used_override,
    )


def build_usage_report(
    *,
    run_id: str,
    telemetry: InteractionTelemetry,
    config: AppConfig,
    wall_clock_ms: int,
) -> UsageReport:
    records: list[AgentUsageRecord] = []
    override_used = False
    missing_pricing_models: set[str] = set()
    for interaction in telemetry.interactions:
        usage: dict[str, Any] = interaction.get("usage", {})
        metadata: dict[str, Any] = interaction.get("metadata", {})
        model = str(metadata.get("model")) if metadata.get("model") else None
        input_tokens = int(usage.get("input_tokens", 0))
        cached_tokens = int(usage.get("cached_input_tokens", 0))
        output_tokens = int(usage.get("output_tokens", 0))
        estimate = _estimated_cost(interaction=interaction, model=model, config=config)
        override_used = override_used or estimate.used_override
        if estimate.amount_usd is None and model:
            missing_pricing_models.add(model)
        pricing = estimate.pricing
        records.append(
            AgentUsageRecord(
                interaction_id=str(interaction["interaction_id"]),
                agent=str(interaction["agent"]),
                stage=str(interaction["stage"]),
                model=model,
                status=str(interaction.get("status", "unknown")),
                requests=int(usage.get("requests", 0)),
                input_tokens=input_tokens,
                cached_input_tokens=cached_tokens,
                cache_write_tokens=int(usage.get("cache_write_tokens", 0)),
                output_tokens=output_tokens,
                reasoning_tokens=int(usage.get("reasoning_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
                duration_ms=int(interaction.get("duration_ms", 0)),
                approximate_cost_usd=estimate.amount_usd,
                pricing_model=pricing.model if pricing else None,
                pricing_source_url=pricing.source_url if pricing else None,
                pricing_verified_on=pricing.verified_on if pricing else None,
                input_rate_per_million_usd=(
                    pricing.input_per_million_usd if pricing else None
                ),
                cached_input_rate_per_million_usd=(
                    pricing.cached_input_per_million_usd if pricing else None
                ),
                cache_write_rate_per_million_usd=(
                    pricing.cache_write_per_million_usd if pricing else None
                ),
                output_rate_per_million_usd=(
                    pricing.output_per_million_usd if pricing else None
                ),
                long_context_pricing_applied=estimate.long_context_applied,
            )
        )

    costs = [record.approximate_cost_usd for record in records]
    cost_available = bool(records) and all(cost is not None for cost in costs)
    pricing_note = (
        f"Estimated token cost uses OpenAI standard API rates verified "
        f"{PRICING_CATALOG_VERSION}. It is not an invoice amount. The estimate excludes "
        "web-search and other hosted-tool charges, alternate service-tier pricing, regional "
        "processing uplifts, taxes, credits, and pricing changes after the verification date."
    )
    if override_used:
        pricing_note += " Configured environment rates override applicable catalog rates."
    if missing_pricing_models:
        pricing_note += (
            " No estimate is available for token-bearing interactions using: "
            + ", ".join(sorted(missing_pricing_models))
            + "."
        )

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
            round(sum(float(cost) for cost in costs if cost is not None), 8)
            if cost_available
            else None
        ),
        pricing_note=pricing_note,
        pricing_catalog_version=PRICING_CATALOG_VERSION,
        pricing_source_url=PRICING_SOURCE_URL,
    )
