# Architecture decision log

## ADR-001 — Phase 1 financial-analysis accounting contract

**Status:** Accepted for the synthetic POC  
**Date:** 18 September 2026

### Context

The Phase 0 workflow returned successful ratios or an unexplained absence. Phase 1 needs auditable non-financial calculations that retain revisions, distinguish unavailable results, and prevent accidental mixing of accounting contexts.

### Decision

- Use canonical `MetricId` values and a versioned metric-definition registry.
- Keep reported observations immutable and exclude only records explicitly marked `superseded` from current calculations.
- Store restatements and analytical adjustments as different concepts.
- Return a `CalculationResult` for unavailable as well as successful metrics.
- Reconcile EBITDA/EBIT, PAT, balance-sheet totals, and cash roll-forward before downstream interpretation.
- Use consolidated annual synthetic statements for the golden Phase 1 dataset.
- Use `Decimal`, six decimal places for ratios, and two for money/days.
- Define Phase 1 ROCE as EBIT divided by average equity plus interest-bearing debt less cash.
- Keep the engine dependency-free beyond Pydantic and the standard library.

### Consequences

- Outputs are more verbose but explain missing, invalid, and incomparable calculations.
- Superseded values remain available for audit and future point-in-time analysis.
- The ROCE and working-capital conventions are explicit rather than falsely universal.
- Real filing ingestion, metric-label mapping, normalized earnings, and sector overrides remain future work.
- Independent CA validation is required before real-company conclusions or public release.

## ADR-002 — Phase 2A local immutable document intake

**Status:** Accepted for the POC
**Date:** 26 September 2026

### Context

The next vertical slice needs real-document lineage without creating an unreviewed downloader, scraper, or parsing pipeline. Raw evidence must remain available for later verification and must not be silently replaced.

### Decision

- Accept only a file that a user has already supplied locally through a permitted route.
- Copy, never move or edit, that file into `data/raw/` using its SHA-256 checksum as the storage key.
- Store a strict JSON manifest separately in ignored local storage, carrying source metadata, licence classification, content details, and the checksum.
- Reuse byte-identical content without overwriting it; reject a different manifest for an existing document ID.
- Make the stored raw copy read-only and provide independent byte-size and checksum verification.

### Consequences

- The POC gains auditable document identity and version preservation without external data access.
- A checksum validates stored-byte identity, not source authority, accounting accuracy, completeness, or legal rights.
- Users still must assess terms and manually acquire permitted documents.
- Parsing, table/page lineage, normalized facts, revisions, and conflict resolution are later Phase 2 slices.

## ADR-003 — Controlled exact-label normalization before document extraction

**Status:** Accepted for the POC
**Date:** 26 September 2026

### Context

Automatic PDF or OCR extraction would combine several uncertain problems: document layout, table detection, number parsing, label interpretation, and accounting mapping. The POC first needs a testable normalized-fact contract with complete field lineage and explicit failure behavior.

### Decision

- Accept only a verified row-oriented `text/csv` document in this slice.
- Require company, page/table/row/column, raw label/value, unit, period, and reporting basis on every row.
- Apply a versioned mapping set scoped to the manifest's exact source organization and document type.
- Match labels only after deterministic case and whitespace normalization; do not use fuzzy or model-generated mapping.
- Permit only an explicit `1` or `-1` sign transformation and retain the unmodified raw value.
- Produce engine-compatible observations while keeping field-level lineage beside each observation.
- Treat invalid, unmapped, company-mismatched, and duplicate rows as structured issues that make the batch unready for analysis.

### Consequences

- Canonical fact semantics can be tested independently of PDF and OCR tooling.
- Mapping changes are reviewable and reproducible through mapping versions and rationales.
- A human still prepares and reviews the controlled CSV and mapping configuration.
- The CSV checksum identifies the normalized input; cryptographic PDF-to-extraction linkage remains future work.
- Real-company mappings require CA review and benchmark comparison before analytical use.

## ADR-004 — Separate source PDFs from benchmarked derived extractions

