"""Framework-neutral report and citation boundaries."""

from pathlib import Path
from typing import Protocol

from indian_company_analysis.domain.models import AnalysisResult, SourceReference


class CitationStore(Protocol):
    def add(self, reference: SourceReference) -> None: ...

    def get(self, source_id: str) -> SourceReference: ...


class ReportRenderer(Protocol):
    def render(self, result: AnalysisResult, destination: Path) -> Path: ...
