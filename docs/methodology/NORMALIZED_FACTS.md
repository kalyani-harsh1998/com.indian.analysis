# Controlled CSV normalization

## Purpose and boundary

Phase 2B converts a verified, row-oriented CSV into canonical `MetricObservation` records that the deterministic financial engine can eventually consume. It is intentionally a controlled bridge, not a PDF, OCR, HTML, or XBRL parser.

The parser never guesses a metric, period, unit, sign, company, or accounting basis. A label must match a versioned mapping exactly after case and whitespace normalization. Rows that are invalid, unmapped, assigned to another company, or duplicates become explicit issues, and the batch is marked not ready for analysis.

Phase 2B can still normalize a CSV directly as its own checksummed source. Phase 2C additionally supports linked normalization where an original PDF remains the cited evidence and the derived CSV has its own checksum in an extraction reference. Linked results remain blocked until their benchmark passes and a human accepts the extraction. See [PDF extraction lineage and review](PDF_EXTRACTION_LINEAGE.md).

## Required CSV columns

The first row must contain all of these column names:

| Column | Meaning |
| --- | --- |
| `company_id` | Internal company identifier; must equal the raw manifest company |
| `page_number` | One-based page in the referenced document |
| `table_id` | Stable name for the source statement or table |
| `row_number` | One-based row within that table |
| `column_name` | Source column heading, such as `FY2025` |
| `reported_label` | Label exactly as reported by the source |
| `value` | Reported numeric value, without commas or currency symbols |
| `unit` | Explicit unit, such as `INR million` |
| `period_label` | Display label, such as `FY2025` |
| `period_type` | `annual` or `quarterly` |
| `period_start_date` | ISO date (`YYYY-MM-DD`) |
| `period_end_date` | ISO date (`YYYY-MM-DD`) |
| `reporting_basis` | `consolidated` or `standalone` |

The parser validates dates and prevents duplicate canonical metrics for the same company, period, and reporting basis within one document.

## Mapping contract

A separate JSON mapping set is scoped to one source organization and document type. It carries a mapping version and one or more reviewed mappings:

```json
{
  "mapping_version": "exampleco-annual-report-v1",
  "source_organization": "Example Co Limited",
  "document_type": "annual_report",
  "mappings": [
    {
      "reported_label": "Revenue from operations",
      "metric_id": "revenue",
      "sign_multiplier": "1",
      "confidence": "high",
      "rationale": "Exact match to the audited statement line."
    }
  ]
}
```

`sign_multiplier` may only be `1` or `-1`. The raw value remains unchanged in lineage while the normalized observation receives the explicit sign transformation. Mapping confidence is not the same as source reliability or audit assurance.

Phase 2D now defines a provider-neutral proposal schema through which a future LLM may suggest a mapping set and aggregation rules for unfamiliar terminology. It retains model/prompt provenance, validates every evidence reference, requires every row to be mapped, aggregated, or explicitly excluded, prevents duplicate row use, and records human approval. It is not an approved mapping merely because the model reports high confidence. Direct approved mappings produce reported facts; approved signed-sum aggregations produce separately typed calculated facts with raw/parsed component values, coefficients, contributions, locators, source identity, rule version, and review lineage. `OnboardingNormalizationWorkflow` re-verifies Phase 2C lineage and persists both types in one batch. See [model-assisted document onboarding](MODEL_ASSISTED_ONBOARDING.md).

Before a future live proposal provider is used, its output can be tested against versioned golden dispositions with deterministic value comparisons and accounting reconciliations. Evaluation reports are audit artifacts, not normalized facts or approvals. See [onboarding proposal evaluation](ONBOARDING_EVALUATION.md).

## Workflow

First ingest the permitted CSV using the Phase 2A `intake` command. Then normalize it using the generated local manifest and a reviewed mapping file:

```bash
uv run python -m indian_company_analysis normalize-csv \
  --manifest data/interim/manifests/exampleco-fy25-controlled-csv.json \
  --mapping /path/to/exampleco-mapping.json
```

The default output is:

```text
data/processed/normalized/<document-id>/<parser-version>--<mapping-version>.json
```

Raw documents, manifests, and normalized outputs are local and ignored by Git. If any row has an issue, the command still writes the complete result for review but returns a non-zero exit status. It refuses to overwrite a different result at the same versioned output path.

For a reviewed model-assisted configuration, use `normalize-onboarding` with the source/extraction manifests, extraction link, onboarding request, and approved configuration. It re-verifies immutable artifact bytes and exact controlled-CSV rows before persisting the combined direct/aggregated batch. Unreviewed or failed extraction links remain visible but block analysis readiness.

## Lineage retained for every fact

Each normalized fact carries the source-document checksum, document and source IDs, original reported label and value, page/table/row/column locator, canonical metric, reporting period and basis, parser version, mapping version, mapping method, mapping confidence, and source reference. Linked facts additionally carry the extraction ID, derived CSV document ID, and derived CSV checksum. The batch retains every rejected row as a structured issue and every review or benchmark restriction as an analysis blocker.
