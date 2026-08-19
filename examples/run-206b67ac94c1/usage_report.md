# Usage report

- **Run:** `run-206b67ac94c1`
- **Model:** `gpt-5.6-terra`
- **Requests:** 7
- **Input tokens:** 185,338
- **Cached input tokens:** 0
- **Cache-write tokens:** 82,790
- **Output tokens:** 31,447
- **Reasoning tokens:** 1,113
- **Total tokens:** 216,785
- **Wall-clock time:** 201.64 seconds
- **Cumulative agent time:** 306.52 seconds
- **Estimated token cost:** $0.78943500

Estimated token cost uses OpenAI standard API rates verified 2026-08-15. It is not an invoice amount. The estimate excludes web-search and other hosted-tool charges, alternate service-tier pricing, regional processing uplifts, taxes, credits, and pricing changes after the verification date.

Agent durations are cumulative and may exceed wall-clock time because branches run concurrently.

## Agent and sub-agent breakdown

| Agent | Stage | Model | Status | Requests | Input | Cached | Cache write | Output | Reasoning | Total | Time (s) | Est. token cost |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| government_sources_researcher | research | gpt-5.6-terra | completed | 1 | 49,804 | 0 | 8,138 | 4,640 | 369 | 54,444 | 55.34 | $0.15935700 |
| legal_regulatory_researcher | research | gpt-5.6-terra | completed | 1 | 44,113 | 0 | 8,120 | 6,352 | 498 | 50,465 | 63.57 | $0.16851000 |
| think_tank_academic_researcher | research | gpt-5.6-terra | completed | 1 | 32,976 | 0 | 8,099 | 4,361 | 246 | 37,337 | 49.85 | $0.12233350 |
| policy_research_manager | reconciliation | gpt-5.6-terra | completed | 1 | 21,486 | 0 | 21,483 | 3,732 | 0 | 25,218 | 32.72 | $0.09849750 |
| synthesis_writer | draft | gpt-5.6-terra | completed | 1 | 7,001 | 0 | 6,998 | 5,615 | 0 | 12,616 | 58.58 | $0.08488100 |
| adversarial_reviewer | review | gpt-5.6-terra | completed | 1 | 20,022 | 0 | 20,019 | 1,084 | 0 | 21,106 | 11.86 | $0.06306150 |
| synthesis_writer_revision | revision | gpt-5.6-terra | completed | 1 | 9,936 | 0 | 9,933 | 5,663 | 0 | 15,599 | 34.60 | $0.09279450 |

## Pricing basis

Rates are USD per one million tokens. Cache-write rates equal regular input rates where OpenAI does not publish a distinct write rate.

| Requested model | Pricing model | Input | Cached input | Cache write | Output | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| gpt-5.6-terra | gpt-5.6-terra | 2.000 | 0.200 | 2.500 | 12.000 | [official model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |
