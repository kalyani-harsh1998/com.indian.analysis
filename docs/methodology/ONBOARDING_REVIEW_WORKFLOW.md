# Onboarding review workflow

## Purpose

Phase 2D requires a human decision before a model proposal can affect normalized facts. The local review workflow records both approvals and rejections as immutable-style JSON artifacts. It never modifies the original proposal.

## Decisions

An `OnboardingReviewDecision` retains the request and proposal identities, reviewer, timezone-aware review time, review-policy version, reviewer rationale, and deterministic validation result.

- An **approved** decision embeds the approved configuration and can be registered in the configuration catalog.
- A **rejected** decision contains one or more reviewer reasons and never creates a configuration.
- A proposal with an abstention cannot be approved. The reviewer must first resolve every abstention as a mapping, aggregation, or exclusion in a new proposal artifact.

Both decision types are append-only. Rewriting the same bytes is idempotent; a different record at the same decision ID is refused.

## Commands

Approve a fully validated proposal:

```bash
uv run python -m indian_company_analysis approve-onboarding \
  --request /path/to/onboarding-request.json \
  --proposal /path/to/proposal.json \
  --decision-id company-fy2026-approval-v1 \
  --configuration-version company-fy2026-mapping-v1 \
  --aggregation-rule-version aggregation-v1 \
  --reviewed-by reviewer@example.com \
  --reviewed-at 2026-09-29T10:00:00+00:00 \
  --approval-policy-version human-review-v1 \
  --review-rationale "Reviewed labels, values, source locators, and aggregation."
```

Reject a proposal without changing it:

```bash
uv run python -m indian_company_analysis reject-onboarding \
  --request /path/to/onboarding-request.json \
  --proposal /path/to/proposal.json \
  --decision-id company-fy2026-rejection-v1 \
  --reviewed-by reviewer@example.com \
  --reviewed-at 2026-09-29T10:00:00+00:00 \
  --approval-policy-version human-review-v1 \
  --review-rationale "The proposal needs correction before use." \
  --rejection-reason "Confirm the revenue definition against the note." \
  --rejection-reason "Resolve the unclassified adjustment."
```

Artifacts remain local under `data/interim/onboarding-reviews/`. Approved configurations are registered under `data/interim/onboarding-configurations/` by company, document type, extraction profile, and configuration version.

## Source identity and reuse

The catalog can retrieve a configuration only when its request ID, document ID, extraction ID/profile, company, source reference, SHA-256 checksum, source organization, document type, unit, reporting period, and reporting basis all match the current request. This POC therefore supports auditable replay for the same verified source context; it does not yet automatically apply one configuration to a later filing.

## Deferred work

This is a local CLI workflow, not a multi-user review system. Role-based access, assignment queues, review amendments, configuration migration across filings, and electronic-signature or compliance requirements remain future work.
