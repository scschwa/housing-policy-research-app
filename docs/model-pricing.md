# Model pricing estimates

The application contains a versioned table of OpenAI standard synchronous API token rates. The current table was verified on 2026-08-15 against the [official API pricing page](https://developers.openai.com/api/docs/pricing) and linked model pages.

All rates below are USD per one million tokens.

| Model | Input | Cached input | Cache write | Output | Long-context adjustment |
| --- | ---: | ---: | ---: | ---: | --- |
| `gpt-5.6-luna` | 0.20 | 0.02 | 0.25 | 1.20 | Above 272K input tokens: input categories 2x, output 1.5x |
| `gpt-5.6-terra` | 2.00 | 0.20 | 2.50 | 12.00 | Above 272K input tokens: input categories 2x, output 1.5x |
| `gpt-5.6-sol` | 5.00 | 0.50 | 6.25 | 30.00 | Above 272K input tokens: input categories 2x, output 1.5x |
| `gpt-5.5` | 5.00 | 0.50 | 5.00 | 30.00 | Above 272K input tokens: input categories 2x, output 1.5x |
| `gpt-5.4` | 2.50 | 0.25 | 2.50 | 15.00 | Above 272K input tokens: input categories 2x, output 1.5x |
| `gpt-5.4-mini` | 0.75 | 0.075 | 0.75 | 4.50 | None |
| `gpt-5.4-nano` | 0.20 | 0.02 | 0.20 | 1.25 | None |
| `gpt-5.2` | 1.75 | 0.175 | 1.75 | 14.00 | None |
| `gpt-5` | 1.25 | 0.125 | 1.25 | 10.00 | None |
| `gpt-5-mini` | 0.25 | 0.025 | 0.25 | 2.00 | None |
| `gpt-5-nano` | 0.05 | 0.005 | 0.05 | 0.40 | None |

`gpt-5.6` resolves to `gpt-5.6-sol`, consistent with the official alias. Dated snapshots such as `gpt-5-mini-2025-08-07` resolve to their base-model rate. A distinct cache-write rate is used where the model page publishes one; otherwise cache writes are estimated at the regular input rate.

## Estimate boundaries

The usage artifact calculates each response separately so long-context pricing is applied at the request level. Reasoning tokens are already included in output token totals and are not charged a second time.

The result is an estimate, not an invoice amount. It excludes web-search and other hosted-tool call charges, file-search storage, alternate service tiers such as Batch, Flex, or Priority, regional processing uplifts, taxes, credits, and pricing changes after the catalog verification date. Unknown models produce no cost estimate unless the rate override environment variables provide at least input and output rates.

## Updating the table

Update `telemetry/pricing.py`, the verification date, this table, and the pricing tests together after checking the official pricing and model pages. Environment rate overrides take precedence over catalog values and allow an operator to correct a rate without a code release.
