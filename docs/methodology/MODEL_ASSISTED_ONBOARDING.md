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

## Human approval and current aggregation limit

`approve_onboarding_proposal` reruns deterministic validation before creating a reviewed configuration. The configuration preserves the model run, reviewer, review timestamp, approval-policy version, direct mapping set, exclusions, and approved aggregation semantics.

Direct one-to-one mappings can feed the existing controlled normalization pipeline. Approved many-to-one aggregation rules are deliberately retained with the blocker `deterministic aggregation execution is not implemented`. This prevents a reviewed semantic suggestion from being mistaken for an executable or analysis-ready calculation.

## Deferred work

- deterministic aggregation execution with component-level calculation lineage;
- accounting reconciliation of aggregated results;
- CLI persistence, review queue, rejection records, and configuration catalog;
- real provider selection and adapter implementation;
- structured-output retries and provider error handling;
- proposal accuracy, abstention, cost, and latency evaluation;
- prompt-injection isolation and evidence-minimization policy;
- automatic statement-page/profile discovery; and
- controlled policy for any future low-risk automatic approval.
