"""Strict models for mapping extracted rows to canonical financial facts."""

from __future__ import annotations

from decimal import Decimal

from pydantic import Field, model_validator

from indian_company_analysis.domain.enums import ConfidenceLevel, DocumentType
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel, MetricObservation, SourceReference


def normalize_reported_label(value: str) -> str:
    """Normalize spacing and case for deterministic exact-label matching."""

    return " ".join(value.casefold().split())


class SourceFactLocator(DomainModel):
    """Location of one reported value within its original document."""

    page_number: int = Field(ge=1)
    table_id: str = Field(min_length=1)
    row_number: int = Field(ge=1)
    column_name: str = Field(min_length=1)


class MetricLabelMapping(DomainModel):
    """Reviewed mapping from a source label to a canonical metric."""

    reported_label: str = Field(min_length=1)
    metric_id: MetricId
    sign_multiplier: Decimal = Decimal("1")
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)

    @model_validator(mode="after")
    def multiplier_is_sign_only(self) -> MetricLabelMapping:
        if self.sign_multiplier not in (Decimal("-1"), Decimal("1")):
            raise ValueError("sign_multiplier must be either -1 or 1")
        return self


class MetricMappingSet(DomainModel):
    """Versioned, source-specific exact-label mapping configuration."""

    mapping_version: str = Field(min_length=1)
    source_organization: str = Field(min_length=1)
    document_type: DocumentType
    mappings: tuple[MetricLabelMapping, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reported_labels_are_unique(self) -> MetricMappingSet:
        normalized_labels = [
            normalize_reported_label(item.reported_label) for item in self.mappings
        ]
        if len(normalized_labels) != len(set(normalized_labels)):
            raise ValueError("mapping set contains duplicate normalized reported labels")
        return self


class NormalizationIssue(DomainModel):
    """Explicit reason why one extracted row was not normalized."""

    csv_record_number: int = Field(ge=2)
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    reported_label: str | None = None


class NormalizedFact(DomainModel):
    """An engine-compatible observation plus its field-level document lineage."""

    fact_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_locator: SourceFactLocator
    reported_label: str = Field(min_length=1)
    raw_value: str = Field(min_length=1)
    observation: MetricObservation
    parser_version: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    mapping_method: str = Field(default="exact_label", pattern=r"^exact_label$")
    mapping_confidence: ConfidenceLevel


class NormalizedFactBatch(DomainModel):
    """Deterministic result for one document, including all rejected rows."""

    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_reference: SourceReference
    parser_version: str = Field(min_length=1)
    mapping_version: str = Field(min_length=1)
    total_rows: int = Field(ge=0)
    facts: tuple[NormalizedFact, ...]
    issues: tuple[NormalizationIssue, ...]
    ready_for_analysis: bool

    @model_validator(mode="after")
    def readiness_and_lineage_are_consistent(self) -> NormalizedFactBatch:
        if self.ready_for_analysis != (not self.issues):
            raise ValueError("ready_for_analysis must be false whenever normalization issues exist")
        if self.total_rows != len(self.facts) + len(self.issues):
            raise ValueError("each CSV row must produce exactly one fact or one issue")
        for fact in self.facts:
            if fact.document_id != self.document_id:
                raise ValueError("all normalized facts must reference the batch document")
            if fact.source_checksum_sha256 != self.source_checksum_sha256:
                raise ValueError("all normalized facts must reference the batch checksum")
            if fact.parser_version != self.parser_version:
                raise ValueError("all normalized facts must use the batch parser version")
            if fact.mapping_version != self.mapping_version:
                raise ValueError("all normalized facts must use the batch mapping version")
            if self.source_reference.source_id not in fact.observation.source_reference_ids:
                raise ValueError("normalized observations must retain the source reference")
        return self
