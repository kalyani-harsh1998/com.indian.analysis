"""Tests for review-only cross-filing onboarding configuration assessments."""

from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from indian_company_analysis.__main__ import main
from indian_company_analysis.data.normalization.models import SourceFactLocator
from indian_company_analysis.data.onboarding import (
    ApprovedOnboardingConfiguration,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    ExclusionCandidate,
    MappingCandidate,
    MetricAggregationCandidate,
    ModelRunProvenance,
    OnboardingEvaluationFixture,
    OnboardingEvidenceRow,
    OnboardingReuseAssessment,
    OnboardingReuseAssessor,
    approve_onboarding_proposal,
)
from indian_company_analysis.domain.enums import ConfidenceLevel, PeriodType
from indian_company_analysis.domain.models import ReportingPeriod

_ASSESSED_AT = datetime(2026, 9, 29, 14, 0, tzinfo=UTC)


def _fixture() -> OnboardingEvaluationFixture:
    path = Path("tests/fixtures/evaluations/fictional_tax_onboarding.json")
    return OnboardingEvaluationFixture.model_validate_json(path.read_text(encoding="utf-8"))


def _configuration() -> ApprovedOnboardingConfiguration:
    fixture = _fixture()
    labels = {row.evidence_id: row.reported_label for row in fixture.request.evidence_rows}
    proposal = DocumentOnboardingProposal(
        proposal_id="fictional-tax-source-proposal",
        request_id=fixture.request.request_id,
        document_id=fixture.request.document_id,
        extraction_id=fixture.request.extraction_id,
        extraction_profile_version=fixture.request.extraction_profile_version,
        company_id=fixture.request.company_id,
        source_reference_id=fixture.request.source_reference_id,
        source_checksum_sha256=fixture.request.source_checksum_sha256,
        source_organization=fixture.request.source_organization,
        document_type=fixture.request.document_type,
        unit=fixture.request.unit,
        period=fixture.request.period,
        reporting_basis=fixture.request.reporting_basis,
        model_run=ModelRunProvenance(
            provider="deterministic-test-provider",
            model_id="static-source-proposal",
            model_version="1",
            prompt_version="onboarding-prompt-v1",
            schema_version="onboarding-proposal-v1",
            generated_at=_ASSESSED_AT,
        ),
        mappings=tuple(
            MappingCandidate(
                candidate_id=f"mapping-{expected.evidence_id}",
                evidence_id=expected.evidence_id,
                reported_label=labels[expected.evidence_id],
                metric_id=expected.metric_id,
                sign_multiplier=expected.sign_multiplier,
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic reviewed mapping.",
            )
            for expected in fixture.expected_mappings
        ),
        aggregations=tuple(
            MetricAggregationCandidate(
                candidate_id=f"aggregation-{expected.metric_id.value}",
                metric_id=expected.metric_id,
                components=expected.components,
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic reviewed aggregation.",
            )
            for expected in fixture.expected_aggregations
        ),
        exclusions=tuple(
            ExclusionCandidate(
                evidence_id=expected.evidence_id,
                confidence=ConfidenceLevel.HIGH,
                rationale="Synthetic reviewed exclusion.",
            )
            for expected in fixture.expected_exclusions
        ),
    )
    return approve_onboarding_proposal(
        fixture.request,
        proposal,
        configuration_version="fictional-tax-source-configuration-v1",
        aggregation_rule_version="aggregation-v1",
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=_ASSESSED_AT,
        approval_policy_version="human-review-v1",
    )


