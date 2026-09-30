"""Tests for the local, CA-reviewed onboarding evaluation corpus registry."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

import pytest

from indian_company_analysis.__main__ import main
from indian_company_analysis.data.extraction.models import (
    DocumentExtractionLink,
    ExtractionBenchmarkResult,
)
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.onboarding import (
    EvaluationCorpusEntry,
    LocalEvaluationCorpusCatalog,
    OnboardingEvaluationFixture,
)
from indian_company_analysis.domain.enums import (
    ExtractionReviewStatus,
    LicenceCategory,
    SourceKind,
)
from indian_company_analysis.domain.models import SourceReference

_REVIEWED_AT = datetime(2026, 9, 30, 10, 0, tzinfo=UTC)


def _fixture() -> OnboardingEvaluationFixture:
    path = Path("tests/fixtures/evaluations/fictional_tax_onboarding.json")
    return OnboardingEvaluationFixture.model_validate_json(path.read_text(encoding="utf-8"))


def _fixture_checksum(fixture: OnboardingEvaluationFixture) -> str:
    serialized = json.dumps(fixture.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _source_manifest(*, synthetic: bool) -> RawDocumentManifest:
    fixture = _fixture()
    return RawDocumentManifest(
        document_id=fixture.request.document_id,
        company_id=fixture.request.company_id,
        document_type=fixture.request.document_type,
        source_reference=SourceReference(
            source_id=fixture.request.source_reference_id,
            source_kind=SourceKind.SYNTHETIC if synthetic else SourceKind.ANNUAL_REPORT,
            source_organization=fixture.request.source_organization,
            source_document="Registry schema test document; not a committed filing",
            locator="local-test-only",
            retrieval_timestamp=_REVIEWED_AT,
            publication_date=date(2026, 5, 1),
            checksum_sha256=fixture.request.source_checksum_sha256,
            is_synthetic=synthetic,
        ),
        licence_category=LicenceCategory.INTERNAL_POC,
        original_filename="not-a-real-filing.pdf",
        content_type="application/pdf",
        byte_size=1,
        checksum_sha256=fixture.request.source_checksum_sha256,
        stored_relative_path="sha256/test.pdf",
        ingested_at=_REVIEWED_AT,
    )


def _link() -> DocumentExtractionLink:
    fixture = _fixture()
    return DocumentExtractionLink(
        extraction_id=fixture.request.extraction_id,
        source_document_id=fixture.request.document_id,
        source_document_type=fixture.request.document_type,
        source_checksum_sha256=fixture.request.source_checksum_sha256,
        extraction_document_id="registry-schema-test-extraction",
        extraction_checksum_sha256="b" * 64,
        extraction_tool="registry-schema-test",
        extraction_tool_version="1",
        profile_version=fixture.request.extraction_profile_version,
        source_pages=(1,),
        extracted_at=_REVIEWED_AT,
        benchmark=ExtractionBenchmarkResult(
            extraction_id=fixture.request.extraction_id,
            benchmark_version="registry-schema-test-v1",
            expected_row_count=1,
            actual_row_count=1,
            matched_row_count=1,
            exact_match_rate="1.000000",
            required_match_rate="1.000000",
            mismatches=(),
            passed=True,
        ),
        review_status=ExtractionReviewStatus.REVIEWED,
        reviewed_by="extraction-reviewer@example.test",
        reviewed_at=_REVIEWED_AT,
    )


def _entry(
    *,
    status: Literal["ready_for_ca_review", "approved_for_evaluation", "rejected"],
    synthetic: bool = False,
) -> EvaluationCorpusEntry:
    fixture = _fixture()
    common = {
        "entry_id": "registry-schema-case-v1",
        "corpus_version": "v1",
        "corpus_scope": "synthetic" if synthetic else "permitted_real",
        "source_manifest": _source_manifest(synthetic=synthetic),
        "extraction_link": _link(),
        "onboarding_request": fixture.request,
        "review_status": status,
    }
    if status == "rejected":
        return EvaluationCorpusEntry(
            **common,
            reviewed_by="ca-reviewer@example.test",
            reviewed_at=_REVIEWED_AT,
            review_policy_version="ca-review-v1",
            review_notes=("The candidate gold standard needs correction.",),
        )
    if status == "ready_for_ca_review":
        return EvaluationCorpusEntry(
            **common,
            fixture=fixture,
            fixture_checksum_sha256=_fixture_checksum(fixture),
        )
    return EvaluationCorpusEntry(
        **common,
        fixture=fixture,
        fixture_checksum_sha256=_fixture_checksum(fixture),
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=_REVIEWED_AT,
        review_policy_version="ca-review-v1",
        review_notes=("CA checked source locations, values, and dispositions.",),
    )


def test_ready_case_retains_candidate_fixture_but_is_not_evaluable(tmp_path: Path) -> None:
    entry = _entry(status="ready_for_ca_review")
    catalog = LocalEvaluationCorpusCatalog(tmp_path / "corpus")

    assert entry.is_approved_for_evaluation is False
    assert catalog.register(entry) is True
    assert catalog.register(entry) is False
    with pytest.raises(ValueError, match="has not received CA approval"):
        catalog.get_approved(entry_id=entry.entry_id, corpus_version=entry.corpus_version)


def test_approved_case_requires_real_permitted_source_and_ca_signoff(tmp_path: Path) -> None:
    approved = _entry(status="approved_for_evaluation")
    catalog = LocalEvaluationCorpusCatalog(tmp_path / "corpus")

    assert approved.is_approved_for_evaluation is True
    assert catalog.register(approved) is True
    assert (
        catalog.get_approved(
            entry_id=approved.entry_id,
            corpus_version=approved.corpus_version,
        )
        == approved
    )
    with pytest.raises(ValueError, match="only permitted_real"):
        _entry(status="approved_for_evaluation", synthetic=True)


def test_registry_rejects_changed_fixture_contents_or_unreviewed_extraction() -> None:
    entry = _entry(status="ready_for_ca_review")
    changed_checksum = entry.model_dump()
    changed_checksum["fixture_checksum_sha256"] = "c" * 64
    with pytest.raises(ValueError, match="fixture checksum"):
        EvaluationCorpusEntry.model_validate(changed_checksum)
    unreviewed_link = entry.model_dump()
    unreviewed_link["extraction_link"] = entry.extraction_link.model_dump()
    unreviewed_link["extraction_link"].update(
        {
            "review_status": ExtractionReviewStatus.UNREVIEWED,
            "reviewed_by": None,
            "reviewed_at": None,
        }
    )
    with pytest.raises(ValueError, match="reviewed extraction"):
        EvaluationCorpusEntry.model_validate(unreviewed_link)


def test_registry_cli_persists_an_append_only_local_case(tmp_path: Path) -> None:
    entry = _entry(status="ready_for_ca_review")
    entry_path = tmp_path / "entry.json"
    catalog_root = tmp_path / "catalog"
    entry_path.write_text(entry.model_dump_json(indent=2), encoding="utf-8")

    exit_code = main(
        [
            "register-evaluation-corpus",
            "--entry",
            str(entry_path),
            "--catalog-root",
            str(catalog_root),
        ]
    )

    assert exit_code == 0
    stored = EvaluationCorpusEntry.model_validate_json(
        (catalog_root / entry.entry_id / f"{entry.corpus_version}.json").read_text(encoding="utf-8")
    )
    assert stored == entry
