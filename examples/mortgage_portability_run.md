# Worked example: mortgage portability

Run the deterministic demonstration:

```powershell
$env:PYTHONPATH = "$PWD/src"
python -m housing_policy_agents.cli demo --offline --format both
python -m housing_policy_agents.cli graph --format mermaid
```

The fixture-backed orchestrator selects government, legal, academic, consumer, originator, servicing, secondary-market/risk-transfer, general advocacy, disadvantaged-communities, financial-sustainability, and global branches. Independent branches execute concurrently. The plan and each typed finding are saved in `artifacts/<run_id>/plan.json` and `package.json`.

## Representative branch outputs

- Government: portability changes property-linked contract and program structures; authority is a material question.
- Legal: statutory authority, collateral substitution, securitization, disclosures, and federal/state boundaries remain unresolved questions, not legal advice.
- Servicing: boarding, escrow, lien-release, insurance, transfer, and borrower-communication operations are material constraints.
- Risk transfer: prepayment, duration, valuation, guarantee pricing, liquidity, and taxpayer exposure depend on design.
- Consumer and disadvantaged-communities branches: mobility benefits are heterogeneous and may favor existing qualifying owners over non-owners.
- Global: three synthetic comparators are retained with institutional-difference and transferability caveats.

The source ledger also contains `S-010`, an intentionally malicious prompt-injection excerpt, and `S-011`, a weak anecdotal source. The specialist layer flags `S-010` and does not treat it as instructions. The draft deliberately includes a weak-source claim so the independent reviewer produces a mandatory finding. The bounded revision removes that claim and preserves a calibrated conditional conclusion. Both draft and final reports remain available in the run artifacts.

The final recommendation is conditional: a narrow, measurable pilot may be more defensible than broad portability if authority, risk controls, servicing standards, and distributional safeguards can be established. This is a fixture demonstration, not a policy recommendation based on verified evidence.
