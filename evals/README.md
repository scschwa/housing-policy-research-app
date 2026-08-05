# Promptfoo evaluation suite

The default suite is offline and fixture-backed:

```powershell
# Activate the same Python environment that has the project dependencies.
.\.venv\Scripts\Activate.ps1
npm ci
npm run eval:offline
```

To run the required ablation comparisons:

```powershell
npm run eval:ablation
```

It compares the complete hierarchical provider with a shallow single-agent baseline across intake, research quality, synthesis, adversarial review, agentic behavior, security, and realistic housing-policy scenarios.

Python providers return structured JSON packages. Python assertions score schema validity, source-ID resolution, required sections, citation coverage, review presence, prompt-injection resistance, and leakage resistance. `thresholds.yaml` centralizes release gates.

Live evaluation is intentionally separate and non-deterministic. It requires explicit network access and an OpenAI API key. Offline fixtures are synthetic and are not evidence for real policy decisions.
