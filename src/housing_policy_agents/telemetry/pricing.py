"""Versioned OpenAI standard API token-price catalog."""

from __future__ import annotations

from dataclasses import dataclass

PRICING_CATALOG_VERSION = "2026-08-15"
PRICING_SOURCE_URL = "https://developers.openai.com/api/docs/pricing"


@dataclass(frozen=True)
class ModelPricing:
    """Per-million-token rates used to estimate one model response."""

    model: str
    input_per_million_usd: float
    cached_input_per_million_usd: float
    cache_write_per_million_usd: float
    output_per_million_usd: float
    source_url: str
    verified_on: str = PRICING_CATALOG_VERSION
    long_context_threshold_tokens: int | None = None
    long_context_input_multiplier: float = 1.0
    long_context_output_multiplier: float = 1.0


def _model_url(model: str) -> str:
    return f"https://developers.openai.com/api/docs/models/{model}"


# Standard synchronous API rates in USD per one million tokens. For models whose
# official page does not list a distinct cache-write rate, writes use the regular
# input rate. Tool-call charges and alternate processing tiers are intentionally
# outside this token-only catalog.
MODEL_PRICING: dict[str, ModelPricing] = {
    "gpt-5.6-luna": ModelPricing(
        "gpt-5.6-luna", 0.20, 0.02, 0.25, 1.20, _model_url("gpt-5.6-luna"),
        long_context_threshold_tokens=272_000,
        long_context_input_multiplier=2.0,
        long_context_output_multiplier=1.5,
    ),
    "gpt-5.6-terra": ModelPricing(
        "gpt-5.6-terra", 2.00, 0.20, 2.50, 12.00, _model_url("gpt-5.6-terra"),
        long_context_threshold_tokens=272_000,
        long_context_input_multiplier=2.0,
        long_context_output_multiplier=1.5,
    ),
    "gpt-5.6-sol": ModelPricing(
        "gpt-5.6-sol", 5.00, 0.50, 6.25, 30.00, _model_url("gpt-5.6-sol"),
        long_context_threshold_tokens=272_000,
        long_context_input_multiplier=2.0,
        long_context_output_multiplier=1.5,
    ),
    "gpt-5.5": ModelPricing(
        "gpt-5.5", 5.00, 0.50, 5.00, 30.00, _model_url("gpt-5.5"),
        long_context_threshold_tokens=272_000,
        long_context_input_multiplier=2.0,
        long_context_output_multiplier=1.5,
    ),
    "gpt-5.4": ModelPricing(
        "gpt-5.4", 2.50, 0.25, 2.50, 15.00, _model_url("gpt-5.4"),
        long_context_threshold_tokens=272_000,
        long_context_input_multiplier=2.0,
        long_context_output_multiplier=1.5,
    ),
    "gpt-5.4-mini": ModelPricing(
        "gpt-5.4-mini", 0.75, 0.075, 0.75, 4.50, _model_url("gpt-5.4-mini")
    ),
    "gpt-5.4-nano": ModelPricing(
        "gpt-5.4-nano", 0.20, 0.02, 0.20, 1.25, _model_url("gpt-5.4-nano")
    ),
    "gpt-5.2": ModelPricing(
        "gpt-5.2", 1.75, 0.175, 1.75, 14.00, _model_url("gpt-5.2")
    ),
    "gpt-5": ModelPricing(
        "gpt-5", 1.25, 0.125, 1.25, 10.00, _model_url("gpt-5")
    ),
    "gpt-5-mini": ModelPricing(
        "gpt-5-mini", 0.25, 0.025, 0.25, 2.00, _model_url("gpt-5-mini")
    ),
    "gpt-5-nano": ModelPricing(
        "gpt-5-nano", 0.05, 0.005, 0.05, 0.40, _model_url("gpt-5-nano")
    ),
}

MODEL_ALIASES = {
    "gpt-5.6": "gpt-5.6-sol",
}


def resolve_model_pricing(model: str | None) -> ModelPricing | None:
    """Resolve aliases and dated snapshots without broad prefix collisions."""
    if not model:
        return None
    normalized = model.strip().lower()
    normalized = MODEL_ALIASES.get(normalized, normalized)
    exact = MODEL_PRICING.get(normalized)
    if exact is not None:
        return exact
    for catalog_model in sorted(MODEL_PRICING, key=len, reverse=True):
        if normalized.startswith(f"{catalog_model}-"):
            return MODEL_PRICING[catalog_model]
    return None
