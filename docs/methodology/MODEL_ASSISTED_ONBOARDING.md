# Model-assisted document onboarding

## Purpose and current boundary

Phase 2D begins the provider-neutral boundary through which an LLM can reduce the manual work of interpreting a new company or filing layout. It defines strict request, proposal, validation, and human-approval records. The optional OpenAI adapter is the first concrete implementation: it remains non-authoritative, has no raw-PDF access, and has separate corpus-gated provisional technical and CA-approved quality-evaluation routes.

The first implementation starts after a deterministic PDF profile has produced a review-ready extraction. `build_onboarding_request` converts those rows into checksummed evidence records with stable evidence IDs and page/table/row/column locators. Automatic discovery of statement pages and extraction coordinates remains future work.

## Controlled flow

```text
review-ready PDF extraction
        |
        v
checksummed onboarding request + source row locators
        |
        v
minimal prompt-isolated provider input
        |
        v
provider-neutral proposal interface
        |
        v
mapping + aggregation + exclusion + abstention candidates
        |
        v
deterministic proposal validation
        |
        v
explicit human approval + versioned configuration
```

`StaticProposalProvider` supplies a frozen proposal for tests and local evaluation. The optional OpenAI adapter implements the same `OnboardingProposalProvider` protocol and returns the same strict `DocumentOnboardingProposal` schema. Any later provider must meet that contract as well.

## Optional OpenAI adapter

`OpenAIOnboardingProposalProvider` is an opt-in dependency (`uv sync --extra openai`), not part
of the normal POC install. It reads `OPENAI_API_KEY` from the local environment only when the
caller invokes it; no key is accepted through a command argument, stored in an artifact, or
committed to the repository.

For each request it makes one call to the Responses API with `store=False`, a fixed developer
message, the packet's data-only user payload, and a strict JSON schema. The model returns only
semantic candidate content. Python binds request identity, model provenance, token counts when
supplied, response-derived model version, a local timestamp, and a response-derived proposal ID
afterwards. It does not estimate cost or relax an error into an approval. The SDK client explicitly
sets `max_retries=0`; the earlier implementation relied on an SDK default despite documenting no
retry. New model runs also record SHA-256 digests of the exact user payload and developer message.

The adapter provides separate corpus-gated live commands. The provisional command is for a single
technical E2E test and always emits a non-CA report:

```bash
uv run python -m indian_company_analysis evaluate-openai-provisional-corpus \
  --entry-id company-fy2026-income-statement \
  --corpus-version provisional-internal-v1 \
  --model gpt-6-astra
```

It accepts only `provisional_internal_review`, not a candidate, rejected, approved, or synthetic
entry. Its report cannot approve a mapping, authorize broader live use, or satisfy a quality gate.

The CA-approved command is the quality-evaluation route:

```bash
uv run python -m indian_company_analysis evaluate-openai-approved-corpus \
  --entry-id permitted-ca-reviewed-case \
  --corpus-version v1 \
  --model gpt-6-astra
```

It first retrieves an `approved_for_evaluation` entry from the local corpus registry; candidate,
provisional, rejected, and synthetic entries are rejected before this CA-quality route is invoked.
Every persisted report remains an evaluation artifact, not an approved mapping or normalization
input.

## Prompt-isolated model input

`PromptIsolatedOnboardingInputBuilder` converts an onboarding request into the only packet that a future mapping provider should receive. It includes the request identity, company/period/unit/basis context, source checksum, and bounded evidence rows with their locators, labels, and raw values. It deliberately excludes local filesystem paths, raw PDF bytes, original filenames, and arbitrary document text.

The rows are named `untrusted_evidence_rows`: a label or value may contain instruction-like text, but it is source data rather than an instruction. The future adapter must send the static `ONBOARDING_MODEL_DEVELOPER_INSTRUCTIONS` in a trusted developer/system channel and `provider_user_payload()` as a separate data-only user message. It must never interpolate a reported label, raw value, or source snippet into trusted instructions.

### Current contract: v3