**Status:** Accepted for the POC
**Date:** 26 September 2026

### Context

A derived table is not the same evidence object as its source filing. Treating an extracted CSV as the source would hide parser risk and make it difficult to prove which PDF bytes, tool version, pages, and transformation produced a normalized fact.

### Decision

- Keep the original PDF and derived controlled CSV as separate immutable raw artifacts with separate manifests and SHA-256 checksums.
- Bind them through a strict `DocumentExtractionLink` carrying tool/version, extraction-profile version, source pages, extraction time, benchmark, and review state.
- Begin with text-based ruled-table and explicitly configured aligned-column profiles implemented with `pdfplumber`.
- Benchmark exact label/value pairs against independently prepared golden rows.
- Preserve unreviewed, rejected, and failed results, but block them from analysis readiness.
- Require an accepted human review in addition to a passing benchmark.
- Cite the original PDF source reference in normalized observations while retaining the derived CSV identity as adjacent extraction lineage.

### Consequences

- A normalized fact can be traced to both original evidence bytes and derived extraction bytes.
- Parser upgrades or extraction-profile changes produce distinguishable, reproducible lineage.
- The committed synthetic fixture proves the contract but says nothing about real-report accuracy.
- Real annual reports require permitted benchmark corpora and independent accounting review.
- General layouts, OCR, XBRL, multiple tables, and automated review remain future work.

## ADR-005 — Hybrid interpretation with deterministic numerical authority

**Status:** Accepted as the target architecture; runtime-dependency limit superseded in part by ADR-018
**Date:** 27 September 2026

### Context

Listed-company filings vary by format, layout, terminology, period presentation, and accounting detail. A single rigid parser will not generalize, while allowing a language model to directly create trusted numbers would introduce nondeterminism and unsupported values.

### Decision

- Route documents among replaceable deterministic extraction profiles rather than require one universal layout.
- Treat extracted labels, values, units, periods, and coordinates as candidates until validation and review complete.
- Use a future provider-neutral LLM adapter during first-time document onboarding to reduce manual configuration work.
- Permit the adapter to suggest document classification, relevant pages, extraction profile/coordinates, table semantics, periods/units/basis, canonical metric mappings, and component aggregation rules.
- Never allow an LLM suggestion to become numerical evidence without a source locator, deterministic parsing, validation, and the required review gate.
- Keep number parsing, unit transformations, duplicate handling, period/basis checks, accounting reconciliation, and acceptance status in deterministic Python.
- Preserve model/provider, model version, prompt/schema version, source evidence/locators, suggestion, rationale, confidence, validation results, and review decision when LLM assistance is introduced.
- Persist accepted suggestions as versioned reusable configurations so compatible later filings can run deterministically; do not require repeated model interpretation when an approved profile applies.
- Initially add no LLM or OpenAI runtime dependency during the current POC. ADR-018 later permits a narrowly scoped optional OpenAI evaluation adapter without changing the numerical or review boundaries above.

### Consequences

- Input handling can evolve across company layouts while canonical output remains strict.
- First-time onboarding effort can fall substantially while ambiguous cases remain visible to a reviewer.
- High-confidence structured filings may eventually pass automatically; ambiguous PDF/OCR cases remain reviewable candidates.
- Model changes cannot silently change accepted historical facts.
- Profile routing, representative live-model evaluation, privacy, cost, and provider selection remain future tested slices.

## ADR-006 — Treat model onboarding output as a reviewed proposal artifact

**Status:** Accepted for the POC foundation
**Date:** 27 September 2026

### Context

The hybrid target needs a concrete boundary before any live model is connected. Model output must not bypass evidence identity, silently omit inconvenient rows, reuse a source value in multiple facts, or become an executable aggregation merely because it is expressed confidently.

### Decision

