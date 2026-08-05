# Implementation plan

1. Establish Python and Promptfoo tooling, repository instructions, and the milestone workflow.
2. Add Pydantic domain contracts, configuration, fixture data, source normalization, validation, and guardrails.
3. Add the OpenAI Agents SDK hierarchy, agent contracts, offline/live research backends, and explicit async workflow.
4. Add CLI interaction, report rendering, artifact persistence, tracing, metrics, and graph output.
5. Add Promptfoo scenarios, providers, assertions, graders, baselines, and ablations.
6. Add unit, integration, golden, security, and evaluation tests; run all checks and record results.

The default acceptance path is a fully offline mortgage-portability demonstration with synthetic sources. Live retrieval is opt-in.

## Completion record

The implementation is complete through the offline acceptance path. The repository now includes the Pydantic contracts, fixture-backed and live research backends, Agents SDK hierarchy, bounded async workflow, source ledger, guardrails, report/artifact outputs, tracing hooks, CLI, Promptfoo evaluation matrix, ablations, and documentation.

Verification performed before publishing:

- `ruff check .` — clean.
- `pytest -q` — 16 passed.
- `mypy --exclude-gitignore src tests evals` — 35 files checked with no issues.
- Offline Promptfoo evaluation — 52/52 cases passed.
- Ablation Promptfoo evaluation — 208/208 cases passed across eight providers.
- Offline demo plus artifact validation — completed with `ok: true`.
- CLI progress smoke test — stage and branch updates printed successfully on Windows-safe ASCII output.

Live evaluation remains opt-in because it requires a configured model/API key and incurs external retrieval/token cost. Synthetic fixtures are intentionally used for deterministic CI and security regression coverage.
