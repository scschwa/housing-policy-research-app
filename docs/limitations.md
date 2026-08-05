# Limitations

- Offline fixtures are synthetic evaluation records. They demonstrate workflow behavior, not real-world evidence.
- The live adapter delegates search to the Agents SDK web-search tool, but live source extraction, source verification, and citation correctness still require deployment testing and human review.
- The current offline writer is deterministic and intentionally narrow to the mortgage-portability demonstration. Other questions exercise branch selection and the evaluation interface but do not yet have domain-specific fixture claims.
- Source deduplication uses normalized URLs and excerpt hashes; it is not a full semantic near-duplicate detector.
- The simple injection detector is lexical. It is a defense-in-depth control, not a proof that arbitrary malicious content is harmless.
- Qualitative decision-matrix scores are not forecasts and do not imply that a higher score is always preferable.
- The workflow records bounded retries and latency, but exact live token/cost accounting depends on SDK/provider response metadata and should be instrumented further in production.
- No report is legal, financial, or investment advice. Current law, regulations, sources, and forecasts must be independently verified before formal reliance.
- A production deployment should add authentication, encrypted artifact storage, retention controls, stronger PII redaction, semantic source matching, domain allowlists, and human approval for release.
