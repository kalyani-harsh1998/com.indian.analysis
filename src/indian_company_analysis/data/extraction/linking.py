"""Verification and immutable linkage for source PDFs and derived extraction artifacts."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from indian_company_analysis.data.extraction.models import (
    DocumentExtractionLink,
    ExtractionBenchmarkResult,
    ExtractionLinkVerificationResult,
    PdfTableExtractionResult,
)
from indian_company_analysis.data.extraction.serialization import extraction_to_controlled_csv
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document
from indian_company_analysis.domain.enums import DocumentType, ExtractionReviewStatus


class ExtractionLinker:
    """Create a checksum-bound relationship after verifying both immutable artifacts."""

    def __init__(self, raw_root: Path) -> None:
        self._raw_root = raw_root

    def link(
        self,
        *,
        source_manifest: RawDocumentManifest,
        extraction_manifest: RawDocumentManifest,
        extraction_result: PdfTableExtractionResult,
        benchmark: ExtractionBenchmarkResult,
        extracted_at: datetime,
        review_status: ExtractionReviewStatus = ExtractionReviewStatus.UNREVIEWED,
        reviewed_by: str | None = None,
        reviewed_at: datetime | None = None,
    ) -> DocumentExtractionLink:
        self._validate_manifests(source_manifest, extraction_manifest)
        if extraction_result.source_document_id != source_manifest.document_id:
            raise ValueError("extraction result references a different source document")
        if extraction_result.source_checksum_sha256 != source_manifest.checksum_sha256:
            raise ValueError("extraction result references a different source checksum")
        if benchmark.extraction_id != extraction_result.extraction_id:
            raise ValueError("benchmark references a different extraction")
        if benchmark.actual_row_count != len(extraction_result.rows):
            raise ValueError("benchmark row count does not match the extraction result")
        if review_status is ExtractionReviewStatus.REVIEWED and (
            not extraction_result.ready_for_review or not benchmark.passed
        ):
            raise ValueError("an accepted review requires a review-ready, passing extraction")
        expected_csv = extraction_to_controlled_csv(
            extraction_result,
            company_id=source_manifest.company_id,
        ).encode("utf-8")
        extraction_path = self._raw_root / extraction_manifest.stored_relative_path
        if extraction_path.read_bytes() != expected_csv:
            raise ValueError("derived CSV bytes do not match the extraction result")

        return DocumentExtractionLink(
            extraction_id=extraction_result.extraction_id,
            source_document_id=source_manifest.document_id,
            source_document_type=source_manifest.document_type,
            source_checksum_sha256=source_manifest.checksum_sha256,
            extraction_document_id=extraction_manifest.document_id,
            extraction_checksum_sha256=extraction_manifest.checksum_sha256,
            extraction_tool=extraction_result.extraction_tool,
            extraction_tool_version=extraction_result.extraction_tool_version,
            profile_version=extraction_result.profile_version,
            source_pages=(extraction_result.spec.page_number,),
            extracted_at=extracted_at,
            benchmark=benchmark,
            review_status=review_status,
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
        )

    def _validate_manifests(
        self,
        source_manifest: RawDocumentManifest,
        extraction_manifest: RawDocumentManifest,
    ) -> None:
        for label, manifest in (
            ("source", source_manifest),
            ("extraction", extraction_manifest),
        ):
            verification = verify_raw_document(manifest, self._raw_root)
            if not verification.valid:
                raise ValueError(f"{label} verification failed: {verification.message}")
        if source_manifest.content_type != "application/pdf":
            raise ValueError("source extraction manifest must describe an application/pdf")
        if extraction_manifest.content_type != "text/csv":
            raise ValueError("derived extraction manifest must describe text/csv")
        if extraction_manifest.document_type is not DocumentType.CONTROLLED_EXTRACTION:
            raise ValueError("derived CSV must use the controlled_extraction document type")
        if source_manifest.company_id != extraction_manifest.company_id:
            raise ValueError("source and extraction manifests must use the same company_id")


def verify_extraction_link(
    link: DocumentExtractionLink,
    source_manifest: RawDocumentManifest,
    extraction_manifest: RawDocumentManifest,
    raw_root: Path,
) -> ExtractionLinkVerificationResult:
    """Re-verify artifact bytes and every identity recorded by an extraction link."""

    try:
        ExtractionLinker(raw_root)._validate_manifests(source_manifest, extraction_manifest)
    except ValueError as error:
        return ExtractionLinkVerificationResult(
            extraction_id=link.extraction_id,
            valid=False,
            message=str(error),
        )
    expected = (
        link.source_document_id,
        link.source_checksum_sha256,
        link.extraction_document_id,
        link.extraction_checksum_sha256,
        link.source_document_type,
    )
    actual = (
        source_manifest.document_id,
        source_manifest.checksum_sha256,
        extraction_manifest.document_id,
        extraction_manifest.checksum_sha256,
        source_manifest.document_type,
    )
    if expected != actual:
        return ExtractionLinkVerificationResult(
            extraction_id=link.extraction_id,
            valid=False,
            message="extraction link identity does not match the supplied manifests",
        )
    return ExtractionLinkVerificationResult(
        extraction_id=link.extraction_id,
        valid=True,
        message="source PDF and derived extraction match their cryptographic link",
    )