def _new_request(*, profile_version: str = "aligned-single-period-v1") -> DocumentOnboardingRequest:
    source_request = _fixture().request
    rows = tuple(
        row.model_copy(
            update={
                "evidence_id": f"fy2027-{index}",
                "source_locator": row.source_locator.model_copy(update={"row_number": index}),
            }
        )
        for index, row in enumerate(source_request.evidence_rows, start=1)
    )
    exceptional_item = OnboardingEvidenceRow(
        evidence_id="fy2027-7",
        source_locator=SourceFactLocator(
            page_number=301,
            table_id="profit_and_loss",
            row_number=7,
            column_name="FY2027",
        ),
        reported_label="Exceptional item",
        raw_value="(250)",
    )
    return source_request.model_copy(
        update={
            "request_id": "fictionalco-fy2027-reuse-v1",
            "document_id": "fictionalco-fy2027-synthetic-report",
            "extraction_id": "fictionalco-fy2027-profit-loss",
            "extraction_profile_version": profile_version,
            "source_reference_id": "source-fictionalco-fy2027-reuse",
            "source_checksum_sha256": "d" * 64,
            "period": ReportingPeriod(
                label="FY2027",
                period_type=PeriodType.ANNUAL,
                start_date=date(2026, 4, 1),
                end_date=date(2027, 3, 31),
            ),
            "evidence_rows": (*rows, exceptional_item),
        }
    )


def test_reuse_assessment_marks_exact_labels_as_candidates_but_requires_review() -> None:
    assessment = OnboardingReuseAssessor().assess(
        _configuration(),
        _new_request(),
        assessment_id="fictionalco-fy2027-reuse-v1",
        assessed_at=_ASSESSED_AT,
    )

    assert assessment.requires_human_approval is True
    assert assessment.reusable_candidate_count == 5
    assert assessment.review_required_count == 0
    assert {row.reported_label for row in assessment.new_evidence_rows} == {"Exceptional item"}
    assert {item.field_name for item in assessment.context_differences} >= {
        "document_id",
        "period",
        "source_checksum_sha256",
    }


def test_changed_label_or_profile_requires_reviewer_action() -> None:
    target = _new_request()
    changed_row = target.evidence_rows[0].model_copy(
        update={"reported_label": "Revenue from operations and services"}
    )
    changed_label_request = target.model_copy(
        update={"evidence_rows": (changed_row, *target.evidence_rows[1:])}
    )
    assessor = OnboardingReuseAssessor()
    changed_label_assessment = assessor.assess(
        _configuration(),
        changed_label_request,
        assessment_id="fictionalco-fy2027-changed-label-v1",
        assessed_at=_ASSESSED_AT,
    )
    changed_profile_assessment = assessor.assess(
        _configuration(),
        _new_request(profile_version="different-profile-v1"),
        assessment_id="fictionalco-fy2027-changed-profile-v1",
        assessed_at=_ASSESSED_AT,
    )

    assert changed_label_assessment.decision_assessments[0].outcome == "missing_evidence"
    assert changed_profile_assessment.review_required_count == 5
    assert {item.outcome for item in changed_profile_assessment.decision_assessments} == {
        "incompatible_context"
    }


def test_assessment_persistence_is_non_overwriting_and_cli_writes_report(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configuration = _configuration()
    request = _new_request()
    assessor = OnboardingReuseAssessor()
    assessment = assessor.assess(
        configuration,
        request,
        assessment_id="fictionalco-fy2027-persist-v1",
        assessed_at=_ASSESSED_AT,
    )
    output = tmp_path / "assessment.json"

    assessor.persist(assessment, output)
    assessor.persist(assessment, output)
    output.write_text("{}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="refusing to overwrite"):
        assessor.persist(assessment, output)

    configuration_path = tmp_path / "configuration.json"
    request_path = tmp_path / "request.json"
    configuration_path.write_text(configuration.model_dump_json(indent=2), encoding="utf-8")
    request_path.write_text(request.model_dump_json(indent=2), encoding="utf-8")
    data_directory = tmp_path / "data"
    monkeypatch.setenv("ICA_DATA_DIRECTORY", str(data_directory))
    exit_code = main(
        [
            "assess-onboarding-reuse",
            "--configuration",
            str(configuration_path),
            "--request",
            str(request_path),
            "--assessment-id",
            "fictionalco-fy2027-cli-v1",
            "--assessed-at",
            _ASSESSED_AT.isoformat(),
        ]
    )

    report_path = (
        data_directory
        / "interim"
        / "onboarding-reuse-assessments"
        / "fictionalco-fy2027-cli-v1.json"
    )
    restored = OnboardingReuseAssessment.model_validate_json(
        report_path.read_text(encoding="utf-8")
    )
    assert exit_code == 0
    assert restored.reusable_candidate_count == 5
