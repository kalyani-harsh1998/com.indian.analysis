"""Bounded, source-verified page candidates for future LLM-assisted discovery."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal, Protocol

import pdfplumber
from pdfplumber.pdf import PDF
from pydantic import Field, model_validator

from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document
from indian_company_analysis.data.onboarding.models import (
    DocumentOnboardingRequest,
    ModelRunProvenance,
)
from indian_company_analysis.domain.enums import ConfidenceLevel, ReportingBasis
from indian_company_analysis.domain.metrics import MetricId
from indian_company_analysis.domain.models import DomainModel, ReportingPeriod


class PageDiscoveryPolicy(DomainModel):
    """Hard limits for a local PDF page-candidate index."""

    policy_version: str = Field(min_length=1)
    maximum_candidates: int = Field(default=12, ge=1, le=30)
    maximum_excerpt_characters: int = Field(default=1_500, ge=200, le=4_000)


class PageDiscoveryCandidate(DomainModel):
    """One untrusted excerpt from a specific page selected by local term coverage."""

    page_number: int = Field(ge=1)
    lexical_score: int = Field(ge=1)
    excerpt: str = Field(min_length=1)


class PageDiscoveryProvenance(DomainModel):
    source_document_id: str = Field(min_length=1)
    policy_version: str = Field(min_length=1)
    policy_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    extraction_tool: str = Field(min_length=1)
    extraction_tool_version: str = Field(min_length=1)


class PageDiscoveryEvidenceAnchor(DomainModel):
    """A bounded existing statement-row anchor that supplies context, not evidence approval."""

    evidence_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    table_id: str = Field(min_length=1)
    row_number: int = Field(ge=1)
    column_name: str = Field(min_length=1)
    reported_label: str = Field(min_length=1)


class PageDiscoveryRequestContext(DomainModel):
    """The exact basis, period, scope, and row anchors a page-selection proposal must respect."""

    company_id: str = Field(min_length=1)
    reporting_basis: ReportingBasis
    period: ReportingPeriod
    target_scope_id: str = Field(min_length=1)
    target_metric_ids: tuple[MetricId, ...] = Field(min_length=1)
    purpose: str = Field(min_length=1)
    evidence_anchors: tuple[PageDiscoveryEvidenceAnchor, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def anchors_are_unique(self) -> PageDiscoveryRequestContext:
        evidence_ids = [anchor.evidence_id for anchor in self.evidence_anchors]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("page-discovery request context contains duplicate evidence anchors")
        return self


class PageDiscoveryInput(DomainModel):
    """Checksummed, prompt-safe candidate-page packet for a discovery provider.

    This does not grant a provider PDF access. A provider may select only from candidates already
    included in this packet; it cannot create a final extraction profile or approve evidence.
    """

    input_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    request_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_context: PageDiscoveryRequestContext
    request_context_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate_pages: tuple[PageDiscoveryCandidate, ...] = Field(min_length=1)
    candidate_pages_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    provenance: PageDiscoveryProvenance

    @model_validator(mode="after")
    def candidates_are_unique_and_checksummed(self) -> PageDiscoveryInput:
        page_numbers = [candidate.page_number for candidate in self.candidate_pages]
        if len(page_numbers) != len(set(page_numbers)):
            raise ValueError("page-discovery input contains duplicate candidate pages")
        if self.candidate_pages_checksum_sha256 != _candidate_checksum(self.candidate_pages):
            raise ValueError("page-discovery candidate checksum does not match candidate pages")
        if self.request_context_checksum_sha256 != _request_context_checksum(self.request_context):
            raise ValueError(
                "page-discovery request-context checksum does not match request context"
            )
        return self

    def provider_user_payload(self) -> str:
        """Serialize only untrusted document data for a future provider user message."""

        return self.model_dump_json()


class PageDiscoverySelection(DomainModel):
    """One page chosen by a provider from the supplied candidate-page set."""

    page_number: int = Field(ge=1)
    confidence: ConfidenceLevel
    rationale: str = Field(min_length=1)


class PageDiscoveryProposal(DomainModel):
    """A non-authoritative selection from one fixed page-discovery input packet."""

    proposal_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    input_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    request_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_context_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate_pages_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_run: ModelRunProvenance
    selection_status: Literal["selected", "abstain"]
    selected_reporting_basis: ReportingBasis
    selected_period_label: str = Field(min_length=1)
    primary_selection: PageDiscoverySelection | None = None
    supporting_selections: tuple[PageDiscoverySelection, ...] = Field(max_length=4)
    abstention_reason: str | None = None

    @model_validator(mode="after")
    def selection_state_is_consistent(self) -> PageDiscoveryProposal:
        if self.selection_status == "selected":
            if self.primary_selection is None:
                raise ValueError("selected page-discovery proposal requires a primary selection")
            if self.abstention_reason is not None:
                raise ValueError(
                    "selected page-discovery proposal cannot contain an abstention reason"
                )
        elif self.primary_selection is not None or self.supporting_selections:
            raise ValueError("abstained page-discovery proposal cannot select pages")
        elif not self.abstention_reason:
            raise ValueError("abstained page-discovery proposal requires an abstention reason")

        pages = [selection.page_number for selection in self.supporting_selections]
        if self.primary_selection is not None:
            pages.append(self.primary_selection.page_number)
        if len(pages) != len(set(pages)):
            raise ValueError("page-discovery proposal contains duplicate selected pages")
        return self


class PageDiscoveryValidationIssue(DomainModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    page_number: int | None = Field(default=None, ge=1)


class PageDiscoveryValidationResult(DomainModel):
    input_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    proposal_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    validated_primary_page_number: int | None = Field(default=None, ge=1)
    validated_supporting_page_numbers: tuple[int, ...]
    issues: tuple[PageDiscoveryValidationIssue, ...]
    abstention_requested: bool
    ready_for_review: bool

    @model_validator(mode="after")
    def readiness_matches_issues(self) -> PageDiscoveryValidationResult:
        selected_and_valid = not self.abstention_requested and self.validated_primary_page_number
        if self.ready_for_review != (not self.issues and bool(selected_and_valid)):
            raise ValueError("page-discovery readiness requires a valid primary page and no issues")
        if self.abstention_requested and (
            self.validated_primary_page_number is not None or self.validated_supporting_page_numbers
        ):
            raise ValueError("page-discovery abstention cannot retain validated page selections")
        return self


class PageDiscoveryProposalProvider(Protocol):
    """Select candidate pages, but never create coordinates or source facts."""

    def propose(self, discovery_input: PageDiscoveryInput) -> PageDiscoveryProposal:
        """Return a proposal constrained to the supplied candidate-page packet."""
        ...


def validate_page_discovery_proposal(
    discovery_input: PageDiscoveryInput,
    proposal: PageDiscoveryProposal,
) -> PageDiscoveryValidationResult:
    """Reject identity mismatches and page numbers not supplied in the local packet."""

    issues: list[PageDiscoveryValidationIssue] = []
    for field_name in (
        "input_id",
        "request_id",
        "document_id",
        "source_checksum_sha256",
        "request_context_checksum_sha256",
        "candidate_pages_checksum_sha256",
    ):
        if getattr(discovery_input, field_name) != getattr(proposal, field_name):
            issues.append(
                PageDiscoveryValidationIssue(
                    code="identity_mismatch",
                    message=f"proposal {field_name} does not match the page-discovery input",
                )
            )

    if proposal.selected_reporting_basis != discovery_input.request_context.reporting_basis:
        issues.append(
            PageDiscoveryValidationIssue(
                code="reporting_basis_mismatch",
                message=(
                    "proposal reporting basis does not match the page-discovery request context"
                ),
            )
        )
    if proposal.selected_period_label != discovery_input.request_context.period.label:
        issues.append(
            PageDiscoveryValidationIssue(
                code="period_mismatch",
                message="proposal period label does not match the page-discovery request context",
            )
        )

    candidates = {candidate.page_number for candidate in discovery_input.candidate_pages}
    selections = (
        () if proposal.primary_selection is None else (proposal.primary_selection,)
    ) + proposal.supporting_selections
    invalid_pages = {
        selection.page_number for selection in selections if selection.page_number not in candidates
    }
    for page_number in sorted(invalid_pages):
        issues.append(
            PageDiscoveryValidationIssue(
                code="page_not_in_candidates",
                message="proposal selected a page that was not supplied in the candidate packet",
                page_number=page_number,
            )
        )
    primary_page_number = (
        proposal.primary_selection.page_number if proposal.primary_selection is not None else None
    )
    validated_primary = (
        primary_page_number
        if (
            primary_page_number is not None
            and primary_page_number not in invalid_pages
            and not issues
        )
        else None
    )
    validated_supporting = (
        tuple(
            selection.page_number
            for selection in proposal.supporting_selections
            if selection.page_number not in invalid_pages
        )
        if not issues
        else ()
    )
    return PageDiscoveryValidationResult(
        input_id=discovery_input.input_id,
        proposal_id=proposal.proposal_id,
        validated_primary_page_number=validated_primary,
        validated_supporting_page_numbers=validated_supporting,
        issues=tuple(issues),
        abstention_requested=proposal.selection_status == "abstain",
        ready_for_review=not issues and proposal.selection_status == "selected",
    )


class StaticPageDiscoveryProposalProvider:
    """Deterministic page-selection provider for tests; it never makes a model call."""

    def __init__(self, proposal: PageDiscoveryProposal) -> None:
        self._proposal = proposal

    def propose(self, discovery_input: PageDiscoveryInput) -> PageDiscoveryProposal:
        if discovery_input.input_id != self._proposal.input_id:
            raise ValueError("static page-discovery proposal input ID does not match")
        return self._proposal


class PdfPageDiscoveryInputBuilder:
    """Build a bounded candidate-page packet without a network/model call."""

    tool_name = "pdfplumber"

    def build(
        self,
        manifest: RawDocumentManifest,
        raw_root: Path,
        request: DocumentOnboardingRequest,
        *,
        input_id: str,
        policy: PageDiscoveryPolicy,
    ) -> PageDiscoveryInput:
        self._validate_identity(manifest, raw_root, request)
        if request.target_scope is None:
            raise ValueError("page discovery requires an explicit onboarding target scope")
        if manifest.content_type != "application/pdf":
            raise ValueError("page discovery accepts only application/pdf manifests")

        search_terms = _search_terms(request)
        stored_path = raw_root / manifest.stored_relative_path
        with pdfplumber.open(stored_path) as pdf:
            candidates = self._candidate_pages(pdf, search_terms, policy)
            tool_version = str(pdfplumber.__version__)
        if not candidates:
            raise ValueError("page discovery found no bounded textual candidates for the request")

        request_context = _request_context(request)
        return PageDiscoveryInput(
            input_id=input_id,
            request_id=request.request_id,
            document_id=manifest.document_id,
            source_checksum_sha256=manifest.checksum_sha256,
            request_context=request_context,
            request_context_checksum_sha256=_request_context_checksum(request_context),
            candidate_pages=candidates,
            candidate_pages_checksum_sha256=_candidate_checksum(candidates),
            provenance=PageDiscoveryProvenance(
                source_document_id=manifest.document_id,
                policy_version=policy.policy_version,
                policy_checksum_sha256=_policy_checksum(policy),
                extraction_tool=self.tool_name,
                extraction_tool_version=tool_version,
            ),
        )

    @staticmethod
    def _validate_identity(
        manifest: RawDocumentManifest,
        raw_root: Path,
        request: DocumentOnboardingRequest,
    ) -> None:
        verification = verify_raw_document(manifest, raw_root)
        if not verification.valid:
            raise ValueError(f"source PDF verification failed: {verification.message}")
        expected = (
            manifest.document_id,
            manifest.checksum_sha256,
            manifest.source_reference.source_id,
            manifest.source_reference.source_organization,
            manifest.document_type,
        )
        actual = (
            request.document_id,
            request.source_checksum_sha256,
            request.source_reference_id,
            request.source_organization,
            request.document_type,
        )
        if actual != expected:
            raise ValueError("onboarding request identity does not match the source manifest")

    @staticmethod
    def _candidate_pages(
        pdf: PDF,
        search_terms: tuple[str, ...],
        policy: PageDiscoveryPolicy,
    ) -> tuple[PageDiscoveryCandidate, ...]:
        ranked: list[tuple[int, int, str]] = []
        for page_number, page in enumerate(pdf.pages, start=1):
            text = _normalise_text(page.extract_text())
            if not text:
                continue
            lowered = text.casefold()
            # Count distinct matched terms, rather than their repeated occurrences. A contents page
            # or narrative can repeat a generic word many times, whereas a relevant note tends to
            # cover several independent terms from the selected evidence and target scope.
            score = sum(term in lowered for term in search_terms)
            if score:
                ranked.append((score, page_number, _excerpt(text, search_terms, policy)))
        ranked.sort(key=lambda candidate: (-candidate[0], candidate[1]))
        return tuple(
            PageDiscoveryCandidate(
                page_number=page_number,
                lexical_score=score,
                excerpt=excerpt,
            )
            for score, page_number, excerpt in ranked[: policy.maximum_candidates]
        )


def _search_terms(request: DocumentOnboardingRequest) -> tuple[str, ...]:
    """Derive generic lexical signals from the bounded request, without company alias maps."""

    if request.target_scope is None:
        raise ValueError("page discovery requires an explicit onboarding target scope")
    scope_terms = " ".join(
        metric_id.value.replace("_", " ") for metric_id in request.target_scope.metric_ids
    )
    evidence_terms = " ".join(row.reported_label for row in request.evidence_rows)
    tokens = re.findall(r"[a-zA-Z]{4,}", f"{scope_terms} {evidence_terms}".casefold())
    return tuple(dict.fromkeys(tokens))


def _excerpt(text: str, search_terms: tuple[str, ...], policy: PageDiscoveryPolicy) -> str:
    lowered = text.casefold()
    positions = [
        match.start() for term in search_terms for match in re.finditer(re.escape(term), lowered)
    ]
    window_size = policy.maximum_excerpt_characters
    starts = {max(0, position - window_size // 4) for position in positions}
    candidates = [(start, lowered[start : start + window_size]) for start in starts]
    best_start, _ = max(
        candidates,
        key=lambda candidate: (
            sum(term in candidate[1] for term in search_terms),
            sum(candidate[1].count(term) for term in search_terms),
            -candidate[0],
        ),
    )
    return text[best_start : best_start + window_size]


def _normalise_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _candidate_checksum(candidates: tuple[PageDiscoveryCandidate, ...]) -> str:
    serialized = json.dumps(
        [candidate.model_dump(mode="json") for candidate in candidates],
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _request_context(request: DocumentOnboardingRequest) -> PageDiscoveryRequestContext:
    if request.target_scope is None:
        raise ValueError("page discovery requires an explicit onboarding target scope")
    return PageDiscoveryRequestContext(
        company_id=request.company_id,
        reporting_basis=request.reporting_basis,
        period=request.period,
        target_scope_id=request.target_scope.scope_id,
        target_metric_ids=request.target_scope.metric_ids,
        purpose=request.target_scope.purpose,
        evidence_anchors=tuple(
            PageDiscoveryEvidenceAnchor(
                evidence_id=row.evidence_id,
                page_number=row.source_locator.page_number,
                table_id=row.source_locator.table_id,
                row_number=row.source_locator.row_number,
                column_name=row.source_locator.column_name,
                reported_label=row.reported_label,
            )
            for row in request.evidence_rows
        ),
    )


def _request_context_checksum(context: PageDiscoveryRequestContext) -> str:
    serialized = json.dumps(context.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _policy_checksum(policy: PageDiscoveryPolicy) -> str:
    serialized = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
