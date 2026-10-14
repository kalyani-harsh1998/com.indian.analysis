"""Tests for provider-neutral, model-assisted document onboarding."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest

from indian_company_analysis.__main__ import main
from indian_company_analysis.data.extraction.models import (
    ExtractedTableRow,
    PdfTableExtractionResult,
    PdfTableExtractionSpec,
)
from indian_company_analysis.data.normalization.models import SourceFactLocator
from indian_company_analysis.data.onboarding import (
    AbstentionCandidate,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    ExclusionCandidate,
    LocalOnboardingConfigurationCatalog,
    LocalOnboardingReviewCatalog,
    MappingCandidate,
    MetricAggregationCandidate,
    MetricAggregationComponent,
    ModelRunProvenance,
    OnboardingEvidenceRow,
    OnboardingProposalProvider,
    OnboardingReviewDecision,
    OnboardingTargetScope,
    StaticProposalProvider,
    approve_onboarding_proposal,
    approve_proposal,
    build_onboarding_request,
    reject_proposal,
    validate_onboarding_proposal,
)
from indian_company_analysis.domain.enums import (
    ConfidenceLevel,
    DocumentType,
    PeriodType,
    ReportingBasis,
)
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import ReportingPeriod


def _evidence_row(
    evidence_id: str, row_number: int, label: str, value: str
) -> OnboardingEvidenceRow:
    return OnboardingEvidenceRow(
        evidence_id=evidence_id,
        source_locator=SourceFactLocator(
            page_number=287,
            table_id="profit_and_loss",
            row_number=row_number,
            column_name="FY2026",
        ),
        reported_label=label,
        raw_value=value,
    )


def _request() -> DocumentOnboardingRequest:
    return DocumentOnboardingRequest(
        request_id="fictionalco-fy2026-onboarding-v1",
        document_id="fictionalco-fy2026-annual-report",
        extraction_id="fictional-profit-loss-v1",
        extraction_profile_version="aligned-single-period-v1",
        company_id="fictionalco",
        source_reference_id="source-fictionalco-fy2026",
        source_checksum_sha256="a" * 64,
        source_organization="Fictional Co Limited",
        document_type=DocumentType.ANNUAL_REPORT,
        unit="INR crore",
        period=ReportingPeriod(
            label="FY2026",
            period_type=PeriodType.ANNUAL,
            start_date=date(2025, 4, 1),
            end_date=date(2026, 3, 31),
        ),
        reporting_basis=ReportingBasis.CONSOLIDATED,
        evidence_rows=(
            _evidence_row("row-1", 1, "Revenue from operations", "1,78,650"),
            _evidence_row("row-2", 2, "Current tax", "11,767"),
            _evidence_row("row-3", 3, "Deferred tax", "(1,246)"),
            _evidence_row("row-4", 4, "Other income", "3,100"),
        ),
    )


def _model_run() -> ModelRunProvenance:
    return ModelRunProvenance(
        provider="deterministic-test-provider",
        model_id="static-proposal",
        model_version="1",
        prompt_version="onboarding-prompt-v1",
        schema_version="onboarding-proposal-v1",
        generated_at=datetime(2026, 9, 27, 10, 0, tzinfo=UTC),
    )


def _proposal() -> DocumentOnboardingProposal:
    return DocumentOnboardingProposal(
        proposal_id="fictionalco-fy2026-proposal-v1",
        request_id="fictionalco-fy2026-onboarding-v1",
        document_id="fictionalco-fy2026-annual-report",
        extraction_id="fictional-profit-loss-v1",
        extraction_profile_version="aligned-single-period-v1",
        company_id="fictionalco",
        source_reference_id="source-fictionalco-fy2026",
        source_checksum_sha256="a" * 64,
        source_organization="Fictional Co Limited",
        document_type=DocumentType.ANNUAL_REPORT,
        unit="INR crore",
        period=ReportingPeriod(
            label="FY2026",
            period_type=PeriodType.ANNUAL,
            start_date=date(2025, 4, 1),
            end_date=date(2026, 3, 31),
        ),
        reporting_basis=ReportingBasis.CONSOLIDATED,
        model_run=_model_run(),
        mappings=(
            MappingCandidate(
                candidate_id="map-revenue",
                evidence_id="row-1",
                reported_label="Revenue from operations",
                metric_id=MetricId.REVENUE,
                confidence=ConfidenceLevel.HIGH,
                rationale="The source row explicitly reports operating revenue.",
            ),
        ),
        aggregations=(
            MetricAggregationCandidate(
                candidate_id="aggregate-tax",
                metric_id=MetricId.TAX_EXPENSE,
                components=(
                    MetricAggregationComponent(evidence_id="row-2"),
                    MetricAggregationComponent(evidence_id="row-3"),
                ),
                confidence=ConfidenceLevel.HIGH,
                rationale="Current and deferred tax reconcile to total tax expense.",
            ),
        ),
        exclusions=(
            ExclusionCandidate(
                evidence_id="row-4",
                confidence=ConfidenceLevel.HIGH,
                rationale="Other income is outside the current canonical metric set.",
            ),
        ),
    )


def test_static_provider_returns_a_strict_reproducible_proposal() -> None:
    request = _request()
    expected = _proposal()
    provider: OnboardingProposalProvider = StaticProposalProvider(expected)

    assert provider.propose(request) == expected


def test_request_builder_preserves_extraction_identity_and_locator() -> None:
    spec = PdfTableExtractionSpec(
        extraction_id="fictional-profit-loss-v1",
        page_number=287,
        table_id="profit_and_loss",
        label_column_name="Particulars",
        value_column_name="FY2026",
        unit="INR crore",
        period_label="FY2026",
        period_type=PeriodType.ANNUAL,
        period_start_date=date(2025, 4, 1),
        period_end_date=date(2026, 3, 31),
        reporting_basis=ReportingBasis.CONSOLIDATED,
    )
    extraction = PdfTableExtractionResult(
        extraction_id=spec.extraction_id,
        source_document_id="fictionalco-fy2026-annual-report",
        source_checksum_sha256="a" * 64,
        extraction_tool="synthetic-test",
        extraction_tool_version="1",
        profile_version=spec.profile_version,
        spec=spec,
        rows=(
            ExtractedTableRow(
                page_number=287,
                table_id="profit_and_loss",
                row_number=1,
                column_name="FY2026",
                reported_label="Revenue from operations",
                raw_value="1,78,650",
            ),
        ),
        issues=(),
        ready_for_review=True,
    )

    request = build_onboarding_request(
        extraction,
        request_id="fictionalco-fy2026-onboarding-v1",
        company_id="fictionalco",
        source_reference_id="source-fictionalco-fy2026",
        source_organization="Fictional Co Limited",
        document_type=DocumentType.ANNUAL_REPORT,
    )

    assert request.source_checksum_sha256 == extraction.source_checksum_sha256
    assert request.extraction_id == extraction.extraction_id
    assert request.extraction_profile_version == extraction.profile_version
    assert request.company_id == "fictionalco"
    assert request.source_reference_id == "source-fictionalco-fy2026"
    assert request.evidence_rows[0].evidence_id == "row-287-1"
    assert request.evidence_rows[0].source_locator.page_number == 287
    assert request.evidence_rows[0].raw_value == "1,78,650"


def test_valid_proposal_accounts_for_every_source_row() -> None:
    result = validate_onboarding_proposal(_request(), _proposal())

    assert result.ready_for_review is True
    assert result.validated_mapping_ids == ("map-revenue",)
    assert result.validated_aggregation_ids == ("aggregate-tax",)
    assert result.validated_exclusion_evidence_ids == ("row-4",)
    assert not result.issues


def test_explicit_target_scope_rejects_a_candidate_outside_the_requested_metrics() -> None:
    scope = OnboardingTargetScope(
        scope_id="fictional-revenue-only-v1",
        metric_ids=(MetricId.REVENUE,),
        purpose="Review operating revenue only.",
    )
    request = _request().model_copy(update={"target_scope": scope})
    proposal = _proposal().model_copy(update={"target_scope": scope})

    result = validate_onboarding_proposal(request, proposal)

    assert not result.ready_for_review
    assert {issue.code for issue in result.issues} == {"metric_outside_requested_scope"}
    assert result.issues[0].candidate_id == "aggregate-tax"


def test_explicit_abstention_is_valid_but_cannot_be_approved() -> None:
    proposal = _proposal().model_copy(
        update={
            "exclusions": (),
            "abstentions": (
                AbstentionCandidate(
                    candidate_id="abstain-other-income",
                    evidence_id="row-4",
                    confidence=ConfidenceLevel.LOW,
                    rationale="The row may be relevant to a company-specific metric.",
                ),
            ),
        }
    )

    result = validate_onboarding_proposal(_request(), proposal)

    assert result.ready_for_review is True
    assert result.validated_abstention_ids == ("abstain-other-income",)
    with pytest.raises(ValueError, match="abstentions requiring a reviewed disposition"):
        approve_onboarding_proposal(
            _request(),
            proposal,
            configuration_version="fictionalco-fy2026-mapping-v1",
            aggregation_rule_version="aggregation-v1",
            reviewed_by="ca-reviewer@example.test",
            reviewed_at=datetime(2026, 9, 27, 12, 0, tzinfo=UTC),
            approval_policy_version="review-policy-v1",
        )


def test_review_preserves_model_and_source_evidence_lineage() -> None:
    configuration = approve_onboarding_proposal(
        _request(),
        _proposal(),
        configuration_version="fictionalco-fy2026-mapping-v1",
        aggregation_rule_version="aggregation-v1",
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=datetime(2026, 9, 27, 11, 0, tzinfo=UTC),
        approval_policy_version="human-review-v1",
    )

    assert configuration.mapping_set is not None
    assert configuration.mapping_set.mappings[0].metric_id is MetricId.REVENUE
    assert configuration.direct_mappings[0].evidence_id == "row-1"
    assert configuration.direct_mappings[0].raw_value == "1,78,650"
    assert configuration.model_run.prompt_version == "onboarding-prompt-v1"
    assert configuration.aggregation_rules[0].metric_id is MetricId.TAX_EXPENSE
    assert configuration.aggregation_rules[0].components[0].reported_label == "Current tax"
    assert configuration.exclusions[0].evidence_id == "row-4"
    assert configuration.ready_for_normalization is True
    assert not configuration.normalization_blockers


def test_review_records_and_catalog_require_matching_source_identity(tmp_path: Path) -> None:
    reviewed_at = datetime(2026, 9, 29, 10, 0, tzinfo=UTC)
    decision = approve_proposal(
        _request(),
        _proposal(),
        decision_id="fictionalco-fy2026-approval-v1",
        configuration_version="fictionalco-fy2026-mapping-v1",
        aggregation_rule_version="aggregation-v1",
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=reviewed_at,
        approval_policy_version="human-review-v1",
        review_rationale="Source labels and the tax aggregation were checked against evidence.",
    )
    assert decision.configuration is not None
    configuration_catalog = LocalOnboardingConfigurationCatalog(tmp_path / "configurations")
    review_catalog = LocalOnboardingReviewCatalog(tmp_path / "reviews")

    assert configuration_catalog.register(decision.configuration) is True
    assert configuration_catalog.register(decision.configuration) is False
    assert review_catalog.register(decision) is True
    assert review_catalog.register(decision) is False
    assert (
        configuration_catalog.get_for_request(
            _request(),
            configuration_version="fictionalco-fy2026-mapping-v1",
        )
        == decision.configuration
    )
    changed_request = _request().model_copy(update={"source_checksum_sha256": "b" * 64})
    with pytest.raises(ValueError, match="source_checksum_sha256"):
        configuration_catalog.get_for_request(
            changed_request,
            configuration_version="fictionalco-fy2026-mapping-v1",
        )
    with pytest.raises(ValueError, match="different record"):
        review_catalog.register(decision.model_copy(update={"review_rationale": "Changed."}))


def test_rejection_records_reasons_without_creating_configuration() -> None:
    decision = reject_proposal(
        _request(),
        _proposal(),
        decision_id="fictionalco-fy2026-rejection-v1",
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=datetime(2026, 9, 29, 11, 0, tzinfo=UTC),
        approval_policy_version="human-review-v1",
        review_rationale="The proposed revenue mapping needs further source review.",
        rejection_reasons=("Confirm that revenue excludes pass-through income.",),
    )

    assert decision.outcome == "rejected"
    assert decision.configuration is None
    assert decision.rejection_reasons == ("Confirm that revenue excludes pass-through income.",)


def test_approved_review_record_rejects_unresolved_abstentions() -> None:
    decision = approve_proposal(
        _request(),
        _proposal(),
        decision_id="fictionalco-fy2026-approval-v1",
        configuration_version="fictionalco-fy2026-mapping-v1",
        aggregation_rule_version="aggregation-v1",
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=datetime(2026, 9, 29, 10, 0, tzinfo=UTC),
        approval_policy_version="human-review-v1",
        review_rationale="Synthetic approval.",
    )
    invalid_validation = decision.validation.model_copy(
        update={"validated_abstention_ids": ("abstain-row-4",)}
    )
    invalid_record = decision.model_dump()
    invalid_record["validation"] = invalid_validation.model_dump()

    with pytest.raises(ValueError, match="unresolved abstentions"):
        OnboardingReviewDecision.model_validate(invalid_record)


def test_approval_cli_registers_configuration_and_review_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request_path = tmp_path / "request.json"
    proposal_path = tmp_path / "proposal.json"
    request_path.write_text(_request().model_dump_json(indent=2), encoding="utf-8")
    proposal_path.write_text(_proposal().model_dump_json(indent=2), encoding="utf-8")
    monkeypatch.setenv("ICA_DATA_DIRECTORY", str(tmp_path / "data"))

    exit_code = main(
        [
            "approve-onboarding",
            "--request",
            str(request_path),
            "--proposal",
            str(proposal_path),
            "--decision-id",
            "fictionalco-fy2026-cli-approval-v1",
            "--configuration-version",
            "fictionalco-fy2026-mapping-v1",
            "--aggregation-rule-version",
            "aggregation-v1",
            "--reviewed-by",
            "ca-reviewer@example.test",
            "--reviewed-at",
            "2026-09-29T12:00:00+00:00",
            "--approval-policy-version",
            "human-review-v1",
            "--review-rationale",
            "Synthetic end-to-end approval.",
        ]
    )

    assert exit_code == 0
    assert list((tmp_path / "data" / "interim" / "onboarding-configurations").rglob("*.json"))
    assert list((tmp_path / "data" / "interim" / "onboarding-reviews").glob("*.json"))


def test_rejection_cli_records_decision_without_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request_path = tmp_path / "request.json"
    proposal_path = tmp_path / "proposal.json"
    request_path.write_text(_request().model_dump_json(indent=2), encoding="utf-8")
    proposal_path.write_text(_proposal().model_dump_json(indent=2), encoding="utf-8")
    data_directory = tmp_path / "data"
    monkeypatch.setenv("ICA_DATA_DIRECTORY", str(data_directory))

    exit_code = main(
        [
            "reject-onboarding",
            "--request",
            str(request_path),
            "--proposal",
            str(proposal_path),
            "--decision-id",
            "fictionalco-fy2026-cli-rejection-v1",
            "--reviewed-by",
            "ca-reviewer@example.test",
            "--reviewed-at",
            "2026-09-29T12:00:00+00:00",
            "--approval-policy-version",
            "human-review-v1",
            "--review-rationale",
            "Synthetic end-to-end rejection.",
            "--rejection-reason",
            "Confirm revenue scope before approval.",
        ]
    )

    assert exit_code == 0
    assert list((data_directory / "interim" / "onboarding-reviews").glob("*.json"))
    assert not (data_directory / "interim" / "onboarding-configurations").exists()


def test_direct_mapping_only_configuration_can_enter_current_normalization() -> None:
    request = _request().model_copy(update={"evidence_rows": (_request().evidence_rows[0],)})
    proposal = _proposal().model_copy(update={"aggregations": (), "exclusions": ()})

    configuration = approve_onboarding_proposal(
        request,
        proposal,
        configuration_version="fictionalco-direct-v1",
        aggregation_rule_version="aggregation-v1",
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=datetime(2026, 9, 27, 11, 0, tzinfo=UTC),
        approval_policy_version="human-review-v1",
    )

    assert configuration.ready_for_normalization is True
    assert not configuration.normalization_blockers


def test_duplicate_source_row_use_is_rejected() -> None:
    proposal = _proposal()
    duplicate_component = MetricAggregationComponent(evidence_id="row-1")
    aggregation = proposal.aggregations[0].model_copy(
        update={
            "components": (
                duplicate_component,
                proposal.aggregations[0].components[0],
            )
        }
    )
    proposal = proposal.model_copy(update={"aggregations": (aggregation,)})

    result = validate_onboarding_proposal(_request(), proposal)

    assert result.ready_for_review is False
    assert "duplicate_evidence_use" in {issue.code for issue in result.issues}
    with pytest.raises(ValueError, match="not ready for review"):
        approve_onboarding_proposal(
            _request(),
            proposal,
            configuration_version="invalid-v1",
            aggregation_rule_version="aggregation-v1",
            reviewed_by="ca-reviewer@example.test",
            reviewed_at=datetime(2026, 9, 27, 11, 0, tzinfo=UTC),
            approval_policy_version="human-review-v1",
        )


def test_hallucinated_evidence_and_unaccounted_rows_are_rejected() -> None:
    proposal = _proposal()
    hallucinated_mapping = proposal.mappings[0].model_copy(update={"evidence_id": "row-999"})
    proposal = proposal.model_copy(update={"mappings": (hallucinated_mapping,)})

    result = validate_onboarding_proposal(_request(), proposal)
    codes = {issue.code for issue in result.issues}

    assert result.ready_for_review is False
    assert {"unknown_evidence", "unaccounted_evidence"} <= codes


def test_derived_metric_and_document_identity_mismatch_are_rejected() -> None:
    proposal = _proposal()
    derived_mapping = proposal.mappings[0].model_copy(update={"metric_id": MetricId.REVENUE_GROWTH})
    proposal = proposal.model_copy(
        update={
            "source_organization": "Hallucinated issuer",
            "mappings": (derived_mapping,),
        }
    )

    result = validate_onboarding_proposal(_request(), proposal)
    codes = {issue.code for issue in result.issues}

    assert result.ready_for_review is False
    assert "derived_metric_target" in codes
    assert "proposal_identity_mismatch" in codes


def test_mapping_label_must_match_the_source_evidence_exactly() -> None:
    proposal = _proposal()
    renamed_mapping = proposal.mappings[0].model_copy(update={"reported_label": "Total income"})
    proposal = proposal.model_copy(update={"mappings": (renamed_mapping,)})

    result = validate_onboarding_proposal(_request(), proposal)

    assert result.ready_for_review is False
    assert "reported_label_mismatch" in {issue.code for issue in result.issues}


def test_aggregation_coefficients_are_restricted_to_signs() -> None:
    with pytest.raises(ValueError, match="either -1 or 1"):
        MetricAggregationComponent(evidence_id="row-2", coefficient=Decimal("0.5"))
