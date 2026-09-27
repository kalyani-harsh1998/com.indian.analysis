"""Narrow PDF extractor for simple ruled, two-column tables."""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from indian_company_analysis.data.extraction.models import (
    ExtractedTableRow,
    PdfTableExtractionResult,
    PdfTableExtractionSpec,
)
from indian_company_analysis.data.extraction.serialization import (
    extraction_to_controlled_csv,
)
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document


class RuledPdfTableExtractor:
    """Extract one explicitly located table with visible cell borders."""

    tool_name = "pdfplumber"

    def extract(
        self,
        manifest: RawDocumentManifest,
        raw_root: Path,
        spec: PdfTableExtractionSpec,
    ) -> PdfTableExtractionResult:
        verification = verify_raw_document(manifest, raw_root)
        if not verification.valid:
            raise ValueError(f"source PDF verification failed: {verification.message}")
        if manifest.content_type != "application/pdf":
            raise ValueError("ruled PDF extractor accepts only application/pdf manifests")

        stored_path = raw_root / manifest.stored_relative_path
        issues: list[str] = []
        rows: list[ExtractedTableRow] = []
        with pdfplumber.open(stored_path) as pdf:
            if spec.page_number > len(pdf.pages):
                raise ValueError("extraction page does not exist in the source PDF")
            page = pdf.pages[spec.page_number - 1]
            extracted = page.extract_table(
                table_settings={
                    "vertical_strategy": "lines",
                    "horizontal_strategy": "lines",
                }
            )

        if not extracted:
            issues.append("no ruled table was found on the requested page")
        else:
            rows.extend(self._parse_table(extracted, spec, issues))
        return PdfTableExtractionResult(
            extraction_id=spec.extraction_id,
            source_document_id=manifest.document_id,
            source_checksum_sha256=manifest.checksum_sha256,
            extraction_tool=self.tool_name,
            extraction_tool_version=str(pdfplumber.__version__),
            profile_version=spec.profile_version,
            spec=spec,
            rows=tuple(rows),
            issues=tuple(issues),
            ready_for_review=bool(rows) and not issues,
        )

    @staticmethod
    def _parse_table(
        extracted: list[list[str | None]],
        spec: PdfTableExtractionSpec,
        issues: list[str],
    ) -> list[ExtractedTableRow]:
        header = extracted[0]
        if len(header) != 2 or tuple(RuledPdfTableExtractor._clean(cell) for cell in header) != (
            spec.label_column_name,
            spec.value_column_name,
        ):
            issues.append("table header does not match the extraction specification")
            return []

        rows: list[ExtractedTableRow] = []
        for row_number, cells in enumerate(extracted[1:], start=1):
            if len(cells) != 2:
                issues.append(f"table row {row_number} does not contain exactly two cells")
                continue
            label, raw_value = (RuledPdfTableExtractor._clean(cell) for cell in cells)
            if not label or not raw_value:
                issues.append(f"table row {row_number} contains an empty label or value")
                continue
            rows.append(
                ExtractedTableRow(
                    page_number=spec.page_number,
                    table_id=spec.table_id,
                    row_number=row_number,
                    column_name=spec.value_column_name,
                    reported_label=label,
                    raw_value=raw_value,
                )
            )
        return rows

    @staticmethod
    def _clean(value: str | None) -> str:
        return " ".join((value or "").split())

    @staticmethod
    def to_controlled_csv(
        result: PdfTableExtractionResult,
        *,
        company_id: str,
    ) -> str:
        """Serialize a review-ready result to the Phase 2B controlled CSV contract."""

        return extraction_to_controlled_csv(result, company_id=company_id)
