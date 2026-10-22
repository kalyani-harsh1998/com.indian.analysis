"""Controlled conversion and review of one saved visual-region draft.

This module deliberately uses the existing note-context extractor for every re-extraction.  It
does not make browser rectangles executable, call a provider, or create financial facts.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path

from indian_company_analysis.data.extraction.models import (
    PdfNoteContextExtractionSpec,
    PdfNoteContextSnippetSpec,
)
from indian_company_analysis.data.extraction.note_context import PdfNoteContextExtractor
from indian_company_analysis.data.locators import SourceFactLocator
from indian_company_analysis.data.onboarding.model_input import (
    ContextAttachmentProvenance,
    LocatorBoundContextBundle,
    OnboardingModelInputPolicy,
    PromptIsolatedOnboardingInputBuilder,
    onboarding_request_checksum,
)
from indian_company_analysis.data.onboarding.models import DocumentOnboardingRequest
from indian_company_analysis.review_ui.models import (
    ProfileCandidateSubmission,
    ReviewerProfileCandidate,
    ReviewerProfileReviewDecision,
    ReviewerRegionDraft,
    profile_candidate_checksum,
)
from indian_company_analysis.review_ui.service import ProfileReviewSession


def read_draft(path: Path) -> tuple[ReviewerRegionDraft, str]:
    """Read a persisted draft and bind subsequent work to its exact bytes."""

    contents = path.read_bytes()
    return ReviewerRegionDraft.model_validate_json(contents), _sha256(contents)


def candidate_checksum(candidate: ReviewerProfileCandidate) -> str:
    """Return a stable checksum for one exact candidate artifact."""

    return profile_candidate_checksum(candidate)


class ReviewerProfileWorkflow:
    """Prepare and independently review source-bound executable profile candidates."""

    def __init__(self, session: ProfileReviewSession) -> None:
        self._session = session

    def prepare_candidate(
        self,
        draft: ReviewerRegionDraft,
        *,
        draft_file_checksum_sha256: str,
        submission: ProfileCandidateSubmission,
    ) -> ReviewerProfileCandidate:
        """Add explicit locator metadata and re-extract the region from the verified PDF."""

        self._session.validate_saved_draft(draft)
        spec = PdfNoteContextExtractionSpec(
            bundle_id=submission.bundle_id,
            profile_version=submission.profile_version,
            snippets=(
                PdfNoteContextSnippetSpec(
                    context_id=submission.context_id,
                    source_locator=SourceFactLocator(
                        page_number=draft.page_number,
                        table_id=submission.table_id,
                        row_number=submission.row_number,
                        column_name=submission.column_name,
                    ),
                    metric_ids=draft.metric_ids,
                    x0=draft.x0,
                    top=draft.top,
                    x1=draft.x1,
                    bottom=draft.bottom,
                    x_tolerance=submission.x_tolerance,
                    y_tolerance=submission.y_tolerance,
                    maximum_characters=submission.maximum_characters,
                ),
            ),
        )
        context = PdfNoteContextExtractor().extract(
            self._session.source_manifest,
            self._session.raw_root,
            self._session.onboarding_request,
            spec,
        )
        return ReviewerProfileCandidate(
            candidate_id=submission.candidate_id,
            draft_file_checksum_sha256=draft_file_checksum_sha256,
            draft=draft,
            profile_spec=spec,
            extracted_context=context,
            prepared_by=submission.prepared_by,
            prepared_at=submission.prepared_at,
        )

    def approve_candidate(
        self,
        candidate: ReviewerProfileCandidate,
        *,
        draft: ReviewerRegionDraft,
        draft_file_checksum_sha256: str,
        decision_id: str,
        reviewed_by: str,
        reviewed_at: datetime,
        approval_policy_version: str,
        review_rationale: str,
    ) -> ReviewerProfileReviewDecision:
        """Re-extract before recording an approval; nothing is trusted from disk unchanged."""

        self._revalidate_candidate(candidate, draft, draft_file_checksum_sha256)
        return ReviewerProfileReviewDecision(
            decision_id=decision_id,
            outcome="approved",
            candidate=candidate,
            candidate_checksum_sha256=candidate_checksum(candidate),
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            approval_policy_version=approval_policy_version,
            review_rationale=review_rationale,
            revalidated_context_checksum_sha256=(
                candidate.extracted_context.context_checksum_sha256
            ),
            approved_profile=candidate.profile_spec,
        )

    def reject_candidate(
        self,
        candidate: ReviewerProfileCandidate,
        *,
        draft: ReviewerRegionDraft,
        draft_file_checksum_sha256: str,
        decision_id: str,
        reviewed_by: str,
        reviewed_at: datetime,
        approval_policy_version: str,
        review_rationale: str,
        rejection_reasons: tuple[str, ...],
    ) -> ReviewerProfileReviewDecision:
        """Record a rejection after the same source and candidate revalidation."""

        self._revalidate_candidate(candidate, draft, draft_file_checksum_sha256)
        return ReviewerProfileReviewDecision(
            decision_id=decision_id,
            outcome="rejected",
            candidate=candidate,
            candidate_checksum_sha256=candidate_checksum(candidate),
            reviewed_by=reviewed_by,
            reviewed_at=reviewed_at,
            approval_policy_version=approval_policy_version,
            review_rationale=review_rationale,
            revalidated_context_checksum_sha256=(
                candidate.extracted_context.context_checksum_sha256
            ),
            rejection_reasons=rejection_reasons,
        )

    def extract_approved_context(
        self,
        decision: ReviewerProfileReviewDecision,
    ) -> LocatorBoundContextBundle:
        """Re-extract one approved profile for use as bounded untrusted context.

        The returned bundle is still not an approved financial fact.  This is intentionally the
        only bridge from a profile decision into an existing provider-input artifact.
        """

        if decision.outcome != "approved" or decision.approved_profile is None:
            raise ValueError("only an approved reviewer profile decision can extract context")
        if decision.candidate_checksum_sha256 != candidate_checksum(decision.candidate):
            raise ValueError("approved profile decision candidate checksum does not match")
        self._session.validate_saved_draft(decision.candidate.draft)
        if decision.approved_profile != decision.candidate.profile_spec:
            raise ValueError("approved profile decision does not match its candidate profile")
        context = PdfNoteContextExtractor().extract(
            self._session.source_manifest,
            self._session.raw_root,
            self._session.onboarding_request,
            decision.approved_profile,
        )
        if context != decision.candidate.extracted_context:
            raise ValueError("approved profile context changed during re-extraction")
        return context

    def attach_approved_context(
        self,
        decision: ReviewerProfileReviewDecision,
        target_request: DocumentOnboardingRequest,
        *,
        bundle_id: str,
        attached_by: str,
        attached_at: datetime,
        rationale: str,
    ) -> LocatorBoundContextBundle:
        """Attach unchanged, reverified context to another compatible onboarding task.

        The original approval remains scoped to its region/metrics. This attachment is neither
        a mapping approval nor permission to apply the excerpt to other target metrics.
        """

        source_context = self.extract_approved_context(decision)
        source_request = self._session.onboarding_request
        for field in (
            "company_id",
            "document_id",
            "source_checksum_sha256",
            "source_reference_id",
            "source_organization",
            "document_type",
            "unit",
            "period",
            "reporting_basis",
        ):
            if getattr(source_request, field) != getattr(target_request, field):
                raise ValueError(f"context attachment incompatible target {field}")
        decision_json = json.dumps(
            decision.model_dump(mode="json"), sort_keys=True, separators=(",", ":")
        )
        attached = LocatorBoundContextBundle.for_request(
            target_request,
            bundle_id=bundle_id,
            snippets=source_context.snippets,
            extraction_provenance=source_context.extraction_provenance,
            attachment_provenance=ContextAttachmentProvenance(
                source_request_id=source_request.request_id,
                source_request_checksum_sha256=onboarding_request_checksum(source_request),
                target_request_checksum_sha256=onboarding_request_checksum(target_request),
                source_bundle_id=source_context.bundle_id,
                source_context_checksum_sha256=source_context.context_checksum_sha256,
                profile_decision_id=decision.decision_id,
                profile_decision_checksum_sha256=_sha256(decision_json.encode("utf-8")),
                attached_by=attached_by,
                attached_at=attached_at,
                rationale=rationale,
            ),
        )
        # Use the same scope/size/injection boundaries as preparation and live evaluation.
        # Legacy full-statement requests retain their existing all-eligible metric scope.
        PromptIsolatedOnboardingInputBuilder().build(
            target_request,
            input_id=bundle_id,
            policy=OnboardingModelInputPolicy(policy_version="approved-profile-attachment-v1"),
            context_bundle=attached,
        )
        return attached

    def _revalidate_candidate(
        self,
        candidate: ReviewerProfileCandidate,
        draft: ReviewerRegionDraft,
        draft_file_checksum_sha256: str,
    ) -> None:
        self._session.validate_saved_draft(draft)
        if candidate.draft != draft:
            raise ValueError("profile candidate draft does not match the supplied saved draft")
        if candidate.draft_file_checksum_sha256 != draft_file_checksum_sha256:
            raise ValueError("profile candidate draft checksum does not match the supplied draft")
        re_extracted_context = PdfNoteContextExtractor().extract(
            self._session.source_manifest,
            self._session.raw_root,
            self._session.onboarding_request,
            candidate.profile_spec,
        )
        if re_extracted_context != candidate.extracted_context:
            raise ValueError("profile candidate context changed during independent re-extraction")


class LocalReviewerProfileDecisionCatalog:
    """Append-only local storage for profile approval and rejection decisions."""

    def __init__(self, catalog_root: Path) -> None:
        self._catalog_root = catalog_root

    def register(self, decision: ReviewerProfileReviewDecision) -> bool:
        decision_id = _safe_path_component(decision.decision_id, field_name="decision_id")
        destination = self._catalog_root / f"{decision_id}.json"
        serialized = decision.model_dump_json(indent=2) + "\n"
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with destination.open("x", encoding="utf-8") as output:
                output.write(serialized)
        except FileExistsError:
            if destination.read_text(encoding="utf-8") != serialized:
                raise ValueError(
                    f"profile decision catalog already contains a different record at {destination}"
                ) from None
            return False
        return True


def write_once_json(path: Path, serialized: str, *, artifact_name: str) -> bool:
    """Persist a candidate without overwriting an artifact with different content."""

    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("x", encoding="utf-8") as output:
            output.write(serialized)
    except FileExistsError:
        if path.read_text(encoding="utf-8") != serialized:
            raise ValueError(f"refusing to overwrite different {artifact_name}: {path}") from None
        return False
    return True


def _sha256(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def _safe_path_component(value: str, *, field_name: str) -> str:
    candidate = Path(value)
    if value in {"", ".", ".."} or candidate.name != value or value.startswith("."):
        raise ValueError(f"{field_name} must be a safe single path component")
    return value
