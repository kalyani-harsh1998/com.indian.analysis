# Instructions for coding agents

## Start here

Before substantial work, read `docs/PROJECT_CONTEXT.md`, this file, and the relevant documents in `plans/` and `research/`. Check Git status and preserve unrelated work. Keep changes small and reviewable.

## Non-negotiable engineering rules

- Preserve provenance for every material input and output. A value without evidence is invalid.
- Keep `data/raw/` immutable. Never edit or overwrite a retrieved source; add a new version with its checksum and timestamps.
- Put external access behind replaceable source adapters. Do not couple analysis to a website, vendor, or orchestration framework.
- Keep financial calculations deterministic, independently testable, and outside prompts or agent narratives.
- Explicitly separate reported, calculated, estimated, forecast, management-guidance, and analyst-hypothesis values.
- Explicitly label synthetic and demo data. Never present it as company evidence.
- Do not make unsupported financial claims. Carry sources, dates, reporting basis, definitions, limitations, and confidence into findings.
- During the POC, do not add paid APIs, questionable scraping, cloud-account requirements, live trading, or an OpenAI API dependency.
- Never commit secrets, API keys, credentials, confidential data, or licensed source documents. Keep local raw evidence and generated outputs ignored.
- Add tests for financial formulas, transformations, validation, provenance, and failure behavior.
- Run `pytest`, `ruff check .`, `ruff format --check .`, and `mypy src tests` before committing.
- Record material architectural decisions in `docs/architecture/DECISIONS.md`; create it when the first such decision is accepted.

## Architecture boundaries

- `domain`: typed business concepts and classifications; no I/O.
- `data`: source contracts, ingestion, normalization, provenance, and local storage.
- `analytics`: deterministic historical calculations and sector rules.
- `forecasting`: explicit drivers, scenarios, validation, and backtests.
- `agents`: capability selection and orchestration, never hidden arithmetic.
- `workflows`: execution order and run manifests.
- `reporting`: citations, charts, and renderers from validated structured results.

Prefer protocols and plain Python composition until evidence justifies an agent framework. Do not implement banks, NBFCs, or insurers using the non-financial model.

## Data discipline

Default to the latest revised exchange filing, reconcile it to audited reports, and retain every prior version. Never mix consolidated with standalone values or mismatched periods. Preserve source organization, document, locator, retrieval time, parser version, restatement state, and validation confidence where applicable.

## Product guardrails

Public-data management recommendations are outside-in hypotheses, not definitive instructions. Do not imply affiliation with named professional-services firms or reproduce proprietary material. Do not describe output as investment, audit, tax, legal, or regulated financial advice.
