from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from indian_company_analysis.data.sources.local_files import LocalFixtureDataSource
from indian_company_analysis.domain.enums import (
    CalculationStatus,
    ReconciliationStatus,
    RestatementStatus,
    SourceKind,
    ValueClassification,
)
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.workflows.company_analysis import CompanyAnalysisWorkflow


def test_workflow_executes_with_synthetic_classification(demo_fixture_path: Path) -> None:
    fixed_time = datetime(2026, 4, 30, 12, tzinfo=UTC)
    workflow = CompanyAnalysisWorkflow(
        LocalFixtureDataSource(demo_fixture_path),
        clock=lambda: fixed_time,
        run_id_factory=lambda: "deterministic-test-run",
    )

    result = workflow.run()

    assert result.manifest.run_id == "deterministic-test-run"
    assert result.manifest.data_is_synthetic is True
    assert result.manifest.input_data_version == "2.0.0"
    assert result.manifest.source_kinds == frozenset({SourceKind.SYNTHETIC})
    assert result.manifest.calculation_count == 86
    assert result.manifest.successful_calculation_count == 79
    assert result.manifest.reconciliation_count == 20
    assert len(result.manifest.request.peers) == 0
    assert all(
        item.value_classification is ValueClassification.CALCULATED for item in result.calculations
    )
    assert all(item.status is ReconciliationStatus.PASSED for item in result.reconciliations)
    assert all(item.is_synthetic for item in result.source_references)
    assert len(result.adjustments) == 1

    values = {
        item.metric_id: item.value
        for item in result.calculations
        if item.period.label == "FY2026" and item.status is CalculationStatus.SUCCESS
    }
    assert values[MetricId.REVENUE_GROWTH] == Decimal("0.125000")
    assert values[MetricId.EBITDA_MARGIN] == Decimal("0.240000")
    assert values[MetricId.CFO_TO_PAT_CONVERSION] == Decimal("1.207729")
    assert values[MetricId.FREE_CASH_FLOW] == Decimal("140.00")
    assert values[MetricId.NET_DEBT] == Decimal("-185.00")
    assert values[MetricId.RECEIVABLE_DAYS] == Decimal("63.73")

    fy2024_revenue = [
        item
        for item in result.reported_observations
        if item.metric_id is MetricId.REVENUE and item.period.label == "FY2024"
    ]
    assert {item.restatement_status for item in fy2024_revenue} == {
        RestatementStatus.SUPERSEDED,
        RestatementStatus.RESTATED,
    }


def test_result_serializes_to_structured_json(demo_fixture_path: Path, tmp_path: Path) -> None:
    result = CompanyAnalysisWorkflow(LocalFixtureDataSource(demo_fixture_path)).run()
    output = tmp_path / "result.json"
    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    serialized = output.read_text(encoding="utf-8")
    assert '"data_is_synthetic": true' in serialized
    assert '"workflow_name": "synthetic_company_analysis"' in serialized
    assert '"value_classification": "calculated"' in serialized
    assert '"reconciliation_type": "balance_sheet"' in serialized
    assert '"restatement_status": "superseded"' in serialized
