"""Tests for the local controlled onboarding evaluation corpus registry."""

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
    AbstentionCandidate,
    DocumentOnboardingProposal,
    EvaluationCorpusEntry,
    ExclusionCandidate,
    LocalEvaluationCorpusCatalog,
    MappingCandidate,
    MetricAggregationCandidate,
    ModelRunProvenance,
    OnboardingEvaluationFixture,
    ProvisionalCorpusEvaluationPolicy,
    ProvisionalCorpusEvaluator,
    provisionally_review_entry,
)
from indian_company_analysis.domain.enums import (
    ConfidenceLevel,
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
    status: Literal[
        "ready_for_ca_review",
        "provisional_internal_review",
        "approved_for_evaluation",
        "rejected",
    ],
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
    if status == "provisional_internal_review":
        return EvaluationCorpusEntry(
            **common,
            fixture=fixture,
            fixture_checksum_sha256=_fixture_checksum(fixture),
            reviewed_by="internal-reviewer@example.test",
            reviewed_at=_REVIEWED_AT,
            review_policy_version="internal-review-v1",
            review_notes=("Internal reviewer checked deterministic extraction and fixture.",),
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


def _empty_proposal(entry: EvaluationCorpusEntry) -> DocumentOnboardingProposal:
    request = entry.onboarding_request
    return DocumentOnboardingProposal(
        proposal_id="registry-schema-empty-proposal-v1",
        request_id=request.request_id,
        document_id=request.document_id,
        extraction_id=request.extraction_id,
        extraction_profile_version=request.extraction_profile_version,
        company_id=request.company_id,
        source_reference_id=request.source_reference_id,
        source_checksum_sha256=request.source_checksum_sha256,
        source_organization=request.source_organization,
        document_type=request.document_type,
        unit=request.unit,
        period=request.period,
        reporting_basis=request.reporting_basis,
        model_run=ModelRunProvenance(
            provider="registry-schema-test-provider",
            model_id="empty-proposal",
            model_version="1",
            prompt_version="onboarding-prompt-v1",
            schema_version="onboarding-proposal-v1",
            generated_at=_REVIEWED_AT,
        ),
    )


def _perfect_proposal(entry: EvaluationCorpusEntry) -> DocumentOnboardingProposal:
    fixture = entry.fixture
    assert fixture is not None
    request = fixture.request
    labels = {row.evidence_id: row.reported_label for row in request.evidence_rows}
    return DocumentOnboardingProposal(
        proposal_id="registry-schema-perfect-proposal-v1",
        request_id=request.request_id,
        document_id=request.document_id,
        extraction_id=request.extraction_id,
        extraction_profile_version=request.extraction_profile_version,
        company_id=request.company_id,
        source_reference_id=request.source_reference_id,
        source_checksum_sha256=request.source_checksum_sha256,
        source_organization=request.source_organization,
        document_type=request.document_type,
        unit=request.unit,
        period=request.period,
        reporting_basis=request.reporting_basis,
        model_run=ModelRunProvenance(
            provider="registry-schema-test-provider",
            model_id="perfect-proposal",
            model_version="1",
            prompt_version="onboarding-prompt-v1",
            schema_version="onboarding-proposal-v1",
            generated_at=_REVIEWED_AT,
        ),
        mappings=tuple(
            MappingCandidate(
                candidate_id=f"mapping-{expected.evidence_id}",
                evidence_id=expected.evidence_id,
                reported_label=labels[expected.evidence_id],
                metric_id=expected.metric_id,
                sign_multiplier=expected.sign_multiplier,
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic golden mapping.",
            )
            for expected in fixture.expected_mappings
        ),
        aggregations=tuple(
            MetricAggregationCandidate(
                candidate_id=f"aggregation-{expected.metric_id.value}",
                metric_id=expected.metric_id,
                components=expected.components,
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic golden aggregation.",
            )
            for expected in fixture.expected_aggregations
        ),
        exclusions=tuple(
            ExclusionCandidate(
                evidence_id=expected.evidence_id,
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic golden exclusion.",
            )
            for expected in fixture.expected_exclusions
        ),
        abstentions=tuple(
            AbstentionCandidate(
                candidate_id=f"abstention-{expected.evidence_id}",
                evidence_id=expected.evidence_id,
                confidence=ConfidenceLevel.LOW,
                rationale="Synthetic golden abstention.",
            )
            for expected in fixture.expected_abstentions
        ),
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


def test_provisional_case_is_available_only_to_the_internal_evaluator(tmp_path: Path) -> None:
    provisional = _entry(status="provisional_internal_review")
    catalog = LocalEvaluationCorpusCatalog(tmp_path / "corpus")
    catalog.register(provisional)

    assert provisional.is_approved_for_evaluation is False
    assert provisional.is_provisionally_reviewed_for_internal_evaluation is True
    assert (
        catalog.get_provisionally_reviewed_for_internal_evaluation(
            entry_id=provisional.entry_id,
            corpus_version=provisional.corpus_version,
        )
        == provisional
    )
    with pytest.raises(ValueError, match="has not received CA approval"):
        catalog.get_approved(
            entry_id=provisional.entry_id,
            corpus_version=provisional.corpus_version,
        )
    with pytest.raises(ValueError, match="only permitted_real"):
        _entry(status="provisional_internal_review", synthetic=True)


def test_provisional_review_creates_a_new_version_only_from_a_candidate(tmp_path: Path) -> None:
    candidate = _entry(status="ready_for_ca_review")
    provisional = provisionally_review_entry(
        candidate,
        corpus_version="provisional-v1",
        reviewed_by="internal-reviewer@example.test",
        reviewed_at=_REVIEWED_AT,
        review_policy_version="internal-review-v1",
        review_notes=("Internal review; this is not CA approval.",),
    )
    catalog = LocalEvaluationCorpusCatalog(tmp_path / "corpus")

    assert candidate.review_status == "ready_for_ca_review"
    assert provisional.corpus_version == "provisional-v1"
    assert provisional.review_status == "provisional_internal_review"
    assert catalog.register(candidate) is True
    assert catalog.register(provisional) is True
    with pytest.raises(ValueError, match="only a ready_for_ca_review"):
        provisionally_review_entry(
            provisional,
            corpus_version="provisional-v2",
            reviewed_by="internal-reviewer@example.test",
            reviewed_at=_REVIEWED_AT,
            review_policy_version="internal-review-v1",
            review_notes=("This must not overwrite or promote an existing review.",),
        )


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


def test_provisional_review_cli_creates_a_new_catalog_version(tmp_path: Path) -> None:
    candidate = _entry(status="ready_for_ca_review")
    candidate_path = tmp_path / "candidate.json"
    catalog_root = tmp_path / "catalog"
    candidate_path.write_text(candidate.model_dump_json(indent=2), encoding="utf-8")

    exit_code = main(
        [
            "provisionally-review-evaluation-corpus",
            "--entry",
            str(candidate_path),
            "--catalog-root",
            str(catalog_root),
            "--corpus-version",
            "provisional-v1",
            "--reviewed-by",
            "internal-reviewer@example.test",
            "--reviewed-at",
            _REVIEWED_AT.isoformat(),
            "--review-policy-version",
            "internal-review-v1",
            "--review-note",
            "Internal review; this is not CA approval.",
        ]
    )

    assert exit_code == 0
    stored = EvaluationCorpusEntry.model_validate_json(
        (catalog_root / candidate.entry_id / "provisional-v1.json").read_text(encoding="utf-8")
    )
    assert stored.review_status == "provisional_internal_review"
    assert stored.corpus_version == "provisional-v1"


def test_approved_corpus_cli_evaluates_only_a_ca_approved_entry(tmp_path: Path) -> None:
    approved = _entry(status="approved_for_evaluation")
    proposal = _empty_proposal(approved)
    catalog_root = tmp_path / "catalog"
    proposal_path = tmp_path / "proposal.json"
    report_path = tmp_path / "report.json"
    LocalEvaluationCorpusCatalog(catalog_root).register(approved)
    proposal_path.write_text(proposal.model_dump_json(indent=2), encoding="utf-8")

    exit_code = main(
        [
            "evaluate-approved-corpus",
            "--catalog-root",
            str(catalog_root),
            "--entry-id",
            approved.entry_id,
            "--corpus-version",
            approved.corpus_version,
            "--proposal",
            str(proposal_path),
            "--evaluated-at",
            _REVIEWED_AT.isoformat(),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 1
    assert '"case_id": "fictional-tax-onboarding"' in report_path.read_text(encoding="utf-8")
    assert '"evaluation_qualification": "ca_approved_real"' in report_path.read_text(
        encoding="utf-8"
    )


def test_provisional_corpus_cli_writes_a_clearly_labelled_internal_report(tmp_path: Path) -> None:
    provisional = _entry(status="provisional_internal_review")
    proposal = _empty_proposal(provisional)
    catalog_root = tmp_path / "catalog"
    proposal_path = tmp_path / "proposal.json"
    report_path = tmp_path / "report.json"
    LocalEvaluationCorpusCatalog(catalog_root).register(provisional)
    proposal_path.write_text(proposal.model_dump_json(indent=2), encoding="utf-8")

    exit_code = main(
        [
            "evaluate-provisional-corpus",
            "--catalog-root",
            str(catalog_root),
            "--entry-id",
            provisional.entry_id,
            "--corpus-version",
            provisional.corpus_version,
            "--proposal",
            str(proposal_path),
            "--evaluated-at",
            _REVIEWED_AT.isoformat(),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 1
    assert '"evaluation_qualification": "provisional_internal_review"' in report_path.read_text(
        encoding="utf-8"
    )


def test_approved_corpus_cli_rejects_a_case_still_waiting_for_ca_review(tmp_path: Path) -> None:
    entry = _entry(status="ready_for_ca_review")
    proposal_path = tmp_path / "proposal.json"
    catalog_root = tmp_path / "catalog"
    LocalEvaluationCorpusCatalog(catalog_root).register(entry)
    proposal_path.write_text(_empty_proposal(entry).model_dump_json(indent=2), encoding="utf-8")

    with pytest.raises(ValueError, match="has not received CA approval"):
        main(
            [
                "evaluate-approved-corpus",
                "--catalog-root",
                str(catalog_root),
                "--entry-id",
                entry.entry_id,
                "--corpus-version",
                entry.corpus_version,
                "--proposal",
                str(proposal_path),
            ]
        )


def test_provisional_corpus_evaluator_passes_internal_policy_but_blocks_live_models() -> None:
    provisional = _entry(status="provisional_internal_review")

    report = ProvisionalCorpusEvaluator().evaluate(
        (provisional,),
        (_perfect_proposal(provisional),),
        run_id="provisional-summary-v1",
        policy=ProvisionalCorpusEvaluationPolicy(
            policy_version="internal-summary-v1",
            minimum_case_count=1,
            minimum_distinct_company_count=1,
            minimum_pass_rate="1",
            maximum_failed_case_count=0,
        ),
        evaluated_at=_REVIEWED_AT,
    )

    assert report.internal_gate_passed is True
    assert report.passed_case_count == 1
    assert report.failed_case_count == 0
    assert str(report.pass_rate) == "1.000000"
    assert report.live_model_eligible is False
    assert report.live_model_blockers == (
        "provisional internal review cannot authorize a live model",
    )


def test_provisional_corpus_evaluator_reports_failed_cases_against_policy() -> None:
    provisional = _entry(status="provisional_internal_review")

    report = ProvisionalCorpusEvaluator().evaluate(
        (provisional,),
        (_empty_proposal(provisional),),
        run_id="provisional-summary-failure-v1",
        policy=ProvisionalCorpusEvaluationPolicy(
            policy_version="internal-summary-v1",
            minimum_case_count=1,
            minimum_distinct_company_count=1,
            minimum_pass_rate="1",
            maximum_failed_case_count=0,
        ),
        evaluated_at=_REVIEWED_AT,
    )

    assert report.internal_gate_passed is False
    assert report.failed_case_count == 1
    assert "pass rate 0.000000 is below required 1" in report.internal_failure_reasons
    assert "failed case count 1 exceeds permitted 0" in report.internal_failure_reasons


def test_provisional_corpus_summary_cli_persists_an_internal_only_report(tmp_path: Path) -> None:
    provisional = _entry(status="provisional_internal_review")
    catalog_root = tmp_path / "catalog"
    proposal_path = tmp_path / "proposal.json"
    report_path = tmp_path / "summary.json"
    LocalEvaluationCorpusCatalog(catalog_root).register(provisional)
    proposal_path.write_text(
        _perfect_proposal(provisional).model_dump_json(indent=2), encoding="utf-8"
    )

    exit_code = main(
        [
            "evaluate-provisional-corpus-set",
            "--catalog-root",
            str(catalog_root),
            "--entry-id",
            provisional.entry_id,
            "--corpus-version",
            provisional.corpus_version,
            "--proposal",
            str(proposal_path),
            "--run-id",
            "provisional-summary-cli-v1",
            "--policy-version",
            "internal-summary-v1",
            "--evaluated-at",
            _REVIEWED_AT.isoformat(),
            "--output",
            str(report_path),
        ]
    )

    assert exit_code == 0
    persisted = report_path.read_text(encoding="utf-8")
    assert '"internal_gate_passed": true' in persisted
    assert '"live_model_eligible": false' in persisted