- Build a checksummed onboarding request only from a review-ready deterministic extraction.
- Give every source row a stable evidence ID plus its page/table/row/column locator and raw label/value.
- Require a provider-neutral proposal to classify every row as a direct mapping, aggregation component, or explicit exclusion.
- Reject unknown evidence, changed labels, duplicate row use, duplicate canonical targets, unaccounted rows, source-identity mismatches, and direct mappings to derived metrics.
- Preserve provider/model, prompt/schema, generation-time, candidate rationale/confidence, source checksum, reviewer, review time, and approval-policy versions.
- Rerun deterministic validation inside the human-approval operation rather than trust a supplied validation result.
- Permit reviewed direct mappings to produce the existing mapping set, but retain approved aggregation semantics behind an explicit blocker until deterministic aggregation execution exists.
- Use a static provider for tests; add no network or model dependency in this slice.

### Consequences

- A future provider can reduce semantic setup work without changing the acceptance boundary.
- High model confidence cannot bypass evidence validation or human approval.
- Every extracted row receives an explicit disposition, making omissions and double counting visible.
- The current slice does not discover statement pages or coordinates, call an LLM, execute aggregations, persist configurations, or automate approval.
- ADR-007 subsequently adds deterministic execution for the reviewed signed-sum aggregation subset.

## ADR-007 — Execute approved component aggregations as calculated facts

**Status:** Accepted for the POC
**Date:** 27 September 2026

### Context

Real statements may present one canonical metric as several rows. Treating only one component as the metric would be incomplete, while embedding issuer labels or arithmetic in Python would not generalize. A reviewed semantic rule needs deterministic execution without converting model output into numerical evidence.

### Decision

- Freeze the exact locator, label, raw value, and evidence ID for every approved direct mapping, aggregation component, and exclusion.
- Support an initial generic signed-sum rule whose component coefficients are limited to `1` and `-1`.
- Reconfirm request, company, source reference, checksum, organization, document type, unit, period, and reporting basis before execution.
- Parse each component with the deterministic reported-number parser and retain its parsed value, coefficient, and contribution.
- Reject missing or changed evidence, invalid numbers, duplicate evidence use, duplicate targets, and contextual mismatches explicitly.
- Classify aggregate observations as `calculated`, retain source/proposal/rule/configuration/reviewer lineage, and make them compatible with existing statement reconciliation.
- Keep broader aggregation operators and the combined persisted normalization workflow out of this slice.

### Consequences

- Company-specific labels and component combinations remain versioned configuration rather than Python branches.
- Reviewed aggregation semantics can now produce reproducible canonical facts without model arithmetic.
- Component-level lineage makes signs, omissions, and double counting independently inspectable.
- A synthetic current-tax plus deferred-tax result passes the existing PBT-to-PAT reconciliation.
- Real-company aggregation rules and expected values still require independent accounting review.

## ADR-008 — Persist direct and aggregated onboarding outcomes together

**Status:** Accepted for the POC
**Date:** 27 September 2026

### Context

Direct mappings and deterministic aggregations were independently valid but did not yet form one durable normalization result. Persisting them without rechecking the Phase 2C link could allow an approved configuration to be paired with different PDF, CSV, extraction-profile, or row bytes.

### Decision

- Require the source manifest, extraction manifest, extraction link, onboarding request, and approved configuration for combined normalization.
- Re-verify both immutable artifacts and their extraction-link identities before producing facts.
- Bind onboarding requests and configurations to the extraction ID and profile version in addition to document and checksum identity.
- Compare every controlled-CSV field and row with the approved onboarding evidence.
- Require every evidence row to appear exactly once as a direct mapping, aggregation component, or exclusion.
- Persist reported direct facts, calculated aggregate facts, exclusions, issues, analysis blockers, extraction link, and approved configuration in one strict batch.
- Preserve failed benchmark or missing extraction review as blockers, and refuse to overwrite a different batch at the same output path.
- Provide a local `normalize-onboarding` CLI; proposal generation and approval remain separate reviewed steps.

### Consequences

