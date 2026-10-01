# Development roadmap

Each phase ends at a validation gate. Later phases may be replanned as open decisions are resolved; completing a phase does not authorize deferred work.

## Phase 0 — Research and architecture

- **Objectives:** preserve research, establish durable context, define boundaries, and prove a source-aware skeleton.
- **Deliverables:** organized documents, open-decision register, POC architecture, typed domain models, protocols, synthetic workflow, and repository tooling.
- **Validation criteria:** original research remains intact; synthetic provenance is enforced; tests, lint, formatting, and typing pass.
- **Dependencies:** original research documents and Python 3.12 development environment.
- **Risks:** premature abstraction, implicit product choices, or demo data being mistaken for real evidence.
- **Explicitly deferred:** live retrieval, parsing, LLMs, forecasts, valuation, decks, and UI.

## Phase 1 — Local deterministic financial-analysis engine

**Implementation status:** Engineering baseline implemented on synthetic data; independent CA review and real-company mapping validation remain open.

- **Objectives:** define canonical non-financial metrics and reconciled historical calculations.
- **Deliverables:** statement/metric dictionaries, period and basis handling, ratio and cash-flow modules, adjustment records, and formula documentation.
- **Validation criteria:** CA-reviewed formulas; golden datasets; statement reconciliation; edge-case and restatement tests.
- **Dependencies:** Phase 0 models, pilot company choice, and agreed accounting definitions.
- **Risks:** mixing bases/periods, false comparability, and hidden normalization judgments.
- **Explicitly deferred:** banks/NBFCs/insurers, automated retrieval, narrative agents, and valuation.

## Phase 2 — Source ingestion and normalization

- **Objectives:** ingest permitted local filings and normalize them without losing raw lineage.
- **Deliverables:** immutable content-addressed raw store, catalog, XBRL/document adapters, parsing pipeline, normalized facts, and revision/conflict logs.
- **Validation criteria:** checksum/version preservation, page/table lineage, source reconciliation, parser accuracy benchmarks, and licence classification.
- **Dependencies:** source-rights review, fixture corpus, canonical metrics, and manual benchmark reports.
- **Risks:** document variation, revisions, OCR/table errors, access restrictions, and unauthorized reuse.
- **Explicitly deferred:** broad-universe automation and unofficial scraping.

**Current implementation — Phases 2A–2C:** local intake copies a manually supplied, permitted file into checksum-addressed raw storage and registers provenance and licence metadata. Controlled CSV normalization produces canonical observations through source-specific, versioned exact-label mappings. Synthetic benchmarks cover ruled and borderless aligned statements; separate PDF/CSV checksums, exact-row benchmarks, and accepted human review are required. A local Infosys FY2026 page test matched 19/19 manually checked candidates and validated Indian number parsing, but is not a general accuracy benchmark. General profile routing, semantic/aggregation review, OCR/XBRL extraction, adapter retrieval, revision handling, and conflict resolution remain later Phase 2 slices.

### Phase 2D — LLM-assisted document onboarding

**Implementation status:** Provider-neutral foundation, prompt-isolated bounded model-input preparation, reviewed signed-sum aggregation, combined verified normalization/persistence, synthetic golden-case and adversarial evaluation with safe abstention handling, local approval/rejection records with an identity-bound configuration catalog, review-only cross-filing reuse assessment, and an append-only controlled real-case evaluation-corpus registry implemented. The registry permits separately labelled provisional internal evaluation and a local multi-case pass-rate/failure-budget summary, but reserves real-model quality gating for CA-approved entries; a representative CA-reviewed corpus, live model integration, configuration migration policy, and multi-user review operations remain open.

- **Objective:** reduce first-time setup work for new companies and filing layouts without making a model the numerical authority.
- **LLM responsibilities:** propose document/statement classification, relevant pages, extraction profile and coordinates, period/unit/basis interpretation, canonical metric mappings, and component aggregation candidates.
- **Deterministic responsibilities:** re-extract values from cited locations, parse numbers, apply units/signs, enforce period and basis consistency, prevent duplicate row use, execute aggregation rules, reconcile statements, and decide readiness under an explicit review policy.
- **Provenance:** retain document checksum, evidence locators, provider/model/version, prompt and schema versions, candidate output, rationale/confidence, validation outcomes, review decision, and approved configuration version.
- **Implemented deliverables:** provider-neutral proposal protocol, strict checksummed request/proposal schemas carrying full statement context, deterministic static adapter, extracted-row request builder, prompt-isolated bounded input packet with data-only payload, candidate validation, explicit exclusions and abstentions, human approval/rejection records, versioned direct mapping configuration, identity-bound local configuration catalog, review-only cross-filing comparison, frozen approved evidence snapshots, signed-sum aggregation with reconciliation coverage, reviewed PDF/CSV re-verification, combined normalization batch, non-overwriting persistence, `normalize-onboarding`, `prepare-onboarding-model-input`, `approve-onboarding`, `reject-onboarding`, `assess-onboarding-reuse`, `register-evaluation-corpus`, `provisionally-review-evaluation-corpus`, `evaluate-provisional-corpus`, `evaluate-provisional-corpus-set`, and `evaluate-approved-corpus` CLIs, versioned golden fixture schema, synthetic nominal and adversarial accuracy/coverage/value/reconciliation evaluation, model-usage provenance, immutable-style evaluation reports, and a local registry that binds permitted real evaluation cases to a reviewed extraction link and fixture checksum. Provisional internal evaluation is explicitly marked, has a separately labelled internal corpus summary, and cannot substitute for the CA sign-off required by `approved_for_evaluation`.
- **Remaining deliverables:** populate a representative permitted CA-reviewed evaluation corpus, agree CA-approved quality/privacy/cost/latency gates, provider role-separation and structured-output policy, retry/error controls, multi-user review queue and amendments, approved configuration-migration policy across filings, real provider adapter, and profile-discovery proposals.
- **Validation criteria:** benchmark mapping/profile proposal accuracy and abstention; reject malformed, unsupported, duplicated, or unreconciled candidates; replay approved configurations deterministically; measure cost and latency without weakening evidence gates.
- **Dependencies:** approved privacy/provider policy, representative permitted filings, CA-reviewed golden mappings and aggregations, and the Phase 2C lineage contract.
- **Risks:** hallucinated locators, semantic overconfidence, prompt injection in filings, data disclosure, model drift, cost, latency, and false automation confidence.
- **POC sequencing:** use the implemented registry to expand the synthetic fixture into a representative locally reviewed corpus, then obtain CA approval for the cases intended to gate a live model. Provisional internal cases may exercise the workflow but do not satisfy this gate. Connect a real LLM only after corpus-level quality, privacy, prompt-isolation, and cost/latency gates are agreed; the current POC does not add an OpenAI API dependency.

