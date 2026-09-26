"""Tests for deterministic, immutable local raw-document intake."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from indian_company_analysis.data.ingestion.local_intake import (
    ImmutableRawDocumentStore,
    sha256_file,
)
from indian_company_analysis.data.ingestion.manifest_catalog import LocalManifestCatalog
from indian_company_analysis.data.ingestion.models import LocalDocumentIntakeRequest
from indian_company_analysis.data.ingestion.verification import verify_raw_document
from indian_company_analysis.domain.enums import DocumentType, LicenceCategory, SourceKind


def intake_request(input_path: Path) -> LocalDocumentIntakeRequest:
    return LocalDocumentIntakeRequest(
        document_id="fictionalco-fy25-annual-report",
        company_id="fictionalco",
        document_type=DocumentType.ANNUAL_REPORT,
        source_kind=SourceKind.SYNTHETIC,
        source_organization="Synthetic test fixture",
        source_document="Fictional Co FY25 annual report",
        source_locator="tests/fixtures/documents/fictional_annual_report.txt",
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        licence_category=LicenceCategory.INTERNAL_POC,
        input_path=input_path,
        is_synthetic=True,
    )


def test_intake_copies_content_by_checksum_without_changing_source(tmp_path: Path) -> None:
    source = Path("tests/fixtures/documents/fictional_annual_report.txt")
    source_before = source.read_bytes()
    result = ImmutableRawDocumentStore(tmp_path / "raw").ingest(intake_request(source))

    stored = tmp_path / "raw" / result.manifest.stored_relative_path
    assert result.storage_created is True
    assert source.read_bytes() == source_before
    assert stored.read_bytes() == source_before
    assert result.manifest.checksum_sha256 == sha256_file(source)
    assert result.manifest.source_reference.checksum_sha256 == sha256_file(source)
    assert result.manifest.source_reference.is_synthetic is True
    assert verify_raw_document(result.manifest, tmp_path / "raw").valid is True


def test_reintake_reuses_identical_content_and_catalog_rejects_conflicts(tmp_path: Path) -> None:
    source = Path("tests/fixtures/documents/fictional_annual_report.txt")
    store = ImmutableRawDocumentStore(tmp_path / "raw")
    first = store.ingest(intake_request(source))
    second = store.ingest(intake_request(source))
    catalog = LocalManifestCatalog(tmp_path / "catalog")

    assert second.storage_created is False
    assert catalog.register(first.manifest) is True
    assert catalog.register(first.manifest) is False
    with pytest.raises(ValueError, match="different manifest"):
        catalog.register(second.manifest.model_copy(update={"byte_size": 1}))


def test_verification_detects_tampered_raw_document(tmp_path: Path) -> None:
    source = Path("tests/fixtures/documents/fictional_annual_report.txt")
    raw_root = tmp_path / "raw"
    result = ImmutableRawDocumentStore(raw_root).ingest(intake_request(source))
    stored = raw_root / result.manifest.stored_relative_path
    stored.chmod(0o644)
    stored.write_text("tampered", encoding="utf-8")

    verification = verify_raw_document(result.manifest, raw_root)
    assert verification.valid is False
    assert "byte size" in verification.message or "checksum" in verification.message