- Consumers receive one auditable Phase 2D normalization artifact without losing the distinction between reported and calculated values.
- Approved configurations cannot silently move across extraction profiles or changed derived rows.
- The workflow remains local and provider-neutral with no model or network dependency.
- Automatic creation of proposals/configurations, representative real-report evaluation, review operations, and handoff to the full analysis workflow remain future work.

## ADR-009 — Gate live onboarding models with versioned golden evaluations

**Status:** Accepted for the POC
**Date:** 27 September 2026

### Context

A strict schema prevents malformed model output but does not show whether semantic mappings are correct. Connecting a live provider without a repeatable benchmark would hide model, prompt, and schema regressions and could reward coverage even when values or accounting relationships are wrong.

### Decision

- Evaluate the provider-neutral proposal contract against versioned, human-reviewed golden fixtures before live integration.
- Require each fixture to dispose of every evidence row exactly once through mapping, aggregation, or exclusion.
- Measure decision precision/recall, evidence coverage, hallucinated/duplicated/unaccounted evidence, expected deterministic values, and declared accounting reconciliations.
- Make thresholds explicit per fixture and persist the complete proposal, validation result, measurements, and pass/fail reasons.
- Preserve provider/model, prompt/schema, generation time, and optional token, latency, and cost metadata for comparison.
- Refuse to overwrite a different report at the same path and keep the evaluator outside the normalization authority path.
- Use only an explicitly synthetic fixture in this slice; do not claim real-report accuracy until a permitted, representative, independently reviewed corpus exists.

### Consequences

- Model and prompt versions can be compared with repeatable evidence rather than anecdotal output.
- A syntactically valid but semantically wrong proposal fails value and reconciliation gates.
- Missing usage metadata remains visible; it is not silently inferred.
- Live provider, privacy, prompt-injection, and representative-corpus gates remain future work.

## ADR-010 — Require explicit abstention for unresolved onboarding evidence

**Status:** Accepted for the POC
**Date:** 27 September 2026

### Context

Forcing a model to choose only a mapping, aggregation, or exclusion encourages confident but unsupported handling of ambiguous labels. Treating a missing disposition as an abstention would instead hide an omission and weaken evidence coverage controls.

### Decision

- Add a strict `AbstentionCandidate` containing a candidate ID, exact evidence ID, confidence, and rationale.
- Count an abstention as a visible evidence disposition for validation and golden-case evaluation.
- Score expected abstentions using precision and recall alongside the other disposition types.
- Allow a syntactically valid proposal with abstentions to be reviewed and evaluated, but reject it from approval until a reviewer resolves every abstention.
- Keep abstentions out of normalized facts and approved configurations.

### Consequences

- A provider can safely defer ambiguous rows without fabricating an accounting classification.
- Silent omissions remain validation errors, rather than being reclassified as abstentions.
- Evaluation can reward appropriate uncertainty, while normalization remains fully deterministic and reviewer-approved.

## ADR-011 — Persist reviewer outcomes and bind configurations to source identity

**Status:** Accepted for the POC
**Date:** 29 September 2026

### Context

The approval function created a valid configuration in memory, but there was no durable reviewer outcome, rejection trail, or safe way to retrieve an approved configuration. A version label alone is insufficient: applying a configuration to a different document, checksum, extraction profile, period, or reporting basis would undermine provenance.

### Decision

- Record an append-only review decision for every local approval or rejection.
- Store reviewer identity, timezone-aware timestamp, policy version, rationale, and deterministic validation result in each decision.
- Embed the approved configuration in an approved decision; require explicit rejection reasons for rejected decisions.
- Register approved configurations in a local append-only catalog keyed by company, document type, extraction profile, and configuration version.
- On retrieval, revalidate the configuration against every material request-identity field, including the source checksum and reporting context.
- Provide local `approve-onboarding` and `reject-onboarding` commands; do not create a multi-user queue, access-control system, or configuration-migration mechanism in this slice.

### Consequences

- Review outcomes remain auditable even when a proposal is rejected.
- Approved configurations can be replayed only for their verified source context.
- Later-filing reuse requires an explicit future migration/review policy rather than implicit label matching.

