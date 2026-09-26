"""Tests for deterministic execution of approved onboarding aggregations."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from indian_company_analysis.analytics.reconciliation import FinancialStatementReconciler
from indian_company_analysis.data.normalization.models import SourceFactLocator
from indian_company_analysis.data.onboarding import (
    ApprovedOnboardingConfiguration,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
    ExclusionCandidate,
    MappingCandidate,
    MetricAggregationCandidate,
    MetricAggregationComponent,
    ModelRunProvenance,
    OnboardingEvidenceRow,
    approve_onboarding_proposal,
    execute_approved_aggregations,
)
from indian_company_analysis.domain.enums import (
    ConfidenceLevel,
    DocumentType,
    PeriodType,
    ReconciliationStatus,
    ReconciliationType,
    ReportingBasis,
    SourceKind,
    ValueClassification,
)
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import (
    CompanyIdentifier,
    DemoDataset,
    MetricObservation,
    ReportingPeriod,
    SourceReference,
)


def _row(evidence_id: str, row_number: int, label: str, value: str) -> OnboardingEvidenceRow:
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


def _request(*, deferred_tax: str = "(1,246)") -> DocumentOnboardingRequest:
    return DocumentOnboardingRequest(
        request_id="fictionalco-fy2026-onboarding-v1",
        document_id="fictionalco-fy2026-annual-report",
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
            _row("row-1", 1, "Revenue from operations", "1,78,650"),
            _row("row-2", 2, "Current tax", "11,767"),
            _row("row-3", 3, "Deferred tax", deferred_tax),
            _row("row-4", 4, "Other income", "3,100"),
        ),
    )


def _proposal() -> DocumentOnboardingProposal:
    return DocumentOnboardingProposal(
        proposal_id="fictionalco-fy2026-proposal-v1",
        request_id="fictionalco-fy2026-onboarding-v1",
        document_id="fictionalco-fy2026-annual-report",
        company_id="fictionalco",
        source_reference_id="source-fictionalco-fy2026",
        source_checksum_sha256="a" * 64,
        source_organization="Fictional Co Limited",
        document_type=DocumentType.ANNUAL_REPORT,
        model_run=ModelRunProvenance(
            provider="deterministic-test-provider",
            model_id="static-proposal",
            model_version="1",
            prompt_version="onboarding-prompt-v1",
            schema_version="onboarding-proposal-v1",
            generated_at=datetime(2026, 9, 27, 10, 0, tzinfo=UTC),
        ),
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
                rationale="Current and deferred tax form total tax expense.",
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


def _configuration(
    request: DocumentOnboardingRequest,
) -> ApprovedOnboardingConfiguration:
    return approve_onboarding_proposal(
        request,
        _proposal(),
        configuration_version="fictionalco-fy2026-mapping-v1",
        aggregation_rule_version="signed-sum-v1",
        reviewed_by="ca-reviewer@example.test",
        reviewed_at=datetime(2026, 9, 27, 11, 0, tzinfo=UTC),
        approval_policy_version="human-review-v1",
    )


def test_approved_tax_components_execute_with_complete_lineage() -> None:
    request = _request()
    result = execute_approved_aggregations(request, _configuration(request))

    assert result.ready_for_analysis is True
    assert not result.issues
    assert result.total_rules == 1
    tax = result.facts[0]
    assert tax.observation.metric_id is MetricId.TAX_EXPENSE
    assert str(tax.observation.value) == "10521"
    assert tax.observation.value_classification is ValueClassification.CALCULATED
    assert tax.observation.source_reference_ids == ("source-fictionalco-fy2026",)
    assert tax.formula == "1*row-2 + 1*row-3"
    assert tax.components[0].reported_label == "Current tax"
    assert str(tax.components[0].parsed_value) == "11767"
    assert str(tax.components[1].parsed_value) == "-1246"
    assert str(tax.components[1].contribution) == "-1246"
    assert tax.rule_version == "signed-sum-v1"
    assert tax.reviewed_by == "ca-reviewer@example.test"


def test_invalid_component_number_is_an_explicit_execution_issue() -> None:
    request = _request(deferred_tax="—")
    result = execute_approved_aggregations(request, _configuration(request))

    assert result.ready_for_analysis is False
    assert not result.facts
    assert result.issues[0].code == "invalid_numeric_value"
    assert result.issues[0].evidence_id == "row-3"


def test_evidence_changed_after_review_is_rejected() -> None:
    approved_request = _request()
    configuration = _configuration(approved_request)
    changed_row = approved_request.evidence_rows[2].model_copy(update={"raw_value": "999"})
    changed_request = approved_request.model_copy(
        update={
            "evidence_rows": (
                approved_request.evidence_rows[0],
                approved_request.evidence_rows[1],
                changed_row,
                approved_request.evidence_rows[3],
            )
        }
    )

    result = execute_approved_aggregations(changed_request, configuration)

    assert result.ready_for_analysis is False
    assert result.issues[0].code == "evidence_snapshot_mismatch"
    assert result.issues[0].evidence_id == "row-3"


def test_period_or_basis_mismatch_cannot_execute_an_approved_configuration() -> None:
    request = _request()
    standalone = request.model_copy(update={"reporting_basis": ReportingBasis.STANDALONE})

    with pytest.raises(ValueError, match="reporting_basis"):
        execute_approved_aggregations(standalone, _configuration(request))


def test_aggregated_tax_can_pass_the_existing_pat_reconciliation() -> None:
    request = _request()
    aggregated_tax = (
        execute_approved_aggregations(request, _configuration(request)).facts[0].observation
    )
    pbt = MetricObservation(
        observation_id="fictionalco:pbt",
        company_id="fictionalco",
        metric_id=MetricId.PROFIT_BEFORE_TAX,
        value=Decimal("39995"),
        unit=request.unit,
        period=request.period,
        reporting_basis=request.reporting_basis,
        value_classification=ValueClassification.REPORTED,
        source_reference_ids=(request.source_reference_id,),
    )
    pat = MetricObservation(
        observation_id="fictionalco:pat",
        company_id="fictionalco",
        metric_id=MetricId.PROFIT_AFTER_TAX,
        value=Decimal("29474"),
        unit=request.unit,
        period=request.period,
        reporting_basis=request.reporting_basis,
        value_classification=ValueClassification.REPORTED,
        source_reference_ids=(request.source_reference_id,),
    )
    dataset = DemoDataset(
        dataset_name="fictional aggregation reconciliation",
        dataset_version="1",
        analysis_as_of_date=date(2026, 3, 31),
        primary_company_id="fictionalco",
        peer_company_ids=(),
        companies=(
            CompanyIdentifier(
                company_id="fictionalco",
                legal_name="Fictional Co Limited",
                nse_symbol="FICTIONAL",
            ),
        ),
        source_references=(
            SourceReference(
                source_id=request.source_reference_id,
                source_kind=SourceKind.SYNTHETIC,
                source_organization="Fictional Co Limited",
                source_document="Synthetic FY2026 annual report",
                locator="page 287",
                retrieval_timestamp=datetime(2026, 9, 27, tzinfo=UTC),
                checksum_sha256=request.source_checksum_sha256,
                is_synthetic=True,
            ),
        ),
        observations=(pbt, aggregated_tax, pat),
    )

    reconciliations = FinancialStatementReconciler().reconcile(dataset)
    result = next(
        item
        for item in reconciliations
        if item.reconciliation_type is ReconciliationType.PROFIT_AFTER_TAX
    )

    assert result.status is ReconciliationStatus.PASSED
    assert str(result.difference) == "0.00"
    assert aggregated_tax.observation_id in result.input_observation_ids
