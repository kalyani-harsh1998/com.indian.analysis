# Controlled evaluation corpus registry

## Purpose

The golden-case evaluator is useful only when its expected dispositions, values, and reconciliations are trustworthy. This registry is the Phase 2D control for moving a **permitted real-company filing** from local source evidence to an evaluation case that may gate a future live onboarding model.

It does not retrieve documents, call a model, approve an onboarding configuration, or make a financial conclusion. It records the local artefacts and review status that must already exist. Raw reports, local manifests, registry entries, and generated evaluations live under ignored `data/` paths. Do not commit a source report, a real-company fixture, or output from this workflow.

## Required lineage

One `EvaluationCorpusEntry` carries the immutable source-document manifest, a benchmarked `DocumentExtractionLink` with `review_status: reviewed`, the exact checksummed onboarding request, and a candidate `OnboardingEvaluationFixture` containing every expected disposition, deterministic expected value, reconciliation, and threshold.

The registry validates that document ID, company, document type, source-reference ID, source organization, source checksum, extraction ID, and extraction profile agree across the artefacts. It records a SHA-256 digest of the complete fixture so an approved reviewer record cannot be separated from the values and decisions reviewed.

## Review states

| State | Meaning | Can gate a live model? |
| --- | --- | --- |
| `ready_for_ca_review` | A candidate fixture is present and the deterministic extraction has been reviewed. It has no CA approval metadata. | No |
| `provisional_internal_review` | A named internal reviewer has checked the exact fixture and recorded notes under an internal policy. It may be used only by the separately labelled internal evaluator. | No |
| `approved_for_evaluation` | A non-synthetic, licence-assessed permitted filing has a fixture checksum, named CA reviewer, timezone-aware review time, policy version, and review notes. | Yes |
| `rejected` | The reviewer recorded policy/version/time and reasons. No evaluable fixture remains attached. | No |

Only an `approved_for_evaluation` entry is returned by `LocalEvaluationCorpusCatalog.get_approved`. An internal reviewer may instead record `provisional_internal_review` for a permitted real case, with a fixture checksum, named reviewer, timezone-aware timestamp, internal-policy version, and notes. `get_provisionally_reviewed_for_internal_evaluation` retrieves only that state; it cannot retrieve an approved, candidate, synthetic, or rejected case. The code rejects synthetic sources, unassessed or restricted licences, unreviewed/rejected extraction links, changed fixture contents, missing review information, and mismatched request lineage.

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

To record a new provisional internal-review version from a candidate entry without modifying that candidate:

```bash
uv run python -m indian_company_analysis provisionally-review-evaluation-corpus \
  --entry /path/to/candidate-corpus-entry.json \
  --corpus-version provisional-v1 \
  --reviewed-by "Internal reviewer name" \
  --reviewed-at 2026-10-01T15:00:00+05:30 \
  --review-policy-version internal-review-v1 \
  --review-note "Reviewed for internal workflow testing; not CA approval."
```

This command accepts only `ready_for_ca_review` input and creates a new record. It cannot modify, promote, or overwrite the candidate entry.

After CA approval, use `evaluate-approved-corpus` rather than passing the fixture to the generic evaluator. That command retrieves only an `approved_for_evaluation` entry before it evaluates the saved provider proposal.

When a CA review is not available, a permitted real entry with `provisional_internal_review` may be exercised using the separate command:

```bash
uv run python -m indian_company_analysis evaluate-provisional-corpus \
  --entry-id company-fy2026-income-statement \
  --corpus-version provisional-v1 \
  --proposal /path/to/local-provider-proposal.json
```

Its persisted report is marked `evaluation_qualification: provisional_internal_review` and is stored separately by default. It is suitable for developing the local workflow and finding defects, but it does not demonstrate real-model accuracy, authorize a live provider, create an approved onboarding configuration, or substitute for CA approval. See [onboarding proposal evaluation](ONBOARDING_EVALUATION.md).

## Provisional corpus summary

When several provisional entries exist, `evaluate-provisional-corpus-set` evaluates the saved proposal for each case and applies an explicit local policy: a minimum number of cases and distinct companies, minimum pass rate, and maximum failed cases. It writes one append-only summary containing every underlying evaluation report, aggregate counts, pass rate, and the policy outcome.

For example, the current three-case internal corpus can be checked as follows:

```bash
uv run python -m indian_company_analysis evaluate-provisional-corpus-set \
  --entry-id infosys-fy2026-consolidated-profit-loss-corpus-v1 \
  --corpus-version provisional-internal-v1 \
  --proposal /path/to/infosys-candidate.json \
  --entry-id tcs-fy2026-consolidated-profit-loss-corpus-v1 \
  --corpus-version provisional-internal-v1 \
  --proposal /path/to/tcs-candidate.json \
  --entry-id apsez-fy2026-consolidated-profit-loss-corpus-v1 \
  --corpus-version provisional-internal-v1 \
  --proposal /path/to/apsez-candidate.json \
  --run-id fy2026-internal-corpus-v1 \
  --policy-version internal-corpus-policy-v1 \
  --minimum-case-count 3 \
  --minimum-distinct-company-count 3
```

An internal-policy pass means only that the declared provisional cases met the local threshold. Every summary is permanently marked `evaluation_qualification: provisional_internal_review`, sets `live_model_eligible: false`, and records an explicit live-model blocker. It cannot replace CA approval, a representative CA-reviewed corpus, privacy controls, prompt-isolation tests, or future provider-specific gates.

## Scope and next work

Committed test cases remain explicitly synthetic and are not registered as approved real-company cases. The first real corpus should deliberately cover multiple companies, layouts, periods, terminology changes, aggregations, exclusions, and safe abstentions.

Before a live provider is connected, we still need a representative CA-approved corpus, CA-approved corpus-level pass-rate and failure-budget policies, privacy/evidence-minimization controls, prompt-isolation tests, provider error/retry behavior, cost/latency budgets, and model/prompt/schema comparison rules. The implemented provisional summary is local workflow evidence only; provisional internal review does not relax deterministic validation or CA approval.