## ADR-012 — Compare cross-filing configurations without automatic migration

**Status:** Accepted for the POC
**Date:** 29 September 2026

### Context

Source-bound configurations are safe but leave repeated manual work when a company publishes a later filing with a similar statement layout. Automatically copying an old configuration based on label similarity could silently ignore new rows, changed labels, a changed extraction profile, or a different statement context.

### Decision

- Add a deterministic, review-only assessment between a prior approved configuration and a new onboarding request.
- Match only exact reported labels and require a single target row for each prior source row.
- Report missing and ambiguous labels, target-row conflicts, new rows, and all changed request-context fields.
- Block reuse candidates when company, source organization, document type, unit, reporting basis, or extraction profile differs.
- Keep document, checksum, source-reference, extraction-ID, and period changes visible but expected for a later filing.
- Persist the full source configuration, target request, and results in an immutable-style assessment with `requires_human_approval: true`.
- Do not generate a proposal, configuration, normalized fact, or automatic approval from the assessment.

### Consequences

- Reviewers can focus on changed and new evidence while retaining a complete comparison trail.
- Exact-label matching avoids hidden semantic inference in deterministic code.
- A future provider or migration policy can use the assessment as input only after evaluation and reviewer controls are established.

## ADR-013 — Require adversarial validation before live onboarding models

**Status:** Accepted for the POC
**Date:** 29 September 2026

### Context

A nominal golden case can show that a correct proposal works, but cannot show whether the same boundary rejects common model and document failures. The previous proposal identity omitted unit, period, and reporting basis, leaving a material statement-context mismatch undetected.

### Decision

- Require every proposal to carry the request's unit, reporting period, and reporting basis, and validate them deterministically.
- Add synthetic adversarial cases for changed labels, duplicate evidence, invented locators, wrong statement context, incorrect aggregation signs, and instruction-like filing text.
- Treat instruction-like filing text as evidence content; expected-abstention cases must demonstrate that it is not accepted as an instruction.
- Keep adversarial fixtures synthetic and use them to prove contract behavior only, not real-world model accuracy or provider-side prompt-isolation claims.

### Consequences

- A model cannot advance a proposal that changes material statement context.
- Evaluation now tests both correct and unsafe behavior before any live adapter is connected.
- Live-provider prompt isolation, privacy controls, and representative CA-reviewed corpus testing remain required future gates.

## ADR-014 — Gate real-model evaluation with a CA-reviewed local corpus registry

**Status:** Accepted for the POC
**Date:** 30 September 2026

### Context

Synthetic golden cases prove evaluator behavior but cannot substantiate accuracy on real company filings. A future real fixture must be tied to the permitted source document, reviewed extraction, exact statement context, and the full set of values/dispositions a qualified accounting reviewer actually examined. Otherwise a fixture could silently drift after review or be confused with a synthetic case.

### Decision

- Store each candidate real-case fixture as an append-only local evaluation-corpus entry; do not commit real reports, fixtures, or evaluation results.
- Bind the entry to a raw source manifest, reviewed extraction link, and exact onboarding request, validating all shared document, source, checksum, and extraction identity fields.
- Hash the canonical complete fixture and require that digest in the entry so the reviewed mappings, values, reconciliations, and thresholds are one audited object.
- Distinguish `ready_for_ca_review`, `approved_for_evaluation`, and `rejected` entries.
- Permit only a non-synthetic source with an assessed, non-restricted licence to become `approved_for_evaluation`.
- Require a named reviewer, timezone-aware review timestamp, policy version, and nonblank review notes for approval; reject entries with an unreviewed or rejected extraction link.
- Provide only local append-only registration, approved-case retrieval, and evaluation of a saved proposal through an approved entry. Do not add a model provider, corpus-wide release threshold, multi-user queue, or automated CA approval.

### Consequences

