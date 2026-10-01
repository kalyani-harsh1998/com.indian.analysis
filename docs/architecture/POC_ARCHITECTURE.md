# POC architecture

## Goal

Establish the smallest end-to-end path that proves typed, source-aware, deterministic analysis can run locally. The POC favors explicit composition over autonomous agents or infrastructure.

```text
synthetic JSON fixture
        |
        v
LocalFileDataSource -> Pydantic validation -> provenance/revision gate
        |                                      |
        +--------------------+-----------------+
                             v
                 CompanyAnalysisWorkflow
                             |
       reconciliation + deterministic financial engine
                             |
                             v
   manifest + calculations + reconciliation results
                             |
                             v
                    structured JSON output
```

Phase 2A adds a separate evidence-intake path; it does not yet feed the financial engine:

```text
manually supplied source PDF
        |
        v
SHA-256 + copy-only content-addressed raw store
        |
        v
immutable raw copy + append-only local manifest catalog
        |
        v
independent checksum verification
        |
        v
explicit ruled or aligned-coordinate extraction profile
        |
        v
derived CSV checksum + benchmark + human review
        |
        v
cryptographic PDF-to-CSV extraction link
        |
        v
controlled CSV parser + versioned exact-label mapping
        |
        v
normalized observations + field lineage + explicit issues
```

The Phase 2D foundation adds a replaceable proposal adapter beside, not inside, the deterministic pipeline:

```text
PDF text/layout evidence -> LLM candidate profile/mappings/aggregations
                                      |
                                      v
                        strict versioned proposal schema
                                      |
                                      v
source locators -> deterministic extraction/parsing/aggregation/reconciliation
                                      |
                                      v
                         review policy or human review
                                      |
                                      v
                       approved reusable configuration
                                      |
                                      v
              verified combined normalization batch
```

The current static adapter and strict schemas prove this boundary without calling a model. A future live model can reduce discovery and mapping effort for a new layout. Approved numbers still originate from source locations and deterministic transformations, never from model-generated arithmetic or unsupported narrative. The signed-sum executor freezes each approved component row, parses and combines it with `Decimal`, classifies the output as calculated, and carries it into existing statement reconciliation. The combined workflow re-verifies the source/derived artifact link and exact CSV rows before persisting direct facts, aggregate facts, exclusions, issues, and blockers together.

Before a live adapter is connected, the same provider protocol can be routed through a golden-case evaluator. Versioned fixtures define expected evidence dispositions, canonical values, reconciliations, and thresholds. Persisted reports retain the proposal, deterministic validation, accuracy/coverage results, model and prompt identity, and optional usage/cost metadata. This is a quality gate around the adapter; it does not replace review or enter the financial calculation path.

An explicit abstention is a fourth evidence disposition alongside mapping, aggregation, and exclusion. It carries the source row and rationale into validation and evaluation, allowing a provider to safely defer an ambiguous row. Approval rejects any proposal containing an abstention, so a reviewer must resolve it before a configuration enters deterministic normalization.

The local review boundary records approvals and rejections separately from proposal artifacts. An approved record embeds its configuration and is registered in an append-only catalog keyed by company, document type, extraction profile, and configuration version. Retrieval revalidates the full request identity, including the source checksum, so the catalog supports reproducible replay for the same evidence rather than unreviewed reuse on a later filing.

For a later filing, a deterministic reuse assessor compares the new evidence labels with each approved mapping, aggregation component, and exclusion. Its persisted assessment identifies reuse candidates, missing/ambiguous rows, incompatible context, and new rows. It is deliberately outside both approval and normalization: every target configuration still needs new validation and human approval.

The live-model quality gate is likewise separate from normalization. A local evaluation-corpus entry binds a permitted real source manifest, reviewed PDF-to-CSV extraction link, exact onboarding request, complete golden fixture, and fixture checksum. A named internal reviewer may mark such a case `provisional_internal_review` to exercise the separately labelled internal evaluator, but that result cannot gate a live model. Only after a CA reviewer records policy, timestamp, and review notes may the entry be marked `approved_for_evaluation`. Candidate, provisional, rejected, and synthetic entries cannot serve as real-model benchmark cases.