## Phase 3 — Peer selection and sector rules

- **Objectives:** select explainable peers and apply business-model-aware metrics.
- **Deliverables:** company/security master, candidate generation, ranking rationale, override workflow, IT-services rules, and a second non-financial sector module.
- **Validation criteria:** expert-labelled peer set comparison, exclusion explanations, metric comparability tests, and sector-specific benchmarks.
- **Dependencies:** normalized data coverage and decisions on the pilot universe and peer criteria.
- **Risks:** conglomerates, sparse peers, corporate actions, classification drift, and misleading rankings.
- **Explicitly deferred:** a universal cross-sector score and financial-institution rules.

## Phase 4 — Agent orchestration and evidence synthesis

- **Objectives:** coordinate deterministic capabilities and produce evidence-backed narrative findings.
- **Deliverables:** controlled orchestration, retrieval, claim/evidence validation, finding schema, confidence handling, evaluation cases, and model/provider adapter.
- **Validation criteria:** no uncited material claims, no model arithmetic as truth, reproducible runs, adversarial tests, and cost/latency measurements.
- **Dependencies:** stable facts/analytics, evaluation set, provider decision, privacy/compliance boundaries, and lessons from the narrower Phase 2D model adapter if implemented.
- **Risks:** hallucination, prompt injection, unsupported synthesis, non-determinism, and vendor lock-in.
- **Explicitly deferred:** unconstrained autonomous agents and public recommendations.

## Phase 5 — Forecasting, valuation, and backtesting

- **Objectives:** implement explainable driver scenarios and evaluate them point in time.
- **Deliverables:** integrated base/bull/bear model, assumption registry, validation checks, historical vintages, walk-forward backtests, and valuation/reverse-DCF modules if approved.
- **Validation criteria:** balanced statements, baseline comparisons, interval calibration, no look-ahead/survivorship bias, and versioned inputs/results.
- **Dependencies:** historical point-in-time data, sector drivers, forecast/valuation product decision, and methodology review.
- **Risks:** false precision, weak drivers, stale prices, biased samples, and regulated-output implications.
- **Explicitly deferred:** short-term price prediction and opaque ML forecasting.

## Phase 6 — Charts and PowerPoint generation

- **Objectives:** produce a story-led 16:9 deck with a modular evidence appendix.
- **Deliverables:** chart grammar, narrative slide selection, citation notes, renderer, deck templates, and methodology/evidence artifacts.
- **Validation criteria:** number reconciliation, historical/forecast distinction, citation completeness, accessibility checks, and rendered visual inspection of every slide.
- **Dependencies:** stable structured analysis, visual-identity decision, and permitted display rights.
- **Risks:** misleading visual scales, clipping, unsupported titles, excessive density, and redistribution restrictions.
- **Explicitly deferred:** arbitrary branding ingestion and unattended public release.

## Phase 7 — Chat/API interface

- **Objectives:** expose approved workflows through a usable, observable interface.
- **Deliverables:** API contract, chat/session model, job status, downloadable artifacts, corrections, access controls, and optional web UI.
- **Validation criteria:** end-to-end usability, authorization, input safety, audit logs, performance budgets, and failure recovery.
- **Dependencies:** interface-sequencing choice, validated research pipeline, security design, and product discovery.
- **Risks:** user ambiguity, privacy leakage, long-running jobs, misuse, and unsupported expectations.
- **Explicitly deferred:** trading execution and personalized portfolio advice.

## Phase 8 — Production licensing, security, monitoring, and evaluation

- **Objectives:** establish lawful, secure, measurable production operations.
- **Deliverables:** provider contracts, licence-aware retention/display controls, threat model, incident response, quality monitoring, cost ledger, compliance records, and human-review workflows.
- **Validation criteria:** legal/security sign-off, source SLAs, deletion/retention tests, monitoring coverage, red-team results, and defined release thresholds.
- **Dependencies:** commercial model, user scope, provider selection, deployment architecture, and specialist counsel.
- **Risks:** licensing cost, regulatory classification, data breaches, source drift, model degradation, and inadequate review capacity.
- **Explicitly deferred:** geographic or product expansion until controls are proven.