- A future provider can be evaluated only against fixtures whose values and evidence lineage have a specific CA approval record.
- Synthetic cases remain useful for contract and adversarial tests but cannot be misrepresented as a real-model quality gate.
- Real corpus population and reviewer judgment remain explicit local work, while versioned entries provide a reproducible audit foundation for later provider comparisons.
- Privacy, prompt-isolation, corpus-level performance thresholds, cost/latency budgets, and review operations remain required future controls.

## ADR-015 — Separate provisional internal evaluation from CA-approved model gates

**Status:** Accepted for the POC; live-call prohibition superseded narrowly by ADR-019
**Date:** 1 October 2026

### Context

The first permitted real-company corpus case can be useful to exercise the local onboarding and evaluator workflow before a qualified CA is available. Calling that work CA approval, or allowing it to enter the same evaluation route as CA-approved cases, would overstate the reliability of the golden fixture and weaken the live-model gate.

### Decision

- Add the append-only corpus state `provisional_internal_review` for a permitted real case with the exact fixture checksum, named internal reviewer, timezone-aware timestamp, internal-policy version, and nonblank notes. A local command creates it only as a new version from a `ready_for_ca_review` candidate.
- Keep `approved_for_evaluation` unchanged: it remains the only state returned by `get_approved` and the only source accepted by `evaluate-approved-corpus`.
- Add `evaluate-provisional-corpus`, which retrieves only a provisional entry and writes a report with `evaluation_qualification: provisional_internal_review` to a separate default location.
- Do not permit synthetic, unassessed, or restricted cases to receive provisional internal review.
- Treat provisional results as local workflow-testing evidence only. They cannot create an approved configuration, demonstrate real-model readiness, authorize broader live use, or substitute for CA review. ADR-019 later permits one separately labelled technical provider call against such an entry.

### Consequences

- The team can find integration and evaluation defects using a locally reviewed permitted case without mislabelling the review authority.
- Consumers can distinguish provisional and CA-approved reports directly from persisted artifacts, not only from a command name or file path.
- A later CA review requires a new append-only corpus version; it cannot overwrite or silently promote the provisional record.

## ADR-016 — Summarize provisional corpus quality without creating a live-model gate

**Status:** Accepted for the POC
**Date:** 1 October 2026

### Context

Several internally reviewed real-company cases can exercise the onboarding workflow more meaningfully than a single case. A simple collection of individual reports, however, does not state whether a declared internal policy was met. Treating an internal aggregate pass as permission to connect a live provider would wrongly convert non-CA review into a production-quality claim.

### Decision

- Add a `ProvisionalCorpusEvaluator` that accepts only entries already marked `provisional_internal_review` and evaluates one saved proposal per entry.
- Make a versioned policy declare minimum case count, distinct-company count, pass rate, and maximum failed cases.
- Persist all individual reports, aggregate counts, pass rate, policy failures, and an `internal_gate_passed` result in a non-overwriting report.
- Hard-code the report qualification as `provisional_internal_review`, require `live_model_eligible: false`, and retain an explicit live-model blocker regardless of the internal outcome.
- Keep CA-approved corpus policy, privacy controls, prompt isolation, provider reliability, cost/latency budgets, and live-provider admission as separate future work.

### Consequences

- The team can compare several local cases under a transparent and reproducible internal threshold before a provider is connected.
- A passing internal summary remains workflow evidence only; it cannot promote entries, create approved configurations, or authorize a live model.
- A future CA-approved gate may reuse the reporting pattern but requires its own policy and review authority rather than relaxing this one.

## ADR-017 — Isolate and minimize filing evidence before a future model call

**Status:** Accepted for the POC
**Date:** 1 October 2026

### Context

Filings can contain long, irrelevant, or instruction-like text. A future provider needs enough context to propose evidence-bound mappings, but sending local paths, raw PDFs, or arbitrary document content increases unnecessary disclosure and creates a prompt-injection risk. A static prompt string alone is insufficient if untrusted filing content is interpolated into the same instruction channel.

### Decision

