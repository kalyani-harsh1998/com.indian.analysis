"""Boundary for future explainable forecast engines."""

from typing import Protocol

from indian_company_analysis.domain.models import ForecastAssumption, ForecastScenario


class ForecastEngine(Protocol):
    def forecast(
        self, assumptions: tuple[ForecastAssumption, ...]
    ) -> tuple[ForecastScenario, ...]: ...
