# Project context

## Purpose

This repository is the foundation for a local-first, chat-accessible research and analysis platform for Indian listed companies. A user should eventually be able to name a company and receive a source-backed explanation of its business, peers, historical performance, accounting quality, competitive position, improvement opportunities, forecasts, valuation context, risks, catalysts, and monitoring indicators, with a downloadable consultant-style presentation and evidence-heavy appendix.

The product is decision support and education. It must not present itself as investment, audit, tax, legal, or regulated financial advice. Legal classification, data rights, disclosures, and human-review boundaries require specialist review before public launch.

## Current phase and scope

The repository is in proof-of-concept development. Phase 1 currently does this:

1. load five annual periods of clearly labelled synthetic non-financial statements;
2. validate companies, canonical metrics, periods, provenance, restatements, and adjustments;
3. preserve superseded facts while selecting the current restated observation;
4. reconcile EBITDA/EBIT, PAT, balance-sheet totals, and cash roll-forwards;
5. calculate documented growth, margin, cash-flow, return, working-capital, and leverage metrics;
6. explain missing, zero-denominator, incomparable, and not-applicable results;
7. produce an `AnalysisRunManifest` and structured JSON result with full input lineage.

Phase 2A additionally accepts a manually supplied, permitted local document; copies it to immutable checksum-addressed raw storage; records provenance, licence classification, and a manifest; and verifies the stored bytes against that manifest. It is deliberately not yet a filing parser or normalized-fact pipeline.

Phase 2B adds a deterministic parser for verified, controlled financial-statement CSV files. It maps exact reported labels through source-specific versioned configurations, produces engine-compatible observations, retains page/table/row/column lineage and raw labels/values, and exposes invalid, unmapped, mismatched, and duplicate rows as blocking issues. It does not yet extract facts from PDF, HTML, OCR, or XBRL sources.

Phase 2C adds benchmarked deterministic profiles for a ruled two-column table and a configured period column in a borderless aligned statement. It preserves the PDF and derived CSV as separate immutable artifacts, binds both checksums in an extraction link, records extraction tool/profile versions, and blocks linked facts until the benchmark passes and a human accepts the extraction. A local Infosys FY2026 test matched 19/19 manually checked profit-and-loss candidates and correctly parsed Indian comma grouping and parentheses; semantic mapping and aggregation remain unapproved.

Phase 2D now provides the provider-neutral foundation for LLM-assisted document onboarding. It converts a review-ready extraction into checksummed, locator-backed evidence; accepts strict mapping, aggregation, exclusion, and explicit-abstention candidates through a replaceable proposal protocol; rejects hallucinated, duplicated, changed, omitted, identity-mismatched, and derived-metric candidates deterministically; and requires explicit human approval before producing a versioned configuration. An abstention is a visible request for human resolution, not a normalized fact and not an approval path. A deterministic static provider proves the boundary without a model or network dependency. Approved signed-sum rules execute with frozen component evidence and calculated-value classification; a synthetic tax aggregation passes the existing PBT-to-PAT reconciliation. The combined onboarding workflow re-verifies the PDF/CSV extraction link and exact rows, then persists reported direct facts, calculated aggregates, exclusions, issues, blockers, and complete configuration/review lineage in one non-overwriting batch. A versioned golden-case evaluator now measures mapping, aggregation, exclusion, and abstention precision/recall, evidence coverage and hallucination, expected canonical values, and accounting reconciliations; it also preserves optional token, latency, and cost metadata in the audit report.

The project does not retrieve live data, generally parse annual reports, perform OCR, parse XBRL, use an LLM at runtime, forecast, value securities, recommend investments, generate slides, or serve a UI. The Phase 1 formula baseline, every real-company mapping, every real-document extraction profile, and the future real-report evaluation corpus still require independent CA review before real-company conclusions. Phase 2D implements the model-facing safety and evaluation contracts, not a live provider integration or automatic mapping system.

## Analytical model

Future analysis connects five lenses through one evidence base:

1. **Financial Truth:** accounting quality, cash conversion, working capital, debt/liquidity, contingencies, related parties, audit matters, governance, and disclosure quality.
2. **Performance Diagnosis:** growth, price/volume/mix, margins, cost structure, operating leverage, returns, asset use, cash flow, and peer performance.
3. **Strategic Position:** industry structure, customers and suppliers, differentiation, advantage durability, market share, disruption, and execution evidence.
4. **Value-Creation Plan:** revenue, margin, working capital, capital allocation, portfolio, capabilities, practical actions, and KPIs.
5. **Investor and Credit Outlook:** driver-based scenarios, valuation context, solvency, catalysts, downside, and monitoring signals.

