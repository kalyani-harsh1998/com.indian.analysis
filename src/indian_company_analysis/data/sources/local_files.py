"""Validated adapter for explicitly synthetic local JSON fixtures."""

from dataclasses import dataclass
from pathlib import Path

from indian_company_analysis.domain.enums import SourceKind
from indian_company_analysis.domain.models import DemoDataset


@dataclass(frozen=True, slots=True)
class LocalFixtureDataSource:
    path: Path

    def load(self) -> DemoDataset:
        dataset = DemoDataset.model_validate_json(self.path.read_text(encoding="utf-8"))
        if any(
            source.source_kind is not SourceKind.SYNTHETIC for source in dataset.source_references
        ):
            raise ValueError("the demo adapter accepts only explicitly synthetic sources")
        return dataset
