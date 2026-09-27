"""Coordinate-based extraction for borderless, visually aligned financial statements."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import pdfplumber

from indian_company_analysis.data.extraction.models import (
    AlignedPdfTableExtractionSpec,
    ExtractedTableRow,
    PdfTableExtractionResult,
)
from indian_company_analysis.data.extraction.serialization import (
    extraction_to_controlled_csv,
)
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document

_FINANCIAL_VALUE = re.compile(r"^(?:\(?-?[0-9][0-9,]*(?:\.[0-9]+)?\)?|[-–—])$")


@dataclass(frozen=True, slots=True)
class _PositionedWord:
    text: str
    x0: Decimal
    x1: Decimal
    top: Decimal

    @property
    def center_x(self) -> Decimal:
        return (self.x0 + self.x1) / Decimal("2")


class AlignedPdfStatementExtractor:
    """Extract one configured period column using PDF word coordinates."""

    tool_name = "pdfplumber"

    @staticmethod
    def to_controlled_csv(
        result: PdfTableExtractionResult,
        *,
        company_id: str,
    ) -> str:
        return extraction_to_controlled_csv(result, company_id=company_id)

    def extract(
        self,
        manifest: RawDocumentManifest,
        raw_root: Path,
        spec: AlignedPdfTableExtractionSpec,
    ) -> PdfTableExtractionResult:
        verification = verify_raw_document(manifest, raw_root)
        if not verification.valid:
            raise ValueError(f"source PDF verification failed: {verification.message}")
        if manifest.content_type != "application/pdf":
            raise ValueError("aligned PDF extractor accepts only application/pdf manifests")

        stored_path = raw_root / manifest.stored_relative_path
        with pdfplumber.open(stored_path) as pdf:
            if spec.page_number > len(pdf.pages):
                raise ValueError("extraction page does not exist in the source PDF")
            raw_words = pdf.pages[spec.page_number - 1].extract_words(
                use_text_flow=False,
                keep_blank_chars=False,
            )

        words = tuple(
            _PositionedWord(
                text=str(word["text"]),
                x0=Decimal(str(word["x0"])),
                x1=Decimal(str(word["x1"])),
                top=Decimal(str(word["top"])),
            )
            for word in raw_words
            if spec.data_top <= Decimal(str(word["top"])) <= spec.data_bottom
        )
        rows, issues = self._extract_rows(words, spec)
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

    @classmethod
    def _extract_rows(
        cls,
        words: tuple[_PositionedWord, ...],
        spec: AlignedPdfTableExtractionSpec,
    ) -> tuple[list[ExtractedTableRow], list[str]]:
        lines = cls._group_lines(words, spec.line_tolerance)
        rows: list[ExtractedTableRow] = []
        issues: list[str] = []
        for line in lines:
            label = cls._join_column(line, spec.label_x0, spec.label_x1)
            raw_value = cls._join_column(line, spec.value_x0, spec.value_x1)
            if not raw_value:
                continue
            if not label:
                issues.append(f"value {raw_value!r} at top {line[0].top} has no row label")
                continue
            if not _FINANCIAL_VALUE.fullmatch(raw_value):
                issues.append(
                    f"value {raw_value!r} for label {label!r} is not a supported numeric cell"
                )
                continue
            rows.append(
                ExtractedTableRow(
                    page_number=spec.page_number,
                    table_id=spec.table_id,
                    row_number=len(rows) + 1,
                    column_name=spec.value_column_name,
                    reported_label=label,
                    raw_value=raw_value,
                )
            )
        if not rows and not issues:
            issues.append("no aligned label/value rows were found in the configured region")
        return rows, issues

    @staticmethod
    def _group_lines(
        words: tuple[_PositionedWord, ...], tolerance: Decimal
    ) -> list[list[_PositionedWord]]:
        lines: list[list[_PositionedWord]] = []
        for word in sorted(words, key=lambda item: (item.top, item.x0)):
            if not lines or abs(word.top - lines[-1][0].top) > tolerance:
                lines.append([word])
            else:
                lines[-1].append(word)
        return lines

    @staticmethod
    def _join_column(words: list[_PositionedWord], left: Decimal, right: Decimal) -> str:
        selected = [word for word in words if left <= word.center_x <= right]
        return " ".join(word.text for word in sorted(selected, key=lambda item: item.x0))
