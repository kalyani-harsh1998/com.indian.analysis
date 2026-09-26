"""Tests for controlled financial-fact parsing and field-level lineage."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from indian_company_analysis.__main__ import main
from indian_company_analysis.data.ingestion.local_intake import ImmutableRawDocumentStore
from indian_company_analysis.data.ingestion.manifest_catalog import LocalManifestCatalog
from indian_company_analysis.data.ingestion.models import (
    LocalDocumentIntakeRequest,
    RawDocumentManifest,
)
from indian_company_analysis.data.normalization.csv_parser import ControlledCsvFinancialParser
from indian_company_analysis.data.normalization.models import (
    MetricLabelMapping,
    MetricMappingSet,
    NormalizedFactBatch,
)
from indian_company_analysis.domain.enums import (
    ConfidenceLevel,
    DocumentType,
    LicenceCategory,
    SourceKind,
)
from indian_company_analysis.domain.metrics import MetricId


def _mapping_set() -> MetricMappingSet:
    path = Path("tests/fixtures/mappings/fictional_annual_report.json")
    return MetricMappingSet.model_validate_json(path.read_text(encoding="utf-8"))


def _ingest_csv(tmp_path: Path, source: Path | None = None) -> tuple[RawDocumentManifest, Path]:
    input_path = source or Path("tests/fixtures/documents/fictional_financial_statement.csv")
    request = LocalDocumentIntakeRequest(
        document_id="fictionalco-fy25-financial-statement",
        company_id="fictionalco",
        document_type=DocumentType.ANNUAL_REPORT,
        source_kind=SourceKind.SYNTHETIC,
        source_organization="Synthetic test fixture",
        source_document="Fictional Co FY25 financial statement",
        source_locator="tests/fixtures/documents/fictional_financial_statement.csv",
        retrieved_at=datetime(2026, 9, 26, tzinfo=UTC),
        licence_category=LicenceCategory.INTERNAL_POC,
        input_path=input_path,
        is_synthetic=True,
    )
    raw_root = tmp_path / "raw"
    return ImmutableRawDocumentStore(raw_root).ingest(request).manifest, raw_root


def test_parser_creates_engine_observations_with_field_lineage(tmp_path: Path) -> None:
    manifest, raw_root = _ingest_csv(tmp_path)
    result = ControlledCsvFinancialParser().parse(manifest, raw_root, _mapping_set())

    assert result.ready_for_analysis is True
    assert result.total_rows == 4
    assert not result.issues
    revenue = result.facts[0]
    assert revenue.reported_label == "Revenue from operations"
    assert revenue.raw_value == "1000"
    assert revenue.observation.metric_id is MetricId.REVENUE
    assert str(revenue.observation.value) == "1000"
    assert revenue.source_locator.page_number == 42
    assert revenue.source_locator.table_id == "profit_and_loss"
    assert result.source_reference.parser_version == "controlled-csv-v1"
    assert result.source_checksum_sha256 == manifest.checksum_sha256


def test_unmapped_label_is_an_explicit_issue(tmp_path: Path) -> None:
    source = tmp_path / "unmapped.csv"
    fixture = Path("tests/fixtures/documents/fictional_financial_statement.csv")
    source.write_text(
        fixture.read_text(encoding="utf-8").replace("Tax expense", "Unknown tax label"),
        encoding="utf-8",
    )
    manifest, raw_root = _ingest_csv(tmp_path, source)
    result = ControlledCsvFinancialParser().parse(manifest, raw_root, _mapping_set())

    assert result.ready_for_analysis is False
    assert len(result.facts) == 3
    assert len(result.issues) == 1
    assert result.issues[0].code == "unmapped_label"
    assert result.issues[0].reported_label == "Unknown tax label"


def test_mapping_cannot_be_applied_to_another_source(tmp_path: Path) -> None:
    manifest, raw_root = _ingest_csv(tmp_path)
    wrong_mapping = _mapping_set().model_copy(update={"source_organization": "Another issuer"})

    with pytest.raises(ValueError, match="source organization"):
        ControlledCsvFinancialParser().parse(manifest, raw_root, wrong_mapping)


def test_duplicate_normalized_mapping_labels_are_rejected() -> None:
    mapping = MetricLabelMapping(
        reported_label="Revenue from operations",
        metric_id=MetricId.REVENUE,
        confidence=ConfidenceLevel.HIGH,
        rationale="Synthetic exact mapping.",
    )
    with pytest.raises(ValidationError, match="duplicate normalized"):
        MetricMappingSet(
            mapping_version="duplicate-test",
            source_organization="Synthetic test fixture",
            document_type=DocumentType.ANNUAL_REPORT,
            mappings=(
                mapping,
                mapping.model_copy(update={"reported_label": " REVENUE  FROM operations "}),
            ),
        )


def test_parser_rejects_raw_content_that_no_longer_matches_manifest(tmp_path: Path) -> None:
    manifest, raw_root = _ingest_csv(tmp_path)
    stored = raw_root / manifest.stored_relative_path
    stored.chmod(0o644)
    stored.write_text("changed", encoding="utf-8")

    with pytest.raises(ValueError, match="verification failed"):
        ControlledCsvFinancialParser().parse(manifest, raw_root, _mapping_set())


def test_normalize_csv_command_writes_versioned_batch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    manifest, _ = _ingest_csv(tmp_path)
    catalog_root = tmp_path / "interim" / "manifests"
    LocalManifestCatalog(catalog_root).register(manifest)
    output = tmp_path / "normalized.json"
    monkeypatch.setenv("ICA_DATA_DIRECTORY", str(tmp_path))

    exit_code = main(
        [
            "normalize-csv",
            "--manifest",
            str(catalog_root / f"{manifest.document_id}.json"),
            "--mapping",
            "tests/fixtures/mappings/fictional_annual_report.json",
            "--output",
            str(output),
        ]
    )

    result = NormalizedFactBatch.model_validate_json(output.read_text(encoding="utf-8"))
    assert exit_code == 0
    assert result.ready_for_analysis is True
    assert result.total_rows == 4
