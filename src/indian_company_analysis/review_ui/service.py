"""Verified local services behind the reviewer UI."""

from __future__ import annotations

import io
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pdfplumber
import pypdfium2 as pdfium  # type: ignore[import-untyped]

from indian_company_analysis.data.extraction.page_discovery import (
    PageDiscoveryInput,
    PageDiscoveryProposal,
    validate_page_discovery_proposal,
)
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document
from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingRequest,
    OnboardingTargetScope,
)
from indian_company_analysis.review_ui.models import (
    RegionDraftSubmission,
    ReviewerPage,
    ReviewerRegionDraft,
    ReviewerSessionMetadata,
)


class ProfileReviewSession:
    """One identity-bound, local-only reviewer session.

    The session accepts a rectangle only for a page that passed local page-discovery validation.
    It verifies the raw PDF before rendering, previewing, or recording a draft.
    """

    def __init__(
        self,
        *,
        source_manifest: RawDocumentManifest,
        onboarding_request: DocumentOnboardingRequest,
        page_discovery_input: PageDiscoveryInput,
        page_discovery_proposal: PageDiscoveryProposal,
        raw_root: Path,
        draft_root: Path,
    ) -> None:
        self._source_manifest = source_manifest
        self._onboarding_request = onboarding_request
        self._page_discovery_input = page_discovery_input
        self._page_discovery_proposal = page_discovery_proposal
        self._raw_root = raw_root
        self._draft_root = draft_root
        self._validate_session()

    def metadata(self) -> ReviewerSessionMetadata:
        context = self._page_discovery_input.request_context
        pages = tuple(
            ReviewerPage(
                page_number=page_number,
                width=width,
                height=height,
                selection_role=(
                    "primary" if page_number == self.primary_page_number else "supporting"
                ),
            )
            for page_number, width, height in self._selected_page_dimensions()
        )
        return ReviewerSessionMetadata(
            proposal_id=self._page_discovery_proposal.proposal_id,
            page_discovery_input_id=self._page_discovery_input.input_id,
            request_id=self._onboarding_request.request_id,
            document_id=self._source_manifest.document_id,
            source_checksum_sha256=self._source_manifest.checksum_sha256,
            company_id=context.company_id,
            reporting_basis=context.reporting_basis.value,
            period_label=context.period.label,
            target_scope_id=context.target_scope_id,
            metric_ids=context.target_metric_ids,
            pages=pages,
        )

    @property
    def primary_page_number(self) -> int:
        selection = self._page_discovery_proposal.primary_selection
        if selection is None:  # guarded by _validate_session
            raise RuntimeError("review session has no primary selected page")
        return selection.page_number

    def render_page_png(self, page_number: int) -> bytes:
        self._assert_selected_page(page_number)
        source_path = self._verified_source_path()
        document = pdfium.PdfDocument(str(source_path))
        try:
            page = document[page_number - 1]
            try:
                bitmap = page.render(scale=2)
                try:
                    image = bitmap.to_pil()
                    output = io.BytesIO()
                    image.save(output, format="PNG")
                    return output.getvalue()
                finally:
                    bitmap.close()
            finally:
                page.close()
        finally:
            document.close()

    def create_draft(self, submission: RegionDraftSubmission) -> tuple[ReviewerRegionDraft, str]:
        self._assert_selected_page(submission.page_number)
        width, height = self._page_dimensions(submission.page_number)
        self._validate_bounds(submission, width=width, height=height)
        draft = ReviewerRegionDraft(
            draft_id=submission.draft_id,
            profile_version=submission.profile_version,
            proposal_id=self._page_discovery_proposal.proposal_id,
            page_discovery_input_id=self._page_discovery_input.input_id,
            request_id=self._onboarding_request.request_id,
            document_id=self._source_manifest.document_id,
            source_checksum_sha256=self._source_manifest.checksum_sha256,
            request_context_checksum_sha256=(
                self._page_discovery_input.request_context_checksum_sha256
            ),
            page_number=submission.page_number,
            metric_ids=self._page_discovery_input.request_context.target_metric_ids,
            x0=submission.x0,
            top=submission.top,
            x1=submission.x1,
            bottom=submission.bottom,
            reviewer_name=submission.reviewer_name,
            review_notes=submission.review_notes,
            created_at=datetime.now(UTC),
        )
        preview_text = self._extract_preview_text(draft)
        self._persist_draft(draft)
        return draft, preview_text

    def _validate_session(self) -> None:
        verification = verify_raw_document(self._source_manifest, self._raw_root)
        if not verification.valid:
            raise ValueError(f"source PDF verification failed: {verification.message}")
        request = self._onboarding_request
        input_packet = self._page_discovery_input
        if request.target_scope is None:
            raise ValueError(
                "profile review requires an onboarding request with explicit target scope"
            )
        if (
            request.request_id != input_packet.request_id
            or request.document_id != input_packet.document_id
            or request.source_checksum_sha256 != input_packet.source_checksum_sha256
            or request.company_id != input_packet.request_context.company_id
            or request.reporting_basis != input_packet.request_context.reporting_basis
            or request.period != input_packet.request_context.period
            or request.target_scope != _target_scope_from_input(input_packet)
        ):
            raise ValueError("page-discovery input does not match the onboarding request")
        validation = validate_page_discovery_proposal(
            self._page_discovery_input, self._page_discovery_proposal
        )
        if not validation.ready_for_review:
            raise ValueError(
                "profile review requires a valid non-abstaining page-discovery proposal"
            )

    def _verified_source_path(self) -> Path:
        verification = verify_raw_document(self._source_manifest, self._raw_root)
        if not verification.valid:
            raise ValueError(f"source PDF verification failed: {verification.message}")
        return self._raw_root / self._source_manifest.stored_relative_path

    def _selected_page_dimensions(self) -> tuple[tuple[int, Decimal, Decimal], ...]:
        return tuple(
            (page_number, *self._page_dimensions(page_number))
            for page_number in self._selected_pages()
        )

    def _page_dimensions(self, page_number: int) -> tuple[Decimal, Decimal]:
        source_path = self._verified_source_path()
        document = pdfium.PdfDocument(str(source_path))
        try:
            if page_number > len(document):
                raise ValueError("selected page does not exist in the verified source PDF")
            page = document[page_number - 1]
            try:
                return Decimal(str(page.get_width())), Decimal(str(page.get_height()))
            finally:
                page.close()
        finally:
            document.close()

    def _extract_preview_text(self, draft: ReviewerRegionDraft) -> str:
        source_path = self._verified_source_path()
        with pdfplumber.open(source_path) as pdf:
            page = pdf.pages[draft.page_number - 1]
            text = page.crop(
                (float(draft.x0), float(draft.top), float(draft.x1), float(draft.bottom))
            ).extract_text(x_tolerance=3, y_tolerance=3)
        normalised = " ".join((text or "").split())
        if not normalised:
            raise ValueError("selected rectangle contains no extractable text")
        return normalised

    def _persist_draft(self, draft: ReviewerRegionDraft) -> None:
        self._draft_root.mkdir(parents=True, exist_ok=True)
        destination = self._draft_root / f"{draft.draft_id}.json"
        serialized = draft.model_dump_json(indent=2) + "\n"
        try:
            with destination.open("x", encoding="utf-8") as output:
                output.write(serialized)
        except FileExistsError as error:
            raise ValueError(
                f"refusing to overwrite existing region draft: {destination}"
            ) from error

    def _selected_pages(self) -> tuple[int, ...]:
        primary = self.primary_page_number
        return (primary,) + tuple(
            selection.page_number
            for selection in self._page_discovery_proposal.supporting_selections
        )

    def _assert_selected_page(self, page_number: int) -> None:
        if page_number not in self._selected_pages():
            raise ValueError("reviewer may select a rectangle only on a validated proposal page")

    @staticmethod
    def _validate_bounds(
        submission: RegionDraftSubmission, *, width: Decimal, height: Decimal
    ) -> None:
        if submission.x1 > width or submission.bottom > height:
            raise ValueError("selected rectangle exceeds the verified PDF page bounds")


def _target_scope_from_input(page_discovery_input: PageDiscoveryInput) -> OnboardingTargetScope:
    """Recreate the value object needed for strict request/input identity comparison."""

    context = page_discovery_input.request_context
    return OnboardingTargetScope(
        scope_id=context.target_scope_id,
        metric_ids=context.target_metric_ids,
        purpose=context.purpose,
    )
