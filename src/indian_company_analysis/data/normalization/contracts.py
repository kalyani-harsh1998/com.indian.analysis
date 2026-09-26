"""Replaceable document-parser boundary."""

from pathlib import Path
from typing import Protocol

from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.normalization.models import MetricMappingSet, NormalizedFactBatch


class FinancialDocumentParser(Protocol):
    """Normalize one verified raw document through an explicit mapping set."""

    parser_version: str

    def parse(
        self,
        manifest: RawDocumentManifest,
        raw_root: Path,
        mapping_set: MetricMappingSet,
    ) -> NormalizedFactBatch: ...
