"""Independent verification of immutable raw-document manifests."""

from __future__ import annotations

from pathlib import Path

from indian_company_analysis.data.ingestion.local_intake import sha256_file
from indian_company_analysis.data.ingestion.models import (
    RawDocumentManifest,
    RawDocumentVerificationResult,
)


def verify_raw_document(
    manifest: RawDocumentManifest, raw_root: Path
) -> RawDocumentVerificationResult:
    """Confirm the stored file still exists and exactly matches the manifest."""

    root = raw_root.resolve()
    stored_path = (root / manifest.stored_relative_path).resolve()
    if not stored_path.is_relative_to(root):
        return RawDocumentVerificationResult(
            document_id=manifest.document_id,
            valid=False,
            message="manifest path resolves outside the raw-data root",
        )
    if not stored_path.is_file():
        return RawDocumentVerificationResult(
            document_id=manifest.document_id,
            valid=False,
            message="stored raw document is missing",
        )
    if stored_path.stat().st_size != manifest.byte_size:
        return RawDocumentVerificationResult(
            document_id=manifest.document_id,
            valid=False,
            message="stored raw document byte size differs from the manifest",
        )
    actual_checksum = sha256_file(stored_path)
    if actual_checksum != manifest.checksum_sha256:
        return RawDocumentVerificationResult(
            document_id=manifest.document_id,
            valid=False,
            message="stored raw document checksum differs from the manifest",
            actual_checksum_sha256=actual_checksum,
        )
    return RawDocumentVerificationResult(
        document_id=manifest.document_id,
        valid=True,
        message="stored raw document matches its manifest",
        actual_checksum_sha256=actual_checksum,
    )
