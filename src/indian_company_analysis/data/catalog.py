"""In-memory source catalog used to resolve evidence references."""

from __future__ import annotations

from dataclasses import dataclass

from indian_company_analysis.domain.models import SourceReference


@dataclass(frozen=True, slots=True)
class SourceCatalog:
    _sources: dict[str, SourceReference]

    @classmethod
    def from_references(cls, references: tuple[SourceReference, ...]) -> SourceCatalog:
        sources = {reference.source_id: reference for reference in references}
        if len(sources) != len(references):
            raise ValueError("source IDs must be unique")
        return cls(sources)

    def get(self, source_id: str) -> SourceReference:
        return self._sources[source_id]

    @property
    def source_ids(self) -> frozenset[str]:
        return frozenset(self._sources)
