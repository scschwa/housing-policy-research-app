# Threat model

## Assets

- source provenance, URLs, dates, excerpts, and safety flags;
- user questions and optional audience/context fields;
- API credentials and model configuration;
- report integrity, citations, branch status, and evaluation artifacts;
- reproducibility of offline runs.

## Trust boundaries

1. User input crosses into intake guardrails.
2. Search results cross from an external provider into the research adapter.
3. Specialist findings cross into the source ledger and manager synthesis.
4. Draft prose crosses into deterministic validation and adversarial review.
5. Artifacts cross from process memory to disk and version control.

## Threats and controls

| Threat | Control | Residual risk |
|---|---|---|
| Direct or indirect prompt injection | `inspect_untrusted_text`, source safety flags, fixed agent instructions, no tool/role mutation from excerpts | novel injection wording may evade simple lexical patterns |
| Fabricated or nonexistent citation | typed source ledger plus claim/report reference validation | citation correctness still needs human or model review |
| Malicious targeted exclusion request | housing relevance and discrimination guardrails reject targeted unlawful exclusion | legitimate analysis of discriminatory policy must be carefully scoped |
| Sensitive personal data | request scope checks, no need for personal data, trace sensitive-data logging disabled by default | users can still paste sensitive content; deployment redaction is recommended |
| Unsupported legal advice | legal branch uses calibrated language and report disclosure | live model may overstate; formal counsel remains necessary |
| Source duplication or metadata invention | URL/content-hash deduplication and explicit missing metadata fields | near-duplicate semantic sources require additional similarity tooling |
| Budget or runaway tool use | max turns, sources, searches, retries, concurrency, and total-time configuration | live provider outages can still waste some bounded calls |
| Secret leakage | no secrets in repository, `.env` ignored, trace sensitive data false, security assertion checks common leakage strings | deployment logs and hosted provider policies still require review |
| Artifact tampering | JSON schema validation, run IDs, explicit artifact set, source ledger | local filesystem permissions and retention are deployment concerns |

The fixture intentionally includes a malicious source. Expected behavior is to retain it for auditability, flag it, ignore its instructions, and exclude it from substantive support.
