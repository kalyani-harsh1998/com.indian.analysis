from decimal import Decimal
from pathlib import Path

from indian_company_analysis.analytics.engine import FinancialAnalysisEngine
from indian_company_analysis.analytics.reconciliation import FinancialStatementReconciler
from indian_company_analysis.data.sources.local_files import LocalFixtureDataSource
from indian_company_analysis.domain.enums import CalculationStatus, ReconciliationStatus
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import CalculationResult, DemoDataset


def _dataset(path: Path) -> DemoDataset:
    return LocalFixtureDataSource(path).load()


def _replace_observation(
    dataset: DemoDataset, observation_id: str, **updates: object
) -> DemoDataset:
    observations = tuple(
        item.model_copy(update=updates) if item.observation_id == observation_id else item
        for item in dataset.observations
    )
    return dataset.model_copy(update={"observations": observations})


def _result(dataset: DemoDataset, metric_id: MetricId, period_label: str) -> CalculationResult:
    return next(
        item
        for item in FinancialAnalysisEngine().analyze(dataset)
        if item.metric_id is metric_id and item.period.label == period_label
    )


def test_restated_revenue_is_used_without_deleting_original(demo_fixture_path: Path) -> None:
    dataset = _dataset(demo_fixture_path)

    growth = _result(dataset, MetricId.REVENUE_GROWTH, "FY2024")

    assert growth.status is CalculationStatus.SUCCESS
    assert growth.value == Decimal("0.111111")
    assert growth.input_observation_ids == (
        "demo_info:revenue:fy2024:restated",
        "demo_info:revenue:fy2023",
    )
    assert any(
        item.observation_id == "demo_info:revenue:fy2024:original" for item in dataset.observations
    )


def test_missing_input_returns_explainable_status(demo_fixture_path: Path) -> None:
    dataset = _dataset(demo_fixture_path)
    observations = tuple(
        item
        for item in dataset.observations
        if item.observation_id != "demo_info:finance_cost:fy2026"
    )
    dataset = dataset.model_copy(update={"observations": observations})

    result = _result(dataset, MetricId.INTEREST_COVERAGE, "FY2026")

    assert result.status is CalculationStatus.MISSING_INPUT
    assert result.value is None
    assert result.message == "one or more required observations are missing"


def test_zero_denominator_is_not_silently_converted_to_zero(
    demo_fixture_path: Path,
) -> None:
    dataset = _replace_observation(
        _dataset(demo_fixture_path),
        "demo_info:finance_cost:fy2026",
        value=Decimal(0),
    )

    result = _result(dataset, MetricId.INTEREST_COVERAGE, "FY2026")

    assert result.status is CalculationStatus.ZERO_DENOMINATOR
    assert result.value is None


def test_different_units_are_incomparable(demo_fixture_path: Path) -> None:
    dataset = _replace_observation(
        _dataset(demo_fixture_path),
        "demo_info:finance_cost:fy2026",
        unit="USD million",
    )

    result = _result(dataset, MetricId.INTEREST_COVERAGE, "FY2026")

    assert result.status is CalculationStatus.INCOMPARABLE_INPUTS
    assert result.message == "inputs use different units"


def test_first_period_average_balance_metrics_are_not_applicable(
    demo_fixture_path: Path,
) -> None:
    result = _result(_dataset(demo_fixture_path), MetricId.RETURN_ON_EQUITY, "FY2022")

    assert result.status is CalculationStatus.NOT_APPLICABLE
    assert result.message == "no prior annual period is available"


def test_non_positive_average_equity_is_not_treated_as_normal_roe(
    demo_fixture_path: Path,
) -> None:
    dataset = _replace_observation(
        _dataset(demo_fixture_path),
        "demo_info:total_equity:fy2026",
        value=Decimal("-760"),
    )

    result = _result(dataset, MetricId.RETURN_ON_EQUITY, "FY2026")

    assert result.status is CalculationStatus.NOT_APPLICABLE
    assert result.value is None


def test_reconciliation_failure_preserves_difference(demo_fixture_path: Path) -> None:
    dataset = _replace_observation(
        _dataset(demo_fixture_path),
        "demo_info:total_assets:fy2026",
        value=Decimal("1261"),
    )

    result = next(
        item
        for item in FinancialStatementReconciler().reconcile(dataset)
        if item.reconciliation_type == "balance_sheet" and item.period.label == "FY2026"
    )

    assert result.status is ReconciliationStatus.FAILED
    assert result.difference == Decimal("1.00")
