"""Provenance gates shared by ingestion and analysis workflows."""

from collections.abc import Iterable

from indian_company_analysis.domain.exceptions import ProvenanceError
from indian_company_analysis.domain.models import MetricObservation


def validate_observation_provenance(
    observations: Iterable[MetricObservation], known_source_ids: frozenset[str]
) -> None:
    for observation in observations:
        if not observation.source_reference_ids:
            raise ProvenanceError(f"observation {observation.observation_id} has no evidence")
        unknown = set(observation.source_reference_ids) - known_source_ids
        if unknown:
            raise ProvenanceError(
                f"observation {observation.observation_id} references unknown sources: "
                f"{sorted(unknown)}"
            )
