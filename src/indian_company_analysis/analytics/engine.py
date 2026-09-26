"""Deterministic Phase 1 financial-analysis engine."""

from collections.abc import Callable
from decimal import Decimal

from indian_company_analysis.analytics.observations import (
    ObservationIndex,
    comparability_error,
    source_ids,
)
from indian_company_analysis.analytics.ratios import (
    activity_days,
    average,
    capital_employed,
    compound_annual_growth,
    free_cash_flow,
    gross_debt,
    net_debt,
)
from indian_company_analysis.domain.enums import CalculationStatus, ReportingBasis, UnitType
from indian_company_analysis.domain.metrics import METRIC_DEFINITIONS, MetricId
from indian_company_analysis.domain.models import (
    CalculationResult,
    DemoDataset,
    MetricObservation,
    ReportingPeriod,
)

Calculator = Callable[[tuple[MetricObservation, ...]], Decimal | None]


class FinancialAnalysisEngine:
    """Calculate documented metrics without using narrative or model inference."""

    FORMULA_VERSION = "1.0.0"

    def analyze(self, dataset: DemoDataset) -> tuple[CalculationResult, ...]:
        index = ObservationIndex.from_dataset(dataset)
        results: list[CalculationResult] = []
        for company in dataset.companies:
            for basis in index.bases_for(company.company_id):
                periods = index.annual_periods_for(company.company_id, basis)
                for position, period in enumerate(periods):
                    prior_period = periods[position - 1] if position else None
                    results.extend(
                        self._period_results(index, company.company_id, basis, period, prior_period)
                    )
                if len(periods) >= 2:
                    results.append(
                        self._cagr_result(index, company.company_id, basis, periods[0], periods[-1])
                    )
        return tuple(results)

    def _period_results(
        self,
        index: ObservationIndex,
        company_id: str,
        basis: ReportingBasis,
        period: ReportingPeriod,
        prior_period: ReportingPeriod | None,
    ) -> list[CalculationResult]:
        def get(
            metric: MetricId, selected_period: ReportingPeriod = period
        ) -> MetricObservation | None:
            return index.get(company_id, metric, selected_period, basis)

        results = [
            self._compute(
                company_id,
                MetricId.EBITDA_MARGIN,
                period,
                basis,
                "ebitda / revenue",
                (get(MetricId.EBITDA), get(MetricId.REVENUE)),
                lambda items: self._divide(items[0].value, items[1].value),
            ),
            self._compute(
                company_id,
                MetricId.EBIT_MARGIN,
                period,
                basis,
                "ebit / revenue",
                (get(MetricId.EBIT), get(MetricId.REVENUE)),
                lambda items: self._divide(items[0].value, items[1].value),
            ),
            self._compute(
                company_id,
                MetricId.PAT_MARGIN,
                period,
                basis,
                "profit_after_tax / revenue",
                (get(MetricId.PROFIT_AFTER_TAX), get(MetricId.REVENUE)),
                lambda items: self._divide(items[0].value, items[1].value),
            ),
            self._compute(
                company_id,
                MetricId.CFO_TO_PAT_CONVERSION,
                period,
                basis,
                "cash_flow_from_operations / profit_after_tax",
                (
                    get(MetricId.CASH_FLOW_FROM_OPERATIONS),
                    get(MetricId.PROFIT_AFTER_TAX),
                ),
                lambda items: self._divide(items[0].value, items[1].value),
            ),
            self._compute(
                company_id,
                MetricId.FREE_CASH_FLOW,
                period,
                basis,
                "cash_flow_from_operations - capital_expenditure",
                (
                    get(MetricId.CASH_FLOW_FROM_OPERATIONS),
                    get(MetricId.CAPITAL_EXPENDITURE),
                ),
                lambda items: free_cash_flow(items[0].value, items[1].value),
            ),
            self._compute(
                company_id,
                MetricId.FREE_CASH_FLOW_MARGIN,
                period,
                basis,
                "(cash_flow_from_operations - capital_expenditure) / revenue",
                (
                    get(MetricId.CASH_FLOW_FROM_OPERATIONS),
                    get(MetricId.CAPITAL_EXPENDITURE),
                    get(MetricId.REVENUE),
                ),
                lambda items: self._divide(
                    free_cash_flow(items[0].value, items[1].value), items[2].value
                ),
            ),
            self._compute(
                company_id,
                MetricId.GROSS_DEBT,
                period,
                basis,
                "short_term_debt + long_term_debt",
                (get(MetricId.SHORT_TERM_DEBT), get(MetricId.LONG_TERM_DEBT)),
                lambda items: gross_debt(items[0].value, items[1].value),
            ),
            self._compute(
                company_id,
                MetricId.NET_DEBT,
                period,
                basis,
                "short_term_debt + long_term_debt - cash_and_equivalents",
                (
                    get(MetricId.SHORT_TERM_DEBT),
                    get(MetricId.LONG_TERM_DEBT),
                    get(MetricId.CASH_AND_EQUIVALENTS),
                ),
                lambda items: net_debt(items[0].value, items[1].value, items[2].value),
            ),
            self._compute(
                company_id,
                MetricId.DEBT_TO_EQUITY,
                period,
                basis,
                "(short_term_debt + long_term_debt) / total_equity",
                (
                    get(MetricId.SHORT_TERM_DEBT),
                    get(MetricId.LONG_TERM_DEBT),
                    get(MetricId.TOTAL_EQUITY),
                ),
                lambda items: self._divide_positive_denominator(
                    gross_debt(items[0].value, items[1].value), items[2].value
                ),
            ),
            self._compute(
                company_id,
                MetricId.INTEREST_COVERAGE,
                period,
                basis,
                "ebit / finance_cost",
                (get(MetricId.EBIT), get(MetricId.FINANCE_COST)),
                lambda items: self._divide(items[0].value, items[1].value),
            ),
        ]

        if prior_period is None:
            results.extend(
                self._not_applicable(company_id, metric_id, period, basis)
                for metric_id in (
                    MetricId.REVENUE_GROWTH,
                    MetricId.RETURN_ON_EQUITY,
                    MetricId.RETURN_ON_CAPITAL_EMPLOYED,
                    MetricId.RECEIVABLE_DAYS,
                    MetricId.INVENTORY_DAYS,
                    MetricId.PAYABLE_DAYS,
                    MetricId.CASH_CONVERSION_CYCLE,
                )
            )
            return results

        def prior(metric: MetricId) -> MetricObservation | None:
            return get(metric, prior_period)

        days = (period.end_date - period.start_date).days + 1
        results.extend(
            (
                self._compute(
                    company_id,
                    MetricId.REVENUE_GROWTH,
                    period,
                    basis,
                    "current_revenue / prior_revenue - 1",
                    (get(MetricId.REVENUE), prior(MetricId.REVENUE)),
                    lambda items: self._divide(items[0].value, items[1].value) - Decimal(1),
                ),
                self._compute(
                    company_id,
                    MetricId.RETURN_ON_EQUITY,
                    period,
                    basis,
                    "profit_after_tax / average_total_equity",
                    (
                        get(MetricId.PROFIT_AFTER_TAX),
                        prior(MetricId.TOTAL_EQUITY),
                        get(MetricId.TOTAL_EQUITY),
                    ),
                    lambda items: self._divide_positive_denominator(
                        items[0].value, average(items[1].value, items[2].value)
                    ),
                ),
                self._compute(
                    company_id,
                    MetricId.RETURN_ON_CAPITAL_EMPLOYED,
                    period,
                    basis,
                    "ebit / average(equity + debt - cash)",
                    (
                        get(MetricId.EBIT),
                        prior(MetricId.TOTAL_EQUITY),
                        prior(MetricId.SHORT_TERM_DEBT),
                        prior(MetricId.LONG_TERM_DEBT),
                        prior(MetricId.CASH_AND_EQUIVALENTS),
                        get(MetricId.TOTAL_EQUITY),
                        get(MetricId.SHORT_TERM_DEBT),
                        get(MetricId.LONG_TERM_DEBT),
                        get(MetricId.CASH_AND_EQUIVALENTS),
                    ),
                    self._roce,
                ),
                self._working_capital_days(
                    company_id,
                    MetricId.RECEIVABLE_DAYS,
                    period,
                    basis,
                    prior(MetricId.TRADE_RECEIVABLES),
                    get(MetricId.TRADE_RECEIVABLES),
                    get(MetricId.REVENUE),
                    days,
                    "average_trade_receivables / revenue * period_days",
                ),
                self._working_capital_days(
                    company_id,
                    MetricId.INVENTORY_DAYS,
                    period,
                    basis,
                    prior(MetricId.INVENTORY),
                    get(MetricId.INVENTORY),
                    get(MetricId.COST_OF_REVENUE),
                    days,
                    "average_inventory / cost_of_revenue * period_days",
                ),
                self._working_capital_days(
                    company_id,
                    MetricId.PAYABLE_DAYS,
                    period,
                    basis,
                    prior(MetricId.TRADE_PAYABLES),
                    get(MetricId.TRADE_PAYABLES),
                    get(MetricId.COST_OF_REVENUE),
                    days,
                    "average_trade_payables / cost_of_revenue * period_days",
                ),
                self._compute(
                    company_id,
                    MetricId.CASH_CONVERSION_CYCLE,
                    period,
                    basis,
                    "receivable_days + inventory_days - payable_days",
                    (
                        prior(MetricId.TRADE_RECEIVABLES),
                        get(MetricId.TRADE_RECEIVABLES),
                        prior(MetricId.INVENTORY),
                        get(MetricId.INVENTORY),
                        prior(MetricId.TRADE_PAYABLES),
                        get(MetricId.TRADE_PAYABLES),
                        get(MetricId.REVENUE),
                        get(MetricId.COST_OF_REVENUE),
                    ),
                    lambda items: self._cash_conversion_cycle(items, days),
                ),
            )
        )
        return results

    def _cagr_result(
        self,
        index: ObservationIndex,
        company_id: str,
        basis: ReportingBasis,
        first_period: ReportingPeriod,
        last_period: ReportingPeriod,
    ) -> CalculationResult:
        beginning = index.get(company_id, MetricId.REVENUE, first_period, basis)
        ending = index.get(company_id, MetricId.REVENUE, last_period, basis)
        years = last_period.end_date.year - first_period.end_date.year
        return self._compute(
            company_id,
            MetricId.REVENUE_CAGR,
            last_period,
            basis,
            f"(ending_revenue / beginning_revenue) ^ (1 / {years}) - 1",
            (ending, beginning),
            lambda items: compound_annual_growth(items[0].value, items[1].value, years),
        )

    def _working_capital_days(
        self,
        company_id: str,
        metric_id: MetricId,
        period: ReportingPeriod,
        basis: ReportingBasis,
        opening: MetricObservation | None,
        closing: MetricObservation | None,
        flow: MetricObservation | None,
        days: int,
        formula: str,
    ) -> CalculationResult:
        return self._compute(
            company_id,
            metric_id,
            period,
            basis,
            formula,
            (opening, closing, flow),
            lambda items: activity_days(
                average(items[0].value, items[1].value), items[2].value, days
            ),
        )

    def _compute(
        self,
        company_id: str,
        metric_id: MetricId,
        period: ReportingPeriod,
        basis: ReportingBasis,
        formula: str,
        inputs: tuple[MetricObservation | None, ...],
        calculator: Calculator,
    ) -> CalculationResult:
        available = tuple(item for item in inputs if item is not None)
        if len(available) != len(inputs):
            return self._result(
                company_id,
                metric_id,
                period,
                basis,
                CalculationStatus.MISSING_INPUT,
                formula,
                available,
                None,
                "one or more required observations are missing",
            )
        error = comparability_error(available)
        if error is not None:
            return self._result(
                company_id,
                metric_id,
                period,
                basis,
                CalculationStatus.INCOMPARABLE_INPUTS,
                formula,
                available,
                None,
                error,
            )
        try:
            value = calculator(available)
        except ZeroDivisionError:
            return self._result(
                company_id,
                metric_id,
                period,
                basis,
                CalculationStatus.ZERO_DENOMINATOR,
                formula,
                available,
                None,
                "the formula denominator is zero",
            )
        if value is None:
            return self._result(
                company_id,
                metric_id,
                period,
                basis,
                CalculationStatus.NOT_APPLICABLE,
                formula,
                available,
                None,
                "the formula is not meaningful for the supplied values",
            )
        return self._result(
            company_id,
            metric_id,
            period,
            basis,
            CalculationStatus.SUCCESS,
            formula,
            available,
            self._quantize(metric_id, value),
            None,
        )

    def _not_applicable(
        self,
        company_id: str,
        metric_id: MetricId,
        period: ReportingPeriod,
        basis: ReportingBasis,
    ) -> CalculationResult:
        return self._result(
            company_id,
            metric_id,
            period,
            basis,
            CalculationStatus.NOT_APPLICABLE,
            "requires opening and closing annual balances",
            (),
            None,
            "no prior annual period is available",
        )

    def _result(
        self,
        company_id: str,
        metric_id: MetricId,
        period: ReportingPeriod,
        basis: ReportingBasis,
        status: CalculationStatus,
        formula: str,
        inputs: tuple[MetricObservation, ...],
        value: Decimal | None,
        message: str | None,
    ) -> CalculationResult:
        definition = METRIC_DEFINITIONS[metric_id]
        unit = self._unit(definition.unit_type, inputs)
        return CalculationResult(
            calculation_id=f"{company_id}:{metric_id}:{period.end_date.isoformat()}",
            company_id=company_id,
            metric_id=metric_id,
            period=period,
            reporting_basis=basis,
            status=status,
            value=value,
            unit=unit,
            formula=formula,
            formula_version=self.FORMULA_VERSION,
            input_observation_ids=tuple(item.observation_id for item in inputs),
            source_reference_ids=source_ids(inputs),
            message=message,
        )

    @staticmethod
    def _divide(numerator: Decimal, denominator: Decimal) -> Decimal:
        if denominator == 0:
            raise ZeroDivisionError
        return numerator / denominator

    @staticmethod
    def _divide_positive_denominator(numerator: Decimal, denominator: Decimal) -> Decimal | None:
        if denominator <= 0:
            return None
        return numerator / denominator

    def _roce(self, items: tuple[MetricObservation, ...]) -> Decimal | None:
        opening_capital = capital_employed(*(item.value for item in items[1:5]))
        closing_capital = capital_employed(*(item.value for item in items[5:9]))
        return self._divide_positive_denominator(
            items[0].value, average(opening_capital, closing_capital)
        )

    def _cash_conversion_cycle(self, items: tuple[MetricObservation, ...], days: int) -> Decimal:
        receivable_days = self._required_days(items[0].value, items[1].value, items[6].value, days)
        inventory_days = self._required_days(items[2].value, items[3].value, items[7].value, days)
        payable_days = self._required_days(items[4].value, items[5].value, items[7].value, days)
        return receivable_days + inventory_days - payable_days

    @staticmethod
    def _required_days(opening: Decimal, closing: Decimal, flow: Decimal, days: int) -> Decimal:
        value = activity_days(average(opening, closing), flow, days)
        if value is None:
            raise ZeroDivisionError
        return value

    @staticmethod
    def _unit(unit_type: UnitType, inputs: tuple[MetricObservation, ...]) -> str:
        if unit_type is UnitType.RATIO:
            return "ratio"
        if unit_type is UnitType.DAYS:
            return "days"
        return inputs[0].unit if inputs else "monetary"

    @staticmethod
    def _quantize(metric_id: MetricId, value: Decimal) -> Decimal:
        unit_type = METRIC_DEFINITIONS[metric_id].unit_type
        if unit_type is UnitType.RATIO:
            return value.quantize(Decimal("0.000001"))
        return value.quantize(Decimal("0.01"))
