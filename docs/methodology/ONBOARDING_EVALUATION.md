# Onboarding proposal evaluation

## Purpose

Phase 2D evaluates a model-assisted onboarding proposal before any live provider is allowed into the normalization workflow. The evaluator compares a provider-neutral `DocumentOnboardingProposal` with a versioned, human-reviewed golden fixture. It does not approve mappings, create facts, or make model output authoritative.

The initial committed fixture is explicitly synthetic. It proves the evaluation contract and accounting checks; it is not evidence of accuracy on real-company reports.

## Golden fixture

An `OnboardingEvaluationFixture` freezes:

- the exact checksummed onboarding request and source-row locators;
- expected direct mappings, signed-sum aggregations, and explicit exclusions;
- expected canonical metric values;
- linear accounting reconciliation expectations and tolerances; and
- pass/fail thresholds for each metric.

Golden decisions must account for every evidence row exactly once. Canonical targets, expected values, and reconciliation identifiers must be unique. A future real-report corpus must be built only from permitted documents and independently reviewed mappings.

## Measurements and gates

`OnboardingProposalEvaluator` calls the same provider protocol used by future live adapters, reruns deterministic proposal validation, and records:

- precision and recall for mappings, aggregations, and exclusions;
- evidence coverage;
- hallucinated, duplicated, and unaccounted evidence counts;
- exact decision-set match;
- deterministic canonical-value comparisons; and
- accounting reconciliation results.

A case passes only when all configured thresholds and required checks pass. The report retains the complete proposal, validation issues, provider/model/version, prompt and schema versions, generation time, and optional input/output token, latency, estimated-cost, and currency metadata. Missing usage metadata stays explicit rather than being estimated silently.

The evaluator persists immutable-style JSON: writing the identical report is idempotent, while replacing it with different content at the same path is refused.

## Local evaluation

Use a frozen proposal so the run has no network or API dependency:

```bash
uv run python -m indian_company_analysis evaluate-onboarding \
  --fixture /path/to/golden-fixture.json \
  --proposal /path/to/proposal.json \
  --evaluated-at 2026-09-27T15:00:00+00:00 \
  --output /path/to/evaluation-report.json
```

The command exits with status `0` when the case passes and `1` when it fails. It records the current UTC time unless `--evaluated-at` supplies an explicit timezone-aware audit timestamp. The default output is under `data/interim/evaluations/<case-id>/` and remains local.

## Current limitations and next gate

This slice supplies the evaluation machinery and one synthetic tax-onboarding case. It does not yet establish real-world model accuracy, abstention quality, security, privacy, or acceptable cost/latency. Before connecting a live LLM:

1. assemble a representative, permitted multi-company and multi-layout corpus;
2. have a qualified accounting reviewer approve the golden dispositions and values;
3. add ambiguous, missing, adversarial, and expected-abstention cases;
4. agree minimum quality, privacy, prompt-injection, cost, and latency gates; and
5. compare model/prompt/schema versions without weakening deterministic validation or human approval.
