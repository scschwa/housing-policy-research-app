# Agent contracts

All contracts are Pydantic models in `src/housing_policy_agents/models/domain.py`. Agents may return only their declared typed output; source IDs must resolve through the source ledger before release.

| Agent | Input | Output | Tools | Prohibited behavior |
|---|---|---|---|---|
| Research Orchestrator | `UserResearchRequest`, optional answers | `ResearchBrief`, `ResearchPlan`, workflow package | bounded manager tools | asking more than five questions, silently dropping a failed branch, inventing evidence, or bypassing budgets |
| Government Sources Researcher | `ResearchAssignment` | `SpecialistFinding` | fixture adapter or live `WebSearchTool` | treating political statements as law or fabricating official metadata |
| Legal and Regulatory Researcher | `ResearchAssignment` | `SpecialistFinding` | same | presenting unresolved legal questions as legal advice or definitive holdings |
| Think Tank and Academic Researcher | `ResearchAssignment` | `SpecialistFinding` | same | treating advocacy as causal evidence or hiding contrary research |
| Consumer Researcher | `ResearchAssignment` | `SpecialistFinding` | same | treating consumers as homogeneous or making targeted exclusion recommendations |
| Loan-Originator Researcher | `ResearchAssignment` | `SpecialistFinding` | same | confusing stakeholder incentives with neutral evidence |
| Servicing Researcher | `ResearchAssignment` | `SpecialistFinding` | same | asserting operational feasibility without identifying transfer, escrow, default, and communication constraints |
| Secondary-Market and Risk-Transfer Researcher | `ResearchAssignment` | `SpecialistFinding` | same | omitting prepayment, duration, guarantee, liquidity, or taxpayer exposure |
| General Consumer Advocacy Researcher | `ResearchAssignment` | `SpecialistFinding` | same | suppressing fees, remedies, market-power, or transparency concerns |
| Disadvantaged Communities Researcher | `ResearchAssignment` | `SpecialistFinding` | same | stereotyping groups, inferring protected traits, or collapsing measured disparities into causal claims |
| Financial Sustainability Researcher | `ResearchAssignment` | `SpecialistFinding` | same | ignoring stress, adverse selection, moral hazard, fiscal, or political durability |
| Global Researcher | `ResearchAssignment` | `SpecialistFinding` with comparator evidence | same | listing countries without institutional differences or assuming transplantability |
| Policy Research Manager | three policy findings | `ManagerSynthesis` | policy specialist tools | erasing disagreements or adding unsupported conclusions |
| Industry Research Manager | four industry findings | `ManagerSynthesis` | industry specialist tools | presenting incentive-driven claims as settled facts |
| Advocacy Research Manager | three advocacy findings | `ManagerSynthesis` | advocacy specialist tools | forcing consensus across genuine value conflicts |
| Global Research Manager | global finding | `ManagerSynthesis` | global specialist tool | removing weak-comparability caveats |
| Synthesis Writer | brief, manager syntheses, ledger IDs | `DraftReport` | no broad new research | fabricating citations, consensus, precision, or unsupported legal certainty |
| Adversarial Reviewer | draft, source ledger, accepted evidence | `AdversarialReview` | no report rewrite | rewriting the whole report, hiding security findings, or approving unresolved critical defects |

Managers are callable tools to make the hierarchy inspectable while Python remains the workflow authority. A specialist failure is returned as a `SpecialistFinding` with `FAILED` status and an error, so unavailable perspectives remain visible in artifacts and limitations.