`onboarding-model-input-v3` replaces v2's aggregation-first rule and blanket inference that
statement FX/derivative losses belong to finance cost. V2 matched the provisional APSEZ fixture's
finance-cost amount, but also reconstructed reported PBT/PAT and reused evidence. Matching that
fixture does not independently establish its finance-cost definition. No configuration was approved.

V3 includes `onboarding-metric-catalog-v1`: a checksummed snapshot of the non-derived definitions
from `domain/metrics.py`, with company-independent scope notes from `onboarding/metric_catalog.py`.
It describes eligible targets, **not** a checklist requiring every metric in every report. There
are no company names, label-alias maps, or fixture answers in this catalog. Its scope notes are
engineering review guidance, not CA-certified accounting policy. Competing PAT or gross/net scopes
remain explicit uncertainties rather than silently changing the engine's definitions.

The decision order is:

1. Interpret each row relative to the target definition and supplied statement context. Equivalent
   labels are allowed; a statement subtotal can be the complete amount for its own target metric.
2. Prefer a directly reported, scope-compatible amount. Exclude redundant components or supporting
   disclosures from primary mapping, with rationale; retain all original evidence.
3. Where no compatible full amount exists, aggregate only complete, non-overlapping components of
   the same metric. Python performs the arithmetic. Do not reconstruct analytical PBT/PAT/EBIT/EBITDA
   formulas in onboarding or turn an incomplete component into a total.
4. Exclude clearly non-target rows. Abstain on relevant unresolved rows, identifying the affected
   metric and missing evidence/definition, while retaining independently supported candidates.
5. Account for every row exactly once and target each metric at most once. A later calculation or
   reconciliation may reuse facts; that is separate from primary onboarding dispositions.

V3 preserves credits and loss signs, distinguishes incompatible scopes, and requires positive
evidence before classifying FX/derivative losses as finance costs. It does not invent absent notes,
correct OCR, convert units, or force figures to reconcile. Existing abstentions still block approval
of the entire proposal; partial approval is **not** introduced in this slice.