The proposal boundary also includes unit, period, and reporting basis. Synthetic adversarial cases prove that a changed label, duplicate evidence use, invented locator, incompatible statement context, incorrect aggregation sign, or instruction-like source text cannot silently become a trusted configuration or fact. Provider-side prompt isolation remains a separate future live-adapter requirement.

## Boundaries and dependency direction

Dependencies point inward toward `domain` and deterministic functions:

- `domain` has no project-layer dependencies or I/O.
- `data` depends on domain types and implements replaceable source contracts.
- `analytics` depends on domain types only where a typed result is required; formulas remain pure.
- `agents`, `forecasting`, and `reporting` expose small protocols without third-party frameworks.
- `workflows` composes sources and analytics and owns run lifecycle/manifest creation.
- the CLI is an outer adapter that resolves local paths and serializes results.

## Foundational interfaces

- `DataSource`: load a validated demo dataset; future adapters implement equivalent source-specific behavior.
- `AnalysisStep` and `AnalysisAgent`: accept typed inputs and return typed outputs without embedding formulas in prompts.
- `ForecastEngine`: produce typed forecast scenarios from typed assumptions when forecasting enters scope.
- `ReportRenderer`: convert a validated result to an artifact.
- `CitationStore`: register and retrieve source references.

Protocols are intentionally narrow and framework-neutral. Additional methods should be driven by a tested use case rather than anticipation.

## Provenance model

Each input observation has one or more source-reference IDs. The workflow rejects missing references and unknown IDs before calculation. Calculation and reconciliation results retain the input observation IDs and the union of their source references. Superseded observations remain stored but are excluded from current-period calculations.

The fixture source is explicitly `synthetic`; its fictional values are not representations of Infosys or its peers. Phase 2A manifests retain checksums, publication/retrieval timestamps, document locators, parser version where relevant, and licensing classification. Phase 2B normalized facts retain the original label/value, field locator, parser and mapping versions, mapping rationale/confidence, and the engine-compatible observation. Phase 2C keeps original PDF evidence and its derived CSV as different immutable artifacts and records both checksums, extraction tool/profile, benchmark, pages, and human-review state. Phase 2D approved configurations freeze the exact evidence disposition, model run, reviewer, and rule versions; aggregate facts additionally retain every parsed component and contribution. Evaluation reports retain their golden-fixture version, complete proposal, validation outcome, thresholds, and model-run metadata. A checksum proves byte identity, not accounting correctness, completeness, or rights to use a source.

## Deterministic metric semantics

- Canonical definitions and sign conventions are versioned in `domain/metrics.py`.
- Formula policy is documented in `docs/methodology/FINANCIAL_METRICS.md`.
- Calculations expose success, missing-input, zero-denominator, incomparable-input, and not-applicable states.
- Statement checks expose differences and tolerance without changing source facts.

All values use `Decimal`. Missing, zero-denominator, or incomparable cases produce explicit result records; they are never converted to zero, infinity, or fabricated values.

## Deliberate omissions

Role-specific agent implementations, live NSE/BSE adapters, general PDF/HTML/OCR/XBRL extraction, automated profile selection, databases, runtime LLM integration, forecasts, valuation, recommendations, charts, PowerPoint, API, and web UI are deferred. The ruled and explicitly configured aligned profiles are not represented as general filing parsing. A future LLM may suggest document classes, profiles, semantic mappings, and aggregation rules, but deterministic extraction, normalization, reconciliation, provenance, and review gates remain authoritative. Adapter filenames are not created as empty promises. Banks, NBFCs, and insurers require separate future sector modules.

The research blueprint's possible IT-services-plus-cement MVP is broader than this assignment. This slice uses only fictional IT-services-shaped records; cement becomes useful after ingestion and financial-statement foundations are proven.

## Operational and security posture

The demo has no network or credential requirement. Real raw documents, generated output, local databases, environment files, and credentials are ignored by Git. A future source adapter must document rights, retry/caching behavior, immutable storage, versioning, and observability before production use.
