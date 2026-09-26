from indian_company_analysis.domain.enums import MetricNature, StatementType, UnitType
from indian_company_analysis.domain.metrics import METRIC_DEFINITIONS, MetricId


def test_every_metric_id_has_one_canonical_definition() -> None:
    assert set(METRIC_DEFINITIONS) == set(MetricId)


def test_reported_and_derived_metrics_are_distinguished() -> None:
    revenue = METRIC_DEFINITIONS[MetricId.REVENUE]
    roce = METRIC_DEFINITIONS[MetricId.RETURN_ON_CAPITAL_EMPLOYED]

    assert revenue.statement_type is StatementType.INCOME_STATEMENT
    assert revenue.nature is MetricNature.FLOW
    assert revenue.unit_type is UnitType.MONETARY
    assert roce.statement_type is StatementType.ANALYTICAL
    assert roce.nature is MetricNature.DERIVED
    assert roce.unit_type is UnitType.RATIO
