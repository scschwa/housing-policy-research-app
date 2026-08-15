# Evaluation design

Promptfoo is the default evaluation harness. `evals/promptfooconfig.yaml` uses a deterministic fixture-backed hierarchical provider and a shallow single-agent baseline. Python assertions inspect structured outputs rather than scoring prose alone. The dataset contains more than twenty scenarios spanning intake, research quality, synthesis, adversarial review, agent behavior, security, and varied housing-policy domains.

## Metrics

The suite retains task completion, schema validity, required-section completeness, source-ID validity, citation coverage, source diversity, primary-source coverage, contrary-evidence coverage, stakeholder coverage, legal calibration, uncertainty calibration, review-defect recall, prompt-injection resistance, token/latency/cost metadata, and run stability. The offline provider reports zero token/cost usage because it is fixture-backed; live runs report SDK metadata when available.

## Release gates

Thresholds are centralized in `evals/thresholds.yaml`: 100% schema validity and source resolution, at least 95% fabricated-citation detection, at least 85% seeded-defect recall, at least 90% required-section completeness, zero successful core prompt-injection attacks, at least 80% primary-source coverage for current-law claims, no critical deterministic validation failures, a minimum median rubric score of 4/5, and at least three source tiers or institutions where the question supports it. These are gates, not a replacement for reviewing individual metric columns.

## Comparative experiments

`promptfooconfig.yaml` compares hierarchical and shallow providers. `promptfooconfig.ablation.yaml` compares the full network with legal, global, advocacy, clarification, manager-reconciliation, and adversarial-review ablations. The Python provider maps those settings to `AppConfig`, so branch omission and review omission are explicit and observable. `promptfooconfig.live.yaml` is separate, non-deterministic, and requires an API key plus explicit network permission.

## Interpretation

The primary question is whether the hierarchy improves source coverage, balance, calibration, and seeded-defect recall enough to justify extra latency and cost. Report branch-level results before aggregating. A passing aggregate cannot hide a failed security or citation gate. Suggested next experiments are live primary-source coverage, model-size comparisons, semantic citation correctness grading, and repeated runs for stability intervals.
