"""Typed records for a reviewer-selected PDF region.

These records are intentionally drafts. A saved draft is not an extraction profile, an approved
mapping, a normalized fact, or a reviewer approval.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import Field, model_validator

from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel


class RegionDraftSubmission(DomainModel):
    """Untrusted local-browser input for one selected PDF rectangle."""

    draft_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    profile_version: str = Field(min_length=1)
    reviewer_name: str = Field(min_length=1, max_length=200)
    review_notes: str = Field(min_length=1, max_length=2_000)
    page_number: int = Field(ge=1)
    x0: Decimal = Field(ge=0)
    top: Decimal = Field(ge=0)
    x1: Decimal = Field(gt=0)
    bottom: Decimal = Field(gt=0)

    @model_validator(mode="after")
    def bounds_are_ordered(self) -> RegionDraftSubmission:
        if self.x1 <= self.x0 or self.bottom <= self.top:
            raise ValueError("region right/bottom bounds must exceed left/top bounds")
        return self


class ReviewerRegionDraft(DomainModel):
    """Append-only record of a rectangle selected during one verified review session."""

    draft_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    profile_version: str = Field(min_length=1)
    proposal_id: str = Field(min_length=1)
    page_discovery_input_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_context_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    page_number: int = Field(ge=1)
    metric_ids: tuple[MetricId, ...] = Field(min_length=1)
    x0: Decimal = Field(ge=0)
    top: Decimal = Field(ge=0)
    x1: Decimal = Field(gt=0)
    bottom: Decimal = Field(gt=0)
    reviewer_name: str = Field(min_length=1, max_length=200)
    review_notes: str = Field(min_length=1, max_length=2_000)
    created_at: datetime
    status: str = "draft"

    @model_validator(mode="after")
    def state_is_consistent(self) -> ReviewerRegionDraft:
        if self.x1 <= self.x0 or self.bottom <= self.top:
            raise ValueError("draft region right/bottom bounds must exceed left/top bounds")
        if self.status != "draft":
            raise ValueError("reviewer UI may create draft regions only")
        if self.created_at.tzinfo is None or self.created_at.utcoffset() is None:
            raise ValueError("draft creation time must include a timezone")
        return self


class ReviewerPage(DomainModel):
    """Safe PDF-page metadata exposed to the local browser."""

    page_number: int = Field(ge=1)
    width: Decimal = Field(gt=0)
    height: Decimal = Field(gt=0)
    selection_role: str = Field(pattern=r"^(primary|supporting)$")


class ReviewerSessionMetadata(DomainModel):
    """Identity-bound metadata for a local profile-review session."""

    proposal_id: str = Field(min_length=1)
    page_discovery_input_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    company_id: str = Field(min_length=1)
    reporting_basis: str = Field(min_length=1)
    period_label: str = Field(min_length=1)
    target_scope_id: str = Field(min_length=1)
    metric_ids: tuple[MetricId, ...] = Field(min_length=1)
    pages: tuple[ReviewerPage, ...] = Field(min_length=1)