The OpenAI wire schema is now `openai-onboarding-proposal-v2`. Its shared metric enum is restricted
to the same eligible catalog for both mappings and aggregations. Python independently rejects a
derived target even if a provider ignores that schema. The deterministic validator and thresholds
are otherwise unchanged. Structured output constrains format, not accounting truth; see
[OpenAI's structured-output guidance](https://developers.openai.com/api/docs/guides/structured-outputs).

Legacy v1/v2 packets remain readable without inventing a catalog, but new calls build v3 packets;
legacy parsing does not replay old prompts. Use a new input ID/output path when preparing v3.
Version changes to prompt instructions, catalog scope, and response schema explicitly. The new
run's input/instruction hashes identify the exact serialized content, including the catalog snapshot.

The packet still contains flat rows and request-level context, not source note excerpts, row-level
unit metadata, or a requested metric subset. Missing accounting context therefore still requires
review. Targeted, locator-bound note retrieval is future work; sending the whole PDF is not enabled.

One authorized APSEZ v3 technical call has now completed. Structural validation and the PBT/tax/PAT
reconciliation passed, with no duplicate evidence, but full acceptance failed on finance-cost
deferral and differences from the fixture's tax/expense dispositions. No mapping was approved.
See [the recorded comparison and next steps](OPENAI_ONBOARDING_TECHNICAL_RESULTS.md).

The policy versions and enforces evidence-row, label-length, and value-length limits; unsupported control characters fail preparation rather than being silently truncated. A SHA-256 checksum binds the exact evidence rows included in the packet. The local command persists the packet without calling a provider:

```bash
uv run python -m indian_company_analysis prepare-onboarding-model-input \
  --request /path/to/onboarding-request.json \
  --input-id company-fy2026-profit-loss-input-v1 \
  --policy-version prompt-isolation-v1
```

This is an input-boundary control, not a complete prompt-injection solution. Role separation and
structured-output enforcement are implemented; broader provider-error handling and any bounded
retry policy remain future work.

## Proposal provenance

Every proposal records:

- the request, proposal, and source-document identities;
- the source-document SHA-256 checksum;
- provider, model ID, and model version;
- prompt and schema versions;
- optional exact input-payload and developer-instruction checksums (populated by the v3 adapter);
- timezone-aware generation time;
- optional token counts, latency, estimated cost, and cost currency;
- candidate confidence and rationale; and
- exact evidence-row identifiers used by each proposal.

The provider returns semantic suggestions only. The request's extracted values and locators remain the evidence.

## Deterministic validation

Before human review, the validator rejects proposals that:

- do not match the request ID, document ID, checksum, source organization, or document type;
- do not match the request's unit, reporting period, or reporting basis;
- reference an evidence row that was not supplied;
- change a reported label;
- consume one evidence row more than once;
- silently omit a row instead of mapping, aggregating, or explicitly excluding it;
- produce the same canonical metric through multiple candidates; or
- map a reported row directly to a derived analytical metric.

Model confidence never bypasses these checks and never counts as approval.

## Explicit abstention

When a row cannot be mapped safely, the provider must emit an `AbstentionCandidate` with its exact evidence ID and rationale. An abstention accounts for the row during validation and permits an evaluation case to reward safe deferral, but it blocks promotion to an approved configuration. A reviewer must replace it with a direct mapping, aggregation, or exclusion; it can never become a normalized fact by itself.

## Human approval and deterministic aggregation

`approve_onboarding_proposal` reruns deterministic validation before creating a reviewed configuration. The configuration preserves the model run, reviewer, review timestamp, approval-policy version, direct mapping set, exclusions, and approved aggregation semantics.

The local `approve-onboarding` and `reject-onboarding` commands wrap this decision in a durable review record. Approval registers a configuration only after validation and abstention checks pass; rejection records reviewer reasons without altering the proposal or creating a configuration. See [onboarding review workflow](ONBOARDING_REVIEW_WORKFLOW.md).

For a later filing, `assess-onboarding-reuse` compares a prior configuration with the new evidence and produces reviewer-only reuse candidates. It does not alter, copy, or apply the prior configuration. See [cross-filing configuration reuse assessment](ONBOARDING_CONFIGURATION_REUSE.md).

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

`OnboardingProposalEvaluator` now runs any provider implementation against a versioned golden fixture. It scores direct mappings, aggregations, exclusions, and explicit abstentions; detects missing, duplicated, and hallucinated evidence use; recomputes canonical values deterministically; and runs declared accounting reconciliations. Strict thresholds determine the case result, while the persisted audit report retains the full proposal and validation outcome. The committed fixtures are synthetic and prove the mechanism, not general model quality. See [onboarding proposal evaluation](ONBOARDING_EVALUATION.md).

The synthetic adversarial suite covers changed labels, duplicate evidence, invented locators,
statement-context mismatch, incorrect aggregation signs, and instruction-like filing text. V3 adds
reported totals alongside components, duplicate disclosure, nested subtotals, equivalent labels,
and unresolved finance-cost components. Frozen fake responses exercise the actual adapter and
evaluator offline; passing them does not establish that the live LLM follows the new prompt.
A provisional internal case in the [controlled evaluation corpus registry](EVALUATION_CORPUS_REGISTRY.md)
may exercise the technical route but cannot satisfy the CA-approved quality gate.

## Deferred work

- explicitly reviewed alternative evidence routes in evaluation; exact-decision scoring still
  rejects an otherwise equivalent tax total if the frozen fixture specifies components;
- targeted, locator-bound statement/note context and explicit requested-metric scope;
- precision-aware rounding policies and finer-grained review outcomes without bypassing approval;
- additional explicitly authorized, bounded v3 real-case comparisons; the single APSEZ technical
  result does not establish CA-approved model quality;
- additional aggregation operators only when a reviewed accounting use case requires them;
- multi-user review queue, review amendments, and an approved configuration-migration policy across filings;
- provider comparison and model-selection policy;
- bounded structured-output retry policy and provider error handling based on observed failures;
- creation and CA approval of a representative permitted evaluation corpus, including expected-abstention cases, under the implemented local registry;
- live provider comparison using captured accuracy, token, cost, and latency metadata;
- automatic statement-page/profile discovery; and
- controlled policy for any future low-risk automatic approval.
