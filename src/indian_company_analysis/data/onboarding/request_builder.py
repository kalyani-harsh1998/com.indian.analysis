"""Build model-onboarding requests from verified extraction candidates."""

from indian_company_analysis.data.extraction.models import PdfTableExtractionResult
from indian_company_analysis.data.normalization.models import SourceFactLocator
from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingRequest,
    OnboardingEvidenceRow,
)
from indian_company_analysis.domain.enums import DocumentType
from indian_company_analysis.domain.models import ReportingPeriod


def build_onboarding_request(
    extraction: PdfTableExtractionResult,
    *,
    request_id: str,
    company_id: str,
    source_reference_id: str,
    source_organization: str,
    document_type: DocumentType,
) -> DocumentOnboardingRequest:
    """Convert successful extraction rows into checksummed model input evidence."""

    if not extraction.ready_for_review:
        raise ValueError("onboarding requires an extraction result that is ready for review")

    spec = extraction.spec
    return DocumentOnboardingRequest(
        request_id=request_id,
        document_id=extraction.source_document_id,
        company_id=company_id,
        source_reference_id=source_reference_id,
        source_checksum_sha256=extraction.source_checksum_sha256,
        source_organization=source_organization,
        document_type=document_type,
        unit=spec.unit,
        period=ReportingPeriod(
            label=spec.period_label,
            period_type=spec.period_type,
            start_date=spec.period_start_date,
            end_date=spec.period_end_date,
        ),
        reporting_basis=spec.reporting_basis,
        evidence_rows=tuple(
            OnboardingEvidenceRow(
                evidence_id=f"row-{row.page_number}-{row.row_number}",
                source_locator=SourceFactLocator(
                    page_number=row.page_number,
                    table_id=row.table_id,
                    row_number=row.row_number,
                    column_name=row.column_name,
                ),
                reported_label=row.reported_label,
                raw_value=row.raw_value,
            )
            for row in extraction.rows
        ),
    )