- Convert an approved onboarding request into a versioned, bounded `PromptIsolatedOnboardingInput` before any future provider call.
- Include only identity needed for proposal validation plus page/table/row/column locators, reported labels, and raw values; exclude local filesystem paths, raw PDF bytes, filenames, and arbitrary document text.
- Classify every supplied row as `untrusted_evidence_rows`, checksum its canonical serialized content, and reject oversized fields or unsupported control characters rather than silently truncating them.
- Keep fixed developer instructions as a constant and render dynamic source content only as a separate data-only user payload. A future provider adapter must preserve that role separation and return the existing strict proposal schema.
- Do not call a model, add a provider dependency, claim complete prompt-injection prevention, or relax any deterministic validation or review gate in this slice.

### Consequences

- A future adapter receives a minimal, replayable, checksum-bound input packet instead of direct access to local source files.
- Instruction-like filing text is visible for semantic interpretation but remains isolated from trusted instructions and is still subject to proposal validation and abstention rules.
- Provider-specific role handling, structured-output enforcement, retries, error handling, privacy review, and model connection remain separate preconditions for live integration.

## ADR-018 — Permit a corpus-gated optional OpenAI evaluation adapter

**Status:** Accepted for the POC
**Date:** 4 October 2026

### Context

The provider-neutral contract, prompt-isolated evidence packet, deterministic validator, and CA-reviewed corpus gate are implemented. The project owner approved a narrowly scoped OpenAI integration to evaluate that contract without sending raw PDFs or allowing a model to create approved financial facts.

### Decision

- Add OpenAI as an optional dependency, with a lazy import and `OPENAI_API_KEY` read only from the local environment at invocation time.
- Send only `PromptIsolatedOnboardingInput` through a fixed developer message plus a separate data-only user message; do not upload, transmit, or name a local raw PDF.
- Require Responses structured output with a strict JSON schema, `store=False`, a finite output-token limit, and no automatic retry in the initial slice.
- Bind proposal identity, request identity, source identity, timestamp, returned model version, and usage metadata locally; the provider may return only mapping, aggregation, exclusion, and abstention candidates.
- Initially make `evaluate-openai-approved-corpus` the sole live call path. ADR-019 later adds a separately labelled provisional technical-evaluation path without changing the CA quality gate.
- Preserve deterministic validation, accounting evaluation, review requirements, and the prohibition on direct model-created facts.

### Consequences

- The normal local workflow remains usable without the SDK, an API key, network access, or a paid account.
- A CA-approved quality evaluation can be run reproducibly once a permitted CA-reviewed corpus exists, while raw evidence and secrets remain local.
- The current corpus has only provisional internal entries, so it can support only the limited technical route defined in ADR-019.
- Retries, provider comparison, cost budgeting, and broader production use remain later, separately governed work.

## ADR-019 — Permit one provisional internal OpenAI technical evaluation

**Status:** Accepted for the POC
**Date:** 4 October 2026

### Context

The project needs to verify the complete optional adapter path with an actual local API key: bounded input creation, provider authentication, strict structured output, model provenance, deterministic proposal validation, reconciliation, and report persistence. The available permitted real cases have internal review only, not CA approval.

### Decision

- Permit `evaluate-openai-provisional-corpus` to retrieve only a `provisional_internal_review` entry and make one explicit OpenAI adapter call.
- Preserve `evaluation_qualification: provisional_internal_review`, separate output storage, `live_model_eligible: false`, and all deterministic validation and accounting checks.
- Continue to reject candidate, rejected, approved, and synthetic entries from this command.
- Keep the raw PDF local; send only the same bounded prompt-isolated packet with `store=False`.
- Do not allow this technical result to approve a mapping, normalise facts, promote an entry, establish model accuracy, or authorize broader live use.

### Consequences

- The team can test actual credentials and provider behavior without misrepresenting internal review as CA approval.
- A failing report is useful integration evidence; a passing report is only a provisional technical result.
- CA-approved corpus evaluation, quality thresholds, cost/latency policy, and any broader onboarding use remain separate gates.

## ADR-020 — Make full-metric and component-aggregation policy explicit in prompt contract v2

