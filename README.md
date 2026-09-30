# Indian Listed-Company Analysis

A local-first, source-aware foundation for an agentic research platform covering Indian listed companies. The intended product combines accounting-quality review, performance diagnosis, strategic analysis, value-creation hypotheses, and investor/credit analysis while preserving evidence and uncertainty.

## Current status

This repository is an early proof of concept. The Phase 1 engine loads five years of clearly labelled synthetic IT-services statements, validates provenance and revisions, reconciles core statement equations, calculates documented historical metrics, and writes structured results with explicit failure states. Phase 2A copies a manually supplied local document into immutable checksum-addressed storage and records its provenance and licence metadata. Phase 2B normalizes a verified controlled CSV through an explicit, versioned metric mapping while retaining field-level lineage. Phase 2C adds benchmarked ruled-table and aligned-column PDF profiles and cryptographically links the original PDF to its derived CSV. Phase 2D defines strict provider-neutral proposal and approval records, deterministic signed-sum aggregation, a local approval/rejection workflow, and a review-only cross-filing reuse assessment before persisting facts in a combined verified normalization batch. Approved configurations and reviewer decisions are append-only local artifacts and are source-identity bound; reuse assessments never apply a configuration automatically. Its nominal and adversarial golden-case evaluator measures proposal accuracy, evidence coverage, canonical values, accounting reconciliations, safe abstentions, context mismatches, and unsafe evidence handling while preserving model-run usage metadata. A local evaluation-corpus registry now connects a permitted real filing's manifest, reviewed extraction link, exact fixture checksum, and CA sign-off before that fixture can gate a future live model; the approved-corpus evaluator refuses to run against a candidate or synthetic case. A static adapter and synthetic fixtures test this boundary; no live LLM dependency has been added. It does **not** fetch or scrape live sources, generally parse annual reports or XBRL, forecast, value securities, make recommendations, or generate presentations.

## Architecture

The package separates typed domain objects, replaceable source adapters, deterministic financial calculations, framework-neutral contracts, controlled workflows, and outputs. Numerical truth belongs in deterministic code; future agents may select and explain capabilities but must not become the source of financial calculations.

See [project context](docs/PROJECT_CONTEXT.md), [financial methodology](docs/methodology/FINANCIAL_METRICS.md), [POC architecture](docs/architecture/POC_ARCHITECTURE.md), and the [development roadmap](plans/DEVELOPMENT_ROADMAP.md).

## Repository structure

```text
plans/       Product plans, output specification, roadmap, and open decisions
research/    Source, licensing, and data-strategy research
docs/        Persistent project context and architecture
src/         Python package using a src layout
data/        Local data zones and synthetic demo fixtures
tests/       Unit and integration tests
outputs/     Generated local results (ignored except .gitkeep)
scripts/     Development helper scripts
```

## Requirements and installation

Python 3.12 is required. Both `uv` and a standard virtual environment are supported.

With `uv`:

```bash
uv sync --extra dev
uv run python -m indian_company_analysis demo
```

With `venv` and `pip`:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
python -m indian_company_analysis demo
```

The demo writes `outputs/demo_analysis.json`. It includes reported and superseded observations, adjustments, calculation results, reconciliation results, and the run manifest. Override the paths with `--fixture` and `--output`.

For a manually downloaded, permitted source document, see the [local document-intake guide](docs/methodology/LOCAL_DOCUMENT_INTAKE.md). For the deliberately narrow normalization contract, see [controlled CSV normalization](docs/methodology/NORMALIZED_FACTS.md). The [PDF extraction-lineage guide](docs/methodology/PDF_EXTRACTION_LINEAGE.md) explains the Phase 2C benchmark and human-review gate. The [model-assisted onboarding guide](docs/methodology/MODEL_ASSISTED_ONBOARDING.md) describes the Phase 2D provider boundary, [onboarding proposal evaluation](docs/methodology/ONBOARDING_EVALUATION.md) describes its pre-provider quality gate, [CA-reviewed evaluation corpus registry](docs/methodology/EVALUATION_CORPUS_REGISTRY.md) describes how real cases may enter that gate, [onboarding review workflow](docs/methodology/ONBOARDING_REVIEW_WORKFLOW.md) describes approval and rejection artifacts, and [cross-filing configuration reuse assessment](docs/methodology/ONBOARDING_CONFIGURATION_REUSE.md) describes later-filing comparison. None of these workflows retrieves a source from the internet.

## Validation

```bash
pytest
ruff check .
ruff format --check .
mypy src tests
```

## Data and licensing warning

Raw source documents are local, immutable evidence and are excluded from Git. Public availability does not imply permission to automate collection, retain, transform, train on, display, or redistribute data. Confirm source-specific terms before use. Never commit credentials, licensed documents, or confidential company information.

## Disclaimer

This project is for decision support, research, and education. Its outputs are not investment, audit, tax, legal, or other regulated financial advice. Synthetic demo results are fictional and must not be interpreted as facts about any real company.
