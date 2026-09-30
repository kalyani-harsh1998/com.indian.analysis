# CA-reviewed evaluation corpus registry

## Purpose

The golden-case evaluator is useful only when its expected dispositions, values, and reconciliations are trustworthy. This registry is the Phase 2D control for moving a **permitted real-company filing** from local source evidence to an evaluation case that may gate a future live onboarding model.

It does not retrieve documents, call a model, approve an onboarding configuration, or make a financial conclusion. It records the local artefacts and CA review that must already exist. Raw reports, local manifests, registry entries, and generated evaluations live under ignored `data/` paths. Do not commit a source report, a real-company fixture, or output from this workflow.

## Required lineage

One `EvaluationCorpusEntry` carries the immutable source-document manifest, a benchmarked `DocumentExtractionLink` with `review_status: reviewed`, the exact checksummed onboarding request, and a candidate `OnboardingEvaluationFixture` containing every expected disposition, deterministic expected value, reconciliation, and threshold.

The registry validates that document ID, company, document type, source-reference ID, source organization, source checksum, extraction ID, and extraction profile agree across the artefacts. It records a SHA-256 digest of the complete fixture so an approved reviewer record cannot be separated from the values and decisions reviewed.

## Review states

| State | Meaning | Can gate a live model? |
| --- | --- | --- |
| `ready_for_ca_review` | A candidate fixture is present and the deterministic extraction has been reviewed. It has no CA approval metadata. | No |
| `approved_for_evaluation` | A non-synthetic, licence-assessed permitted filing has a fixture checksum, named CA reviewer, timezone-aware review time, policy version, and review notes. | Yes |
| `rejected` | The reviewer recorded policy/version/time and reasons. No evaluable fixture remains attached. | No |

Only an `approved_for_evaluation` entry is returned by `LocalEvaluationCorpusCatalog.get_approved`. The code rejects synthetic sources, unassessed or restricted licences, unreviewed/rejected extraction links, changed fixture contents, missing review information, and mismatched request lineage from that state.

## CA review checklist

For each candidate fixture, the reviewer should record enough notes to show that they checked:

- the source is permitted for this local POC use and the licence category is correctly recorded;
- the source report and extracted CSV identities/checksums match the extraction link;
- page, table, row, and column locators point to the intended reported values;
- unit, fiscal period, reporting basis, and statement context are correct;
- every source row is disposed of exactly once as a direct mapping, aggregation component, exclusion, or expected abstention;
- aggregation signs/components and expected deterministic values are correct;
- declared reconciliations are appropriate and pass at the documented tolerance; and
- ambiguous, missing, duplicate, adversarial, or instruction-like source text has the correct expected outcome.

The reviewer’s approval applies to the exact fixture checksum and source checksum. A change to either needs a new corpus version and review; it must not overwrite the prior record.

## Local registration

Prepare the strict JSON entry locally from the existing manifest, extraction link, onboarding request, and candidate fixture, then register it once:

```bash
uv run python -m indian_company_analysis register-evaluation-corpus \
  --entry /path/to/local-corpus-entry.json
```

The default catalog is `data/interim/evaluation-corpus/`. It is append-only: replaying identical JSON is harmless, while attempting to write different content at the same entry ID and corpus version fails. A custom local catalog location may be supplied with `--catalog-root`.

## Scope and next work

Committed test cases remain explicitly synthetic and are not registered as approved real-company cases. The first real corpus should deliberately cover multiple companies, layouts, periods, terminology changes, aggregations, exclusions, and safe abstentions.

Before a live provider is connected, we still need corpus-level pass-rate and failure-budget policies, privacy/evidence-minimization controls, prompt-isolation tests, provider error/retry behavior, cost/latency budgets, and model/prompt/schema comparison rules. The registry is the audit boundary for those future evaluations; it does not relax deterministic validation or human approval.
