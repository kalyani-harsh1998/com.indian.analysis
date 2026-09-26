# POC architecture

## Goal

Establish the smallest end-to-end path that proves typed, source-aware, deterministic analysis can run locally. The POC favors explicit composition over autonomous agents or infrastructure.

```text
synthetic JSON fixture
        |
        v
LocalFileDataSource -> Pydantic validation -> provenance gate
        |                                      |
        +--------------------+-----------------+
                             v
                 CompanyAnalysisWorkflow
                             |
                deterministic ratio functions
                             |
                             v
         AnalysisRunManifest + metric observations
                             |
                             v
                    structured JSON output
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

Each input observation has one or more source-reference IDs. The workflow rejects missing references and unknown IDs before calculation. Derived observations retain the union of their input reference IDs, use `calculated` value classification, and preserve the synthetic source status in the manifest.

The fixture source is explicitly `synthetic`; its fictional values are not representations of Infosys or its peers. Future raw sources should also include checksums, publication/retrieval timestamps, document locators, parser version, and licensing classification as those capabilities are implemented.

## Deterministic metric semantics

- Revenue growth = `(current revenue / prior revenue) - 1`.
- Operating margin = `operating profit / revenue`.
- CFO-to-PAT conversion = `cash flow from operations / profit after tax`.

All values use `Decimal`. A missing operand or zero denominator returns `None`; it is never converted to zero or infinity. The workflow omits an unavailable calculated observation rather than fabricating a value.

## Deliberate omissions

Role-specific agent implementations, live NSE/BSE adapters, parsing, normalization pipelines, databases, LLMs, forecasts, valuation, recommendations, charts, PowerPoint, API, and web UI are deferred. Adapter filenames are not created as empty promises. Banks, NBFCs, and insurers require separate future sector modules.

The research blueprint's possible IT-services-plus-cement MVP is broader than this assignment. This slice uses only fictional IT-services-shaped records; cement becomes useful after ingestion and financial-statement foundations are proven.

## Operational and security posture

The demo has no network or credential requirement. Real raw documents, generated output, local databases, environment files, and credentials are ignored by Git. A future source adapter must document rights, retry/caching behavior, immutable storage, versioning, and observability before production use.
