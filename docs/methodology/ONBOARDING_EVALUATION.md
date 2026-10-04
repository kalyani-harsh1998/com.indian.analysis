# Onboarding proposal evaluation

## Purpose

Phase 2D evaluates a model-assisted onboarding proposal before any live provider is allowed into the normalization workflow. The evaluator compares a provider-neutral `DocumentOnboardingProposal` with a versioned, human-reviewed golden fixture. It does not approve mappings, create facts, or make model output authoritative.

The initial committed fixture is explicitly synthetic. It proves the evaluation contract and accounting checks; it is not evidence of accuracy on real-company reports.

## Golden fixture

An `OnboardingEvaluationFixture` freezes:

- the exact checksummed onboarding request and source-row locators;
- expected direct mappings, signed-sum aggregations, and explicit exclusions;
- expected abstentions for rows that should be escalated rather than guessed;
- expected canonical metric values;
- linear accounting reconciliation expectations and tolerances; and
- pass/fail thresholds for each metric.

Golden decisions must account for every evidence row exactly once. Canonical targets, expected values, and reconciliation identifiers must be unique. A future real-report corpus must be built only from permitted documents and independently reviewed mappings.

## Measurements and gates

`OnboardingProposalEvaluator` calls the same provider protocol used by future live adapters, reruns deterministic proposal validation, and records:

- precision and recall for mappings, aggregations, exclusions, and abstentions;
- evidence coverage;
- hallucinated, duplicated, and unaccounted evidence counts;
- exact decision-set match;
- deterministic canonical-value comparisons; and
- accounting reconciliation results.

A case passes only when all configured thresholds and required checks pass. The report retains the complete proposal, validation issues, provider/model/version, prompt and schema versions, generation time, and optional input/output token, latency, estimated-cost, and currency metadata. Missing usage metadata stays explicit rather than being estimated silently.

An abstention is an explicit, locator-backed request for a human decision. It counts as a valid evidence disposition and can therefore pass an evaluation case designed to test safe deferral. It cannot be promoted to an approved normalization configuration: the reviewer must resolve it as a mapping, aggregation, or exclusion first. This keeps “I do not know” distinct from a silent omission and from an unsupported guess.

The evaluator persists immutable-style JSON: writing the identical report is idempotent, while replacing it with different content at the same path is refused.

## Synthetic adversarial suite

The committed synthetic suite proves that the deterministic boundary detects or escalates:

- changed labels and duplicated evidence use;
- invented evidence IDs, representing hallucinated page/row locators;
- mismatched unit, reporting period, and reporting basis in a proposal;
- incorrect aggregation components or signs, including resulting value and reconciliation failures; and
- instruction-like text in a reported label. The golden case expects explicit abstention, so text from a filing is treated as evidence content rather than a command.

These cases demonstrate the local contract only. They are not a real-company accuracy benchmark and do not replace future provider-side prompt-isolation, privacy, or security tests.

### V3 and v4 prompt-policy regression cases

`fictional_reported_totals_onboarding.json` adds direct reported tax/finance/PBT/PAT amounts,
equivalent labels, a deferred-tax credit, a duplicate tax note, and an interest subtotal that already
includes lease interest. `fictional_uncertain_finance_onboarding.json` expects finance-cost
abstentions when only interest, FX losses, and derivative losses are available without scope evidence.
The existing `fictional_tax_onboarding.json` still tests components-only aggregation and the negative
deferred-tax sign. All are fictional and remain outside the real-company corpus registry.

Frozen fake responses traverse the v4 OpenAI adapter, deterministic validation, and evaluator.
Negative variants show that matching PAT does not excuse reused evidence, nested components do
not justify double counting, and uncertain finance components cannot pass by being confidently
mapped or summed. These tests verify contracts and scoring, **not** live prompt effectiveness.
Additional tests verify catalog integrity, legacy input parsing, source-text isolation, derived-target
rejection in both decision types, exact prompt/input hashes, explicit caller-selected metric scope,
locator-bound context checksum/identity controls, and explicit SDK retry disabling.

The v4 scope is supplied in the onboarding request rather than copied from expected fixture
decisions. Tests reject a mapping or aggregation target outside that scope. Context snippets are
only a bounded, untrusted source aid; the current evaluator does not treat their text as a
CA-reviewed route or allow it to bypass evidence, arithmetic, reconciliation, or human approval.

Exact-decision precision/recall and numerical comparisons remain separate diagnostics. In
particular, a model selecting a reported tax total can match the number but fail a fixture that
requires its components. The v3 change does not automatically accept alternative routes, change
any real fixture, or lower thresholds. Reviewed alternative evidence routes, precision-aware
rounding, and richer context scenarios remain follow-up work.

## Local evaluation

Use a frozen proposal so the run has no network or API dependency. `evaluate-onboarding` remains useful for synthetic fixtures and local contract development:

```bash
uv run python -m indian_company_analysis evaluate-onboarding \
  --fixture /path/to/golden-fixture.json \
  --proposal /path/to/proposal.json \
  --evaluated-at 2026-09-27T15:00:00+00:00 \
  --output /path/to/evaluation-report.json
```

The command exits with status `0` when the case passes and `1` when it fails. It records the current UTC time unless `--evaluated-at` supplies an explicit timezone-aware audit timestamp. The default output is under `data/interim/evaluations/<case-id>/` and remains local.

For a CA-approved real-company case, do not supply a fixture path directly. Retrieve the fixture only through its CA-approved corpus entry:

```bash
uv run python -m indian_company_analysis evaluate-approved-corpus \
  --catalog-root /path/to/local-evaluation-corpus \
  --entry-id company-fy2026-income-statement \
  --corpus-version v1 \
  --proposal /path/to/local-provider-proposal.json \
  --evaluated-at 2026-09-30T15:00:00+00:00
```

This command refuses a candidate or rejected entry before reading the proposal. It retrieves the approved fixture by entry ID and corpus version, applies the same deterministic evaluation, and writes the default report under `data/interim/evaluations/approved-corpus/`. It still does not call a live provider: a future provider adapter must write its strict proposal artifact first.

For internal workflow testing while a qualified CA review is unavailable, the registry also supports a separately marked provisional route:

```bash
uv run python -m indian_company_analysis evaluate-provisional-corpus \
  --catalog-root /path/to/local-evaluation-corpus \
  --entry-id company-fy2026-income-statement \
  --corpus-version provisional-v1 \
  --proposal /path/to/local-provider-proposal.json
```

It accepts only an entry with `review_status: provisional_internal_review`, writes under `data/interim/evaluations/provisional-internal-corpus/`, and records `evaluation_qualification: provisional_internal_review` in the report. This is not an approved corpus evaluation and must not be used to claim model readiness or replace a CA-reviewed fixture.

## Current limitations and next gate

This slice supplies the evaluation machinery plus synthetic tax, ambiguity/abstention, and adversarial cases. The local [controlled evaluation corpus registry](EVALUATION_CORPUS_REGISTRY.md) provides both a provisional internal-testing route and the CA-approval gate for permitted real-company cases, but no real corpus case is committed or CA-approved yet. Provisional internal results do not establish real-world model accuracy, security, privacy, or acceptable cost/latency. Before connecting a live LLM:

1. assemble a representative, permitted multi-company and multi-layout corpus in the local registry;
2. have a qualified accounting reviewer approve each fixture's golden dispositions and values;
3. add ambiguous, missing, adversarial, and expected-abstention cases;
4. agree minimum quality, privacy, prompt-injection, cost, and latency gates; and
5. compare model/prompt/schema versions without weakening deterministic validation or human approval.
