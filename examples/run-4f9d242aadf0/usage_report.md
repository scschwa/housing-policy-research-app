# Usage report

- **Run:** `run-4f9d242aadf0`
- **Model:** `gpt-5.6-terra`
- **Requests:** 16
- **Input tokens:** 476,850
- **Cached input tokens:** 0
- **Cache-write tokens:** 217,131
- **Output tokens:** 72,830
- **Reasoning tokens:** 2,691
- **Total tokens:** 549,680
- **Wall-clock time:** 252.38 seconds
- **Cumulative agent time:** 735.04 seconds
- **Estimated token cost:** $1.93622550

Estimated token cost uses OpenAI standard API rates verified 2026-08-15. It is not an invoice amount. The estimate excludes web-search and other hosted-tool charges, alternate service-tier pricing, regional processing uplifts, taxes, credits, and pricing changes after the verification date.

Agent durations are cumulative and may exceed wall-clock time because branches run concurrently.

## Agent and sub-agent breakdown

| Agent | Stage | Model | Status | Requests | Input | Cached | Cache write | Output | Reasoning | Total | Time (s) | Est. token cost |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| government_sources_researcher | research | gpt-5.6-terra | completed | 1 | 39,180 | 0 | 8,147 | 5,302 | 356 | 44,482 | 60.87 | $0.14605750 |
| legal_regulatory_researcher | research | gpt-5.6-terra | completed | 1 | 24,306 | 0 | 8,130 | 4,282 | 219 | 28,588 | 42.78 | $0.10406100 |
| think_tank_academic_researcher | research | gpt-5.6-terra | completed | 1 | 33,091 | 0 | 8,109 | 3,649 | 228 | 36,740 | 42.43 | $0.11402450 |
| consumer_researcher | research | gpt-5.6-terra | completed | 1 | 30,825 | 0 | 8,017 | 4,555 | 251 | 35,380 | 52.01 | $0.12031850 |
| loan_originator_researcher | research | gpt-5.6-terra | completed | 1 | 34,135 | 0 | 7,964 | 3,983 | 196 | 38,118 | 48.57 | $0.12004800 |
| servicing_researcher | research | gpt-5.6-terra | completed | 1 | 33,298 | 0 | 8,011 | 4,636 | 278 | 37,934 | 52.88 | $0.12623350 |
| secondary_market_risk_transfer_researcher | research | gpt-5.6-terra | completed | 1 | 32,577 | 0 | 8,034 | 5,786 | 298 | 38,363 | 59.44 | $0.13860300 |
| general_consumer_advocacy_researcher | research | gpt-5.6-terra | completed | 1 | 39,007 | 0 | 7,998 | 4,958 | 304 | 43,965 | 50.11 | $0.14150900 |
| disadvantaged_communities_researcher | research | gpt-5.6-terra | completed | 1 | 32,631 | 0 | 8,009 | 5,993 | 268 | 38,624 | 61.53 | $0.14118250 |
| financial_sustainability_researcher | research | gpt-5.6-terra | completed | 1 | 41,091 | 0 | 8,021 | 4,699 | 293 | 45,790 | 58.23 | $0.14258050 |
| policy_research_manager | reconciliation | gpt-5.6-terra | completed | 1 | 19,106 | 0 | 19,103 | 3,615 | 0 | 22,721 | 31.55 | $0.09114350 |
| industry_research_manager | reconciliation | gpt-5.6-terra | completed | 1 | 26,266 | 0 | 26,263 | 4,307 | 0 | 30,573 | 37.40 | $0.11734750 |
| advocacy_research_manager | reconciliation | gpt-5.6-terra | completed | 1 | 22,058 | 0 | 22,055 | 3,649 | 0 | 25,707 | 32.87 | $0.09893150 |
| synthesis_writer | draft | gpt-5.6-terra | completed | 1 | 16,869 | 0 | 16,866 | 6,240 | 0 | 23,109 | 56.10 | $0.11705100 |
| adversarial_reviewer | review | gpt-5.6-terra | completed | 1 | 41,920 | 0 | 41,917 | 831 | 0 | 42,751 | 8.86 | $0.11477050 |
| synthesis_writer_revision | revision | gpt-5.6-terra | completed | 1 | 10,490 | 0 | 10,487 | 6,345 | 0 | 16,835 | 39.42 | $0.10236350 |

## Pricing basis

Rates are USD per one million tokens. Cache-write rates equal regular input rates where OpenAI does not publish a distinct write rate.

| Requested model | Pricing model | Input | Cached input | Cache write | Output | Source |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| gpt-5.6-terra | gpt-5.6-terra | 2.000 | 0.200 | 2.500 | 12.000 | [official model page](https://developers.openai.com/api/docs/models/gpt-5.6-terra) |