The perspectives include accounting/forensic analysis, CFO and performance improvement, strategy, equity research, and credit/risk. They should contribute to a linked issue tree, not produce repetitive essays.

## Evidence and classification rules

Evidence precedes opinion. Material facts and conclusions must retain an information cutoff, reporting basis, definition, source, locator where practical, retrieval time, transformation version, restatement state, and confidence.

Values must be explicitly classified as reported, calculated, estimated, forecast, management guidance, or analyst hypothesis. Synthetic/demo is a source classification and remains visible independently of the value classification. LLM narrative is never numerical evidence. Missing, stale, conflicting, or incomparable data lowers confidence and must not be silently filled.

Raw documents are immutable. Preserve original and revised versions, hashes, timestamps, and point-in-time availability. Normalized values and adjustments remain separate from reported values. Do not mix consolidated and standalone accounts, fiscal periods, or incompatible metric definitions.

## Source principles

The priority order is:

1. latest revised NSE or BSE filing;
2. audited annual report;
3. regulator or government source;
4. company investor-relations material;
5. licensed specialist provider;
6. reputable news or secondary research;
7. retail aggregator;
8. social or informal source.

Credibility and legal/commercial usability are different. Public access is not permission for automated collection, storage, transformation, model use, display, or redistribution. During the zero-budget POC, use manually acquired official documents, permitted exchange files, RBI/OGD/MCA sources where appropriate, frozen end-of-day data, and clearly labelled synthetic fixtures. Never bypass controls or rely on undocumented endpoints as production APIs. All external access belongs behind replaceable adapters.

## Recommendation standard

Every future recommendation should be capable of carrying observation, evidence, materiality, root-cause hypotheses, proposed action, value mechanism, impact range, time horizon, difficulty, dependencies, internal evidence required, KPIs, and confidence. With public data alone, recommendations are outside-in hypotheses and must say what internal information is needed to confirm them.

## Forecasting direction

Forecast operating drivers first and statements second. Start with a three-year base/bull/bear model covering revenue or volume, margins, PAT/EPS, working capital, cash flow, returns, debt, and liquidity. Preserve information cutoff, data version, assumptions, scenario definitions, confidence, model version, and point-in-time backtests. Do not begin with short-term price prediction or opaque machine learning.

## Presentation direction

The eventual portable output is a 16:9 PowerPoint with roughly 10–15 story-led main slides plus a modular evidence appendix. Historical series and forecasts must be visibly different. Slide titles should communicate conclusions, citations should follow claims into charts and notes, and every deck must pass reconciliation, content, and visual QA. Presentation generation is not part of the foundational slice.

## Architecture

Use Python 3.12 and a `src` layout. Keep the system framework-neutral:

- domain models express business meaning and validation;
- source adapters perform I/O;
- ingestion and normalization preserve lineage;
- analytics contains deterministic formulas;
- forecasting contains scenario mathematics and backtests;
- agents choose capabilities and synthesize evidence;
- workflows control order and manifests;
- reporting renders validated structured outputs.

The package uses Pydantic for typed models and standard-library composition. Phase 1 adds no new runtime dependency. Add pandas, DuckDB, HTTP clients, plotting, presentation, model, or orchestration dependencies only when an implemented vertical slice requires them. Accounting conventions are documented in `docs/methodology/FINANCIAL_METRICS.md`.

Financial institutions are explicitly out of the initial non-financial engine. Banks, NBFCs, and insurers require separate statement models, regulatory concepts, ratios, sector rules, and validation.

## Provisional POC defaults

- mode/audience: Investor Mode for a retail investor or research analyst;
- suggested company: Infosys;
- suggested peers: TCS, HCLTech, Wipro, and Tech Mahindra;
- source: synthetic fixture only in the first slice;
- longer-term history: five annual periods and eight quarters;
- market data: frozen end-of-day;
- forecast horizon: three years with base, bull, and bear scenarios;
- eventual output: approximately 12 main slides plus appendix;
- environment: local and private.

These are not hardcoded universal decisions. See `plans/OPEN_DECISIONS.md`.

## Durable working practices

Read `AGENTS.md` before implementation. Make small changes, protect unrelated work, add deterministic tests, validate before committing, and record material architecture decisions. Never commit secrets or licensed/confidential source documents. The original research is preserved in `plans/PROJECT_RESEARCH_BLUEPRINT.md`, `plans/PRESENTATION_OUTPUT_SPEC.md`, and `research/DATA_SOURCE_STRATEGY.md`.
