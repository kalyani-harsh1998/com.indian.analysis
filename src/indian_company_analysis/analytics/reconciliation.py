"""Deterministic financial-statement reconciliation checks."""

from collections.abc import Callable
from decimal import Decimal

from indian_company_analysis.analytics.observations import (
    ObservationIndex,
    comparability_error,
    source_ids,
)
from indian_company_analysis.domain.enums import (
    ReconciliationStatus,
    ReconciliationType,
    ReportingBasis,
)
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import (
    DemoDataset,
    MetricObservation,
    ReconciliationResult,
    ReportingPeriod,
)

Reconciler = Callable[[tuple[MetricObservation, ...]], Decimal]


class FinancialStatementReconciler:
    """Check internal statement equations without changing reported values."""

    TOLERANCE = Decimal("0.01")

    def reconcile(self, dataset: DemoDataset) -> tuple[ReconciliationResult, ...]:
        index = ObservationIndex.from_dataset(dataset)
        results: list[ReconciliationResult] = []
        for company in dataset.companies:
            for basis in index.bases_for(company.company_id):
                for period in index.annual_periods_for(company.company_id, basis):
                    results.extend(self._period_results(index, company.company_id, basis, period))
        return tuple(results)

    def _period_results(
        self,
        index: ObservationIndex,
        company_id: str,
        basis: ReportingBasis,
        period: ReportingPeriod,
    ) -> tuple[ReconciliationResult, ...]:
        def get(metric: MetricId) -> MetricObservation | None:
            return index.get(company_id, metric, period, basis)

        return (
            self._check(
                company_id,
                ReconciliationType.EBITDA_TO_EBIT,
                period,
                basis,
                (get(MetricId.EBITDA), get(MetricId.DEPRECIATION_AMORTIZATION), get(MetricId.EBIT)),
                lambda items: items[0].value - items[1].value - items[2].value,
                "EBITDA less depreciation and amortization equals EBIT",
            ),
            self._check(
                company_id,
                ReconciliationType.PROFIT_AFTER_TAX,
                period,
                basis,
                (
                    get(MetricId.PROFIT_BEFORE_TAX),
                    get(MetricId.TAX_EXPENSE),
                    get(MetricId.PROFIT_AFTER_TAX),
                ),
                lambda items: items[0].value - items[1].value - items[2].value,
                "profit before tax less tax expense equals profit after tax",
            ),
            self._check(
                company_id,
                ReconciliationType.BALANCE_SHEET,
                period,
                basis,
                (get(MetricId.TOTAL_ASSETS), get(MetricId.TOTAL_LIABILITIES_AND_EQUITY)),
                lambda items: items[0].value - items[1].value,
                "total assets equal total liabilities and equity",
            ),
            self._check(
                company_id,
                ReconciliationType.CASH_ROLL_FORWARD,
                period,
                basis,
                (
                    get(MetricId.OPENING_CASH),
                    get(MetricId.CASH_FLOW_FROM_OPERATIONS),
                    get(MetricId.CASH_FLOW_FROM_INVESTING),
                    get(MetricId.CASH_FLOW_FROM_FINANCING),
                    get(MetricId.CLOSING_CASH),
                ),
                lambda items: (
                    items[0].value
                    + items[1].value
                    + items[2].value
                    + items[3].value
                    - items[4].value
                ),
                (
                    "opening cash plus operating, investing and financing cash flow "
                    "equals closing cash"
                ),
            ),
        )

    def _check(
        self,
        company_id: str,
        reconciliation_type: ReconciliationType,
        period: ReportingPeriod,
        basis: ReportingBasis,
        inputs: tuple[MetricObservation | None, ...],
        reconciler: Reconciler,
        description: str,
    ) -> ReconciliationResult:
        available = tuple(item for item in inputs if item is not None)
        if len(available) != len(inputs):
            return self._result(
                company_id,
                reconciliation_type,
                period,
                basis,
                ReconciliationStatus.MISSING_INPUT,
                available,
                None,
                f"Not performed: missing input. Expected {description}.",
            )
        error = comparability_error(available)
        if error is not None:
            return self._result(
                company_id,
                reconciliation_type,
                period,
                basis,
                ReconciliationStatus.INCOMPARABLE_INPUTS,
                available,
                None,
                f"Not performed: {error}.",
            )
        difference = reconciler(available).quantize(Decimal("0.01"))
        status = (
            ReconciliationStatus.PASSED
            if abs(difference) <= self.TOLERANCE
            else ReconciliationStatus.FAILED
        )
        message = (
            f"Passed: {description}."
            if status is ReconciliationStatus.PASSED
            else f"Failed by {difference}: expected {description}."
        )
        return self._result(
            company_id,
            reconciliation_type,
            period,
            basis,
            status,
            available,
            difference,
            message,
        )

    def _result(
        self,
        company_id: str,
        reconciliation_type: ReconciliationType,
        period: ReportingPeriod,
        basis: ReportingBasis,
        status: ReconciliationStatus,
        inputs: tuple[MetricObservation, ...],
        difference: Decimal | None,
        message: str,
    ) -> ReconciliationResult:
        return ReconciliationResult(
            reconciliation_id=(f"{company_id}:{reconciliation_type}:{period.end_date.isoformat()}"),
            company_id=company_id,
            reconciliation_type=reconciliation_type,
            period=period,
            reporting_basis=basis,
            status=status,
            difference=difference,
            tolerance=self.TOLERANCE,
            input_observation_ids=tuple(item.observation_id for item in inputs),
            source_reference_ids=source_ids(inputs),
            message=message,
        )
