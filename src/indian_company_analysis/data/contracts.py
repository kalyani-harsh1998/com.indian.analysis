"""Replaceable data-source boundary."""

from typing import Protocol

from indian_company_analysis.domain.models import DemoDataset


class DataSource(Protocol):
    """Minimum source behavior required by the foundational workflow."""

    def load(self) -> DemoDataset: ...
