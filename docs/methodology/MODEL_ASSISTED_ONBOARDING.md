# Model-assisted document onboarding

## Purpose and current boundary

Phase 2D begins the provider-neutral boundary through which a future LLM can reduce the manual work of interpreting a new company or filing layout. The implemented foundation does not call an LLM, add an API dependency, or approve a financial fact automatically. It defines the strict request, proposal, validation, and human-approval records that any later provider adapter must use.

The first implementation starts after a deterministic PDF profile has produced a review-ready extraction. `build_onboarding_request` converts those rows into checksummed evidence records with stable evidence IDs and page/table/row/column locators. Automatic discovery of statement pages and extraction coordinates remains future work.

## Controlled flow

```text
review-ready PDF extraction
        |
        v
checksummed onboarding request + source row locators
        |
        v
provider-neutral proposal interface
        |
        v
mapping + aggregation + exclusion candidates
        |
        v
deterministic proposal validation
        |
        v
explicit human approval + versioned configuration
```

`StaticProposalProvider` supplies a frozen proposal for tests and local evaluation. A future live adapter must implement the same `OnboardingProposalProvider` protocol and return the same strict `DocumentOnboardingProposal` schema.

## Proposal provenance

Every proposal records:

- the request, proposal, and source-document identities;
- the source-document SHA-256 checksum;
- provider, model ID, and model version;
- prompt and schema versions;
- timezone-aware generation time;
- optional token counts, latency, estimated cost, and cost currency;
- candidate confidence and rationale; and
- exact evidence-row identifiers used by each proposal.

The provider returns semantic suggestions only. The request's extracted values and locators remain the evidence.

## Deterministic validation

Before human review, the validator rejects proposals that:

- do not match the request ID, document ID, checksum, source organization, or document type;
- reference an evidence row that was not supplied;
- change a reported label;
- consume one evidence row more than once;
- silently omit a row instead of mapping, aggregating, or explicitly excluding it;
- produce the same canonical metric through multiple candidates; or
- map a reported row directly to a derived analytical metric.

Model confidence never bypasses these checks and never counts as approval.

## Human approval and deterministic aggregation

`approve_onboarding_proposal` reruns deterministic validation before creating a reviewed configuration. The configuration preserves the model run, reviewer, review timestamp, approval-policy version, direct mapping set, exclusions, and approved aggregation semantics.

Direct one-to-one mappings can feed the existing controlled normalization pipeline. Approved many-to-one rules can now be executed by `execute_approved_aggregations` when every component shares the approved request's company, source document, unit, period, and reporting basis.

The first aggregation contract is deliberately narrow: two or more approved component rows are combined with coefficients restricted to `1` or `-1`. Each result preserves the raw and parsed component values, coefficient, contribution, page/table/row/column locator, rule and configuration versions, source checksum/reference, model proposal, and human-review metadata. The output observation is classified as `calculated`, not `reported`, because deterministic code constructed it from reported components.

Execution fails explicitly when a component is missing, its approved evidence snapshot has changed, its number is invalid or ambiguous, a row is reused, a canonical target is duplicated, or the request's document/company/source/unit/period/basis differs from the approved configuration. The resulting observation can enter the existing statement reconciliation checks; the synthetic tax example verifies that profit before tax less aggregated tax expense equals profit after tax.

## Combined verified normalization

`OnboardingNormalizationWorkflow` now combines approved direct mappings, deterministic aggregations, and explicit exclusions into one persistable `OnboardingNormalizationBatch`. Before producing facts it:

- re-verifies the immutable source PDF and derived CSV bytes through their extraction link;
- matches the source document, company, source reference, checksum, extraction ID, and profile version;
- confirms every controlled-CSV field and row still matches the onboarding evidence;
- confirms every evidence row is used exactly once as a direct mapping, aggregation component, or exclusion; and
- retains failed extraction benchmarks and missing extraction review as analysis blockers.

Direct facts remain `reported` and use the mapping method `model_assisted_reviewed`; aggregate facts remain `calculated`. The batch embeds the reviewed configuration and extraction link, preserves issues and blockers, and refuses to overwrite a different artifact at the same output path.

The local command accepts versioned JSON artifacts produced by the earlier intake, extraction, proposal, and approval steps:

```bash
uv run python -m indian_company_analysis normalize-onboarding \
  --source-manifest /path/to/source-manifest.json \
  --extraction-manifest /path/to/extraction-manifest.json \
  --extraction-link /path/to/extraction-link.json \
  --request /path/to/onboarding-request.json \
  --configuration /path/to/approved-configuration.json \
  --output /path/to/normalized-onboarding.json
```

## Golden-case evaluation

`OnboardingProposalEvaluator` now runs any provider implementation against a versioned golden fixture. It scores direct mappings, aggregations, and exclusions; detects missing, duplicated, and hallucinated evidence use; recomputes canonical values deterministically; and runs declared accounting reconciliations. Strict thresholds determine the case result, while the persisted audit report retains the full proposal and validation outcome. The committed fixture is synthetic and proves the mechanism, not general model quality. See [onboarding proposal evaluation](ONBOARDING_EVALUATION.md).

## Deferred work

- additional aggregation operators only when a reviewed accounting use case requires them;
- proposal/approval CLI, review queue, rejection records, and configuration catalog;
- real provider selection and adapter implementation;
- structured-output retries and provider error handling;
- a representative permitted, CA-reviewed evaluation corpus and expected-abstention cases;
- live provider comparison using captured accuracy, token, cost, and latency metadata;
- prompt-injection isolation and evidence-minimization policy;
- automatic statement-page/profile discovery; and
- controlled policy for any future low-risk automatic approval.