**Status:** Superseded by ADR-021; retained as the historical v2 evaluation policy
**Date:** 4 October 2026

### Context

The first APSEZ provisional OpenAI evaluation was structurally valid and reconciled, but the model
mapped an interest-only row to full finance cost, abstained on other finance-cost components, and
used an explicit tax total where the reviewed POC fixture expects component aggregation. The
original trusted instructions did not state whether a component, a total, or a signed aggregation
should be preferred.

### Decision

- Version the trusted prompt contract as `onboarding-model-input-v2`, while retaining v1 parsing compatibility for existing local packets.
- State that a direct mapping must represent the full canonical metric and that one component must not stand in for the total.
- Direct the provider to propose one signed aggregation when relevant components are available and explicitly exclude a duplicated subtotal or reported total.
- Supply an initial general finance-cost interpretation for interest/bank charges, derivative losses, and foreign-exchange losses presented as statement expenses, while preserving abstention for contradicting or unresolved evidence.
- Treat this as an evaluation policy to be measured on the corpus, not an automatic accounting rule or fact-approval path.

### Consequences

- Later evaluations identify the exact prompt-policy version that shaped a proposal.
- The policy can improve complete evidence use without allowing the model to perform arithmetic or bypass deterministic validation.
- The current APSEZ v1 fixture remains immutable; a change to its expected tax treatment would require a new reviewed fixture version.
- The first provisional APSEZ v2 evaluation completed the full adapter path and matched the fixture's finance-cost amount, but deterministically failed because it also formed PBT and PAT aggregates from component rows and reused evidence. Numerical agreement did not establish the accounting scope independently. ADR-021 replaces this policy.

## ADR-021 — Prefer supported reported totals and supply versioned metric context

**Status:** Accepted for the POC
**Date:** 4 October 2026

### Context

The v2 aggregation-first instruction encouraged needless PBT/PAT reconstruction. Its general
FX/derivative finance-cost assumption was stronger than the supplied row context supported.
The provider also received metric identifiers without the dictionary's definitions, and its wire
schema offered derived targets that deterministic validation later rejected.

### Decision

- Build new input packets under `onboarding-model-input-v3`, including the checksummed
  `onboarding-metric-catalog-v1` snapshot of eligible non-derived definitions and generic scope
  guidance. Preserve legacy v1/v2 parsing without pretending to replay their instructions.
- Prefer reported amounts only when their accounting scope fits; permit complete signed component
  aggregations when needed, equivalent labels, explicit exclusions, and targeted abstentions.
  Describe row roles relative to the target, not through a universal total/component classification.
- Remove the blanket classification of statement FX/derivative losses as finance costs. Require
  supporting evidence; preserve uncertainty when notes or scope definitions are unavailable.
- Keep the existing single-disposition, one-target, deterministic arithmetic and human-review
  contracts. Do not introduce partial approval, model certification, or automatic semantic checks
  that claim to understand accounting merely from matching numbers.
- Restrict both mapping and aggregation enums in `openai-onboarding-proposal-v2` to the same
  catalog; reject out-of-catalog targets locally too. Bind the exact input and instruction hashes
  to new model runs. Existing corpus requests, expected answers, and thresholds remain unchanged.
- Explicitly set `max_retries=0` to implement ADR-018's intended no-retry boundary; relying on the
  SDK default in the first adapter did not enforce that intent.
- Test with synthetic fixtures and frozen provider responses. Do not make paid API calls or claim
  improved live accuracy as part of this implementation slice.

### Consequences

- Source evidence and calculation rules remain immutable; prompt/catalog/schema changes have
  explicit versions and exact content hashes for new calls.
- Exact-route evaluation can still reject a legitimate alternative evidence route. Alternatives
  require separately reviewed fixture/policy versioning, not lower thresholds or rewritten history.
- Missing source-note context, fine-grained review, and real model effectiveness remain future
  work. The catalog exposes eligible metrics, not a required list or CA-approved interpretations.
