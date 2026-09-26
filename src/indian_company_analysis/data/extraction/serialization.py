"""Deterministic serialization of reviewed extraction candidates."""

import csv
import io

from indian_company_analysis.data.extraction.models import PdfTableExtractionResult

_CONTROLLED_CSV_COLUMNS = (
    "company_id",
    "page_number",
    "table_id",
    "row_number",
    "column_name",
    "reported_label",
    "value",
    "unit",
    "period_label",
    "period_type",
    "period_start_date",
    "period_end_date",
    "reporting_basis",
)


def extraction_to_controlled_csv(
    result: PdfTableExtractionResult,
    *,
    company_id: str,
) -> str:
    """Serialize a review-ready result to the Phase 2B controlled CSV contract."""

    if not result.ready_for_review:
        raise ValueError("cannot serialize an extraction result that is not ready for review")
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=_CONTROLLED_CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    spec = result.spec
    for row in result.rows:
        writer.writerow(
            {
                "company_id": company_id,
                "page_number": row.page_number,
                "table_id": row.table_id,
                "row_number": row.row_number,
                "column_name": row.column_name,
                "reported_label": row.reported_label,
                "value": row.raw_value,
                "unit": spec.unit,
                "period_label": spec.period_label,
                "period_type": spec.period_type,
                "period_start_date": spec.period_start_date,
                "period_end_date": spec.period_end_date,
                "reporting_basis": spec.reporting_basis,
            }
        )
    return output.getvalue()
