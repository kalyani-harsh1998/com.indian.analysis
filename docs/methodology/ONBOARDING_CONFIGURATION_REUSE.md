# Cross-filing configuration reuse assessment

## Purpose

An approved onboarding configuration is tied to the exact evidence of one filing. This Phase 2D slice reduces repeat review work on a later filing without weakening that rule: it compares the prior configuration with a new checksummed onboarding request and produces a review-only assessment.

The assessment is not a configuration, approval, mapping, or normalization artifact. It cannot be applied automatically.

## What is compared

`OnboardingReuseAssessor` compares each approved direct mapping, aggregation rule, and exclusion with the target filing's extracted evidence using exact reported labels. It reports one of four outcomes for each prior decision:

- `reusable_candidate`: every source label has exactly one target row;
- `missing_evidence`: one or more prior labels are absent;
- `ambiguous_evidence`: more than one target row could match, or two prior decisions would consume the same target row; or
- `incompatible_context`: company, source organization, document type, unit, reporting basis, or extraction profile differs.

It also records new target rows that have no label in the prior approved configuration, and records context differences such as the new document ID, checksum, source reference, extraction ID, and period.

Different document IDs, periods, and checksums are expected for a later filing and do not by themselves make a candidate unsafe. They remain visible in the report. A change to the company, statement context, unit, basis, or extraction profile blocks every reuse candidate.

## Human gate

Every assessment has `requires_human_approval: true`, even when all prior decisions are reuse candidates. A reviewer must create and approve a new configuration for the new filing; the existing source-bound configuration is never altered or applied to the new request.

This POC deliberately does not generate a proposal from the assessment. A future migration policy may use the report to prefill reviewer work, but must preserve the new request's source evidence, configuration version, validation, and approval record.

## Local command

```bash
uv run python -m indian_company_analysis assess-onboarding-reuse \
  --configuration /path/to/prior-approved-configuration.json \
  --request /path/to/new-onboarding-request.json \
  --assessment-id company-fy2027-reuse-v1 \
  --assessed-at 2026-09-29T14:00:00+00:00
```

The default report location is `data/interim/onboarding-reuse-assessments/`. Reports are immutable-style: identical writes are idempotent and conflicting writes are refused.

## Limits

The comparison is intentionally exact-label and deterministic. It does not use fuzzy matching, an LLM, OCR, changed-label semantic inference, automatic profile selection, or automatic approval. A label change such as “Revenue from operations” to “Revenue from operations and services” is surfaced for review rather than assumed equivalent.
