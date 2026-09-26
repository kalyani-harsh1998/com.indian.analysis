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

In a future Phase 2 slice, an LLM may generate a candidate mapping set and candidate aggregation rules for unfamiliar terminology. The candidate must use the same strict schema and retain its model/prompt provenance. It is not an approved mapping merely because the model reports high confidence. Deterministic checks must confirm that every input row exists at the cited locator, periods/units/bases agree, no source row is consumed twice, and applicable statement reconciliations pass. The configured review policy then records acceptance, rejection, or required human review and issues a new approved mapping version.

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

## Lineage retained for every fact

Each normalized fact carries the source-document checksum, document and source IDs, original reported label and value, page/table/row/column locator, canonical metric, reporting period and basis, parser version, mapping version, mapping method, mapping confidence, and source reference. Linked facts additionally carry the extraction ID, derived CSV document ID, and derived CSV checksum. The batch retains every rejected row as a structured issue and every review or benchmark restriction as an analysis blocker.
