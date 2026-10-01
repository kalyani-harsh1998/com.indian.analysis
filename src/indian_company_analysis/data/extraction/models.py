"""Strict records for PDF extraction, accuracy benchmarks, and artifact lineage."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import Field, model_validator

from indian_company_analysis.domain.enums import (
    DocumentType,
    ExtractionReviewStatus,
    PeriodType,
    ReportingBasis,
)
from indian_company_analysis.domain.models import DomainModel


class PdfTableExtractionSpec(DomainModel):
    """Explicit instructions for one simple ruled, two-column PDF table."""

    extraction_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    profile_version: str = Field(default="ruled-two-column-v1", min_length=1)
    page_number: int = Field(ge=1)
    table_id: str = Field(min_length=1)
    label_column_name: str = Field(min_length=1)
    value_column_name: str = Field(min_length=1)
    unit: str = Field(min_length=1)
    period_label: str = Field(min_length=1)
    period_type: PeriodType
    period_start_date: date
    period_end_date: date
    reporting_basis: ReportingBasis

    @model_validator(mode="after")
    def dates_are_ordered(self) -> PdfTableExtractionSpec:
        if self.period_end_date < self.period_start_date:
            raise ValueError("extraction period end date must not precede start date")
        return self


class AlignedPdfTableExtractionSpec(PdfTableExtractionSpec):
    """Coordinates for one value column in a borderless aligned statement."""

    profile_version: str = Field(default="aligned-single-period-v1", min_length=1)
    data_top: Decimal = Field(ge=0)
    data_bottom: Decimal = Field(gt=0)
    label_x0: Decimal = Field(ge=0)
    label_x1: Decimal = Field(gt=0)
    value_x0: Decimal = Field(ge=0)
    value_x1: Decimal = Field(gt=0)
    line_tolerance: Decimal = Field(default=Decimal("2"), gt=0, le=10)
    word_x_tolerance: Decimal = Field(default=Decimal("3"), gt=0, le=10)

    @model_validator(mode="after")
    def coordinates_are_ordered(self) -> AlignedPdfTableExtractionSpec:
        if self.data_bottom <= self.data_top:
            raise ValueError("data_bottom must be below data_top")
        if self.label_x1 <= self.label_x0 or self.value_x1 <= self.value_x0:
            raise ValueError("column right boundaries must exceed left boundaries")
        if self.label_x1 >= self.value_x0:
            raise ValueError("label and value columns must not overlap")
        return self


class ExtractedTableRow(DomainModel):
    page_number: int = Field(ge=1)
    table_id: str = Field(min_length=1)
    row_number: int = Field(ge=1)
    column_name: str = Field(min_length=1)
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)


class PdfTableExtractionResult(DomainModel):
    extraction_id: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extraction_tool: str = Field(min_length=1)
    extraction_tool_version: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    spec: AlignedPdfTableExtractionSpec | PdfTableExtractionSpec
    rows: tuple[ExtractedTableRow, ...]
    issues: tuple[str, ...]
    ready_for_review: bool

    @model_validator(mode="after")
    def readiness_matches_issues(self) -> PdfTableExtractionResult:
        if self.ready_for_review != (bool(self.rows) and not self.issues):
            raise ValueError("ready_for_review requires extracted rows and no extraction issues")
        if self.extraction_id != self.spec.extraction_id:
            raise ValueError("result extraction_id must match the extraction specification")
        return self


class ExpectedExtractionRow(DomainModel):
    row_number: int = Field(ge=1)
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)


class ExtractionBenchmarkFixture(DomainModel):
    """Versioned human-prepared golden rows for one extraction profile."""

    benchmark_version: str = Field(min_length=1)
    required_match_rate: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    expected_rows: tuple[ExpectedExtractionRow, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def row_numbers_are_unique(self) -> ExtractionBenchmarkFixture:
        row_numbers = [row.row_number for row in self.expected_rows]
        if len(row_numbers) != len(set(row_numbers)):
            raise ValueError("benchmark fixture contains duplicate expected row numbers")
        return self


class ExtractionBenchmarkResult(DomainModel):
    extraction_id: str = Field(min_length=1)
    benchmark_version: str = Field(min_length=1)
    expected_row_count: int = Field(ge=1)
    actual_row_count: int = Field(ge=0)
    matched_row_count: int = Field(ge=0)
    exact_match_rate: Decimal = Field(ge=0, le=1)
    required_match_rate: Decimal = Field(ge=0, le=1)
    mismatches: tuple[str, ...]
    passed: bool

    @model_validator(mode="after")
    def benchmark_math_is_consistent(self) -> ExtractionBenchmarkResult:
        comparison_count = max(self.expected_row_count, self.actual_row_count)
        expected_rate = Decimal(self.matched_row_count) / Decimal(comparison_count)
        if self.exact_match_rate != expected_rate.quantize(Decimal("0.000001")):
            raise ValueError("exact_match_rate does not match benchmark counts")
        if self.passed != (self.exact_match_rate >= self.required_match_rate):
            raise ValueError("benchmark pass status does not match the required rate")
        return self


class DocumentExtractionLink(DomainModel):
    """Cryptographic relationship between one source PDF and one derived CSV."""

    extraction_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    source_document_id: str = Field(min_length=1)
    source_document_type: DocumentType
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extraction_document_id: str = Field(min_length=1)
    extraction_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extraction_tool: str = Field(min_length=1)
    extraction_tool_version: str = Field(min_length=1)
    profile_version: str = Field(min_length=1)
    source_pages: tuple[int, ...] = Field(min_length=1)
    extracted_at: datetime
    benchmark: ExtractionBenchmarkResult
    review_status: ExtractionReviewStatus = ExtractionReviewStatus.UNREVIEWED
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None

    @model_validator(mode="after")
    def review_and_identity_are_consistent(self) -> DocumentExtractionLink:
        if self.source_document_id == self.extraction_document_id:
            raise ValueError("source and extraction document IDs must be different")
        if len(self.source_pages) != len(set(self.source_pages)) or any(
            page < 1 for page in self.source_pages
        ):
            raise ValueError("source_pages must contain unique positive page numbers")
        has_review_metadata = self.reviewed_by is not None and self.reviewed_at is not None
        if self.review_status is ExtractionReviewStatus.UNREVIEWED and (
            self.reviewed_by is not None or self.reviewed_at is not None
        ):
            raise ValueError("unreviewed extraction links cannot carry review metadata")
        if self.review_status is not ExtractionReviewStatus.UNREVIEWED and not has_review_metadata:
            raise ValueError("reviewed or rejected extraction links require reviewer and time")
        if self.benchmark.extraction_id != self.extraction_id:
            raise ValueError("benchmark extraction_id must match the extraction link")
        return self


class ExtractionLinkVerificationResult(DomainModel):
    extraction_id: str
    valid: bool
    message: str
