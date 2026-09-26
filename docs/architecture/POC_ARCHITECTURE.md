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
manually supplied local document
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
controlled CSV parser + versioned exact-label mapping
        |
        v
normalized observations + field lineage + explicit issues
```

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

The fixture source is explicitly `synthetic`; its fictional values are not representations of Infosys or its peers. Phase 2A manifests retain checksums, publication/retrieval timestamps, document locators, parser version where relevant, and licensing classification. Phase 2B normalized facts additionally retain the original label/value, field locator, parser and mapping versions, mapping rationale/confidence, and the engine-compatible observation. A checksum proves byte identity, not accounting correctness, completeness, or rights to use a source.

## Deterministic metric semantics

- Canonical definitions and sign conventions are versioned in `domain/metrics.py`.
- Formula policy is documented in `docs/methodology/FINANCIAL_METRICS.md`.
- Calculations expose success, missing-input, zero-denominator, incomparable-input, and not-applicable states.
- Statement checks expose differences and tolerance without changing source facts.

All values use `Decimal`. Missing, zero-denominator, or incomparable cases produce explicit result records; they are never converted to zero, infinity, or fabricated values.

## Deliberate omissions

Role-specific agent implementations, live NSE/BSE adapters, PDF/HTML/OCR/XBRL extraction, automated normalization, databases, LLMs, forecasts, valuation, recommendations, charts, PowerPoint, API, and web UI are deferred. The controlled CSV bridge is not represented as automatic filing parsing. Adapter filenames are not created as empty promises. Banks, NBFCs, and insurers require separate future sector modules.

The research blueprint's possible IT-services-plus-cement MVP is broader than this assignment. This slice uses only fictional IT-services-shaped records; cement becomes useful after ingestion and financial-statement foundations are proven.

## Operational and security posture

The demo has no network or credential requirement. Real raw documents, generated output, local databases, environment files, and credentials are ignored by Git. A future source adapter must document rights, retry/caching behavior, immutable storage, versioning, and observability before production use.
