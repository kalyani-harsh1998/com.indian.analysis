"""Framework-neutral contract for sector-specific analytical rules."""

from typing import Protocol


class SectorRuleSet(Protocol):
    @property
    def sector_id(self) -> str: ...

    @property
    def metric_ids(self) -> tuple[str, ...]: ...
