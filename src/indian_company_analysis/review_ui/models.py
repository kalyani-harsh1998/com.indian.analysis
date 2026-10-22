"""Typed records for reviewer-selected PDF regions and controlled profile review.

These records are intentionally drafts. A saved draft is not an extraction profile, an approved
mapping, a normalized fact, or a reviewer approval.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field, model_validator

from indian_company_analysis.data.extraction.models import PdfNoteContextExtractionSpec
from indian_company_analysis.data.onboarding.model_input import LocatorBoundContextBundle
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


class ProfileCandidateSubmission(DomainModel):
    """Human-supplied metadata required to turn one saved draft into a candidate profile.

    The browser does not supply this metadata.  In particular, a stable source locator remains a
    reviewer decision rather than an inference from pixels or an LLM suggestion.
    """

    candidate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    bundle_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    profile_version: str = Field(min_length=1)
    context_id: str = Field(pattern=r"^[a-zA-Z0-9][a-zA-Z0-9._:-]*$")
    table_id: str = Field(min_length=1)
    row_number: int = Field(ge=1)
    column_name: str = Field(min_length=1)
    prepared_by: str = Field(min_length=1, max_length=200)
    prepared_at: datetime
    x_tolerance: Decimal = Field(default=Decimal("3"), gt=0, le=10)
    y_tolerance: Decimal = Field(default=Decimal("3"), gt=0, le=10)
    maximum_characters: int = Field(default=2_000, ge=1, le=12_000)

    @model_validator(mode="after")
    def preparation_time_is_timezone_aware(self) -> ProfileCandidateSubmission:
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("profile candidate preparation time must include a timezone")
        return self


class ReviewerProfileCandidate(DomainModel):
    """A deterministic, re-extracted profile candidate derived from an immutable draft.

    It remains review-only.  Its embedded excerpt is untrusted source text, not a financial fact.
    """

    candidate_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    draft_file_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    draft: ReviewerRegionDraft
    profile_spec: PdfNoteContextExtractionSpec
    extracted_context: LocatorBoundContextBundle
    prepared_by: str = Field(min_length=1, max_length=200)
    prepared_at: datetime
    status: Literal["candidate"] = "candidate"

    @model_validator(mode="after")
    def candidate_is_bound_to_its_draft_and_extraction(self) -> ReviewerProfileCandidate:
        if len(self.profile_spec.snippets) != 1:
            raise ValueError(
                "reviewer profile candidate must contain exactly one draft-derived region"
            )
        snippet = self.profile_spec.snippets[0]
        if (
            snippet.source_locator.page_number != self.draft.page_number
            or snippet.metric_ids != self.draft.metric_ids
            or snippet.x0 != self.draft.x0
            or snippet.top != self.draft.top
            or snippet.x1 != self.draft.x1
            or snippet.bottom != self.draft.bottom
        ):
            raise ValueError("profile candidate snippet must exactly match its saved draft region")
        if (
            self.extracted_context.bundle_id != self.profile_spec.bundle_id
            or self.extracted_context.request_id != self.draft.request_id
            or self.extracted_context.source_checksum_sha256 != self.draft.source_checksum_sha256
        ):
            raise ValueError("profile candidate context does not match its draft identity")
        if len(self.extracted_context.snippets) != 1:
            raise ValueError("reviewer profile candidate must retain one extracted context snippet")
        context = self.extracted_context.snippets[0]
        if (
            context.context_id != snippet.context_id
            or context.source_locator != snippet.source_locator
            or context.metric_ids != snippet.metric_ids
        ):
            raise ValueError("profile candidate extracted context does not match its profile spec")
        if self.prepared_at.tzinfo is None or self.prepared_at.utcoffset() is None:
            raise ValueError("profile candidate preparation time must include a timezone")
        return self


class ReviewerProfileReviewDecision(DomainModel):
    """Append-only approval or rejection of one independently revalidated candidate profile."""

    decision_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    outcome: Literal["approved", "rejected"]
    candidate: ReviewerProfileCandidate
    candidate_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_by: str = Field(min_length=1, max_length=200)
    reviewed_at: datetime
    approval_policy_version: str = Field(min_length=1)
    review_rationale: str = Field(min_length=1, max_length=2_000)
    revalidated_context_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    approved_profile: PdfNoteContextExtractionSpec | None = None
    rejection_reasons: tuple[str, ...] = ()

    @model_validator(mode="after")
    def outcome_is_explicit_and_consistent(self) -> ReviewerProfileReviewDecision:
        if self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None:
            raise ValueError("profile review time must include a timezone")
        if self.candidate_checksum_sha256 != profile_candidate_checksum(self.candidate):
            raise ValueError("review decision candidate checksum does not match the candidate")
        if (
            self.revalidated_context_checksum_sha256
            != self.candidate.extracted_context.context_checksum_sha256
        ):
            raise ValueError(
                "review decision must retain the revalidated candidate context checksum"
            )
        if self.outcome == "approved":
            if self.approved_profile != self.candidate.profile_spec:
                raise ValueError("approval must embed the exact candidate profile specification")
            if self.rejection_reasons:
                raise ValueError("approved profile decisions cannot carry rejection reasons")
        elif self.approved_profile is not None:
            raise ValueError("rejected profile decisions cannot contain an approved profile")
        elif not self.rejection_reasons or any(
            not reason.strip() for reason in self.rejection_reasons
        ):
            raise ValueError("rejected profile decisions require nonblank rejection reasons")
        return self


def profile_candidate_checksum(candidate: ReviewerProfileCandidate) -> str:
    """Return a stable checksum for one exact reviewer profile candidate."""

    payload = candidate.model_dump(mode="json")
    # Preserve checksums of pre-attachment approvals: a newly added optional null field must
    # not invalidate the immutable candidate that the reviewer actually approved.
    if candidate.extracted_context.attachment_provenance is None:
        payload["extracted_context"].pop("attachment_provenance", None)
    serialized = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


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
