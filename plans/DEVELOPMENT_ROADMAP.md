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
- **Dependencies:** stable facts/analytics, evaluation set, provider decision, and privacy/compliance boundaries.
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
