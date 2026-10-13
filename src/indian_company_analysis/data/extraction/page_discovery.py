"""Bounded, source-verified page candidates for future LLM-assisted discovery."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pdfplumber
from pdfplumber.pdf import PDF
from pydantic import Field, model_validator

from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document
from indian_company_analysis.data.onboarding.models import DocumentOnboardingRequest
from indian_company_analysis.domain.models import DomainModel


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


class PageDiscoveryInput(DomainModel):
    """Checksummed, prompt-safe candidate-page packet for a discovery provider.

    This does not grant a provider PDF access. A provider may select only from candidates already
    included in this packet; it cannot create a final extraction profile or approve evidence.
    """

    input_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    request_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    document_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    target_scope_id: str = Field(min_length=1)
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
        return self

    def provider_user_payload(self) -> str:
        """Serialize only untrusted document data for a future provider user message."""

        return self.model_dump_json()


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

        return PageDiscoveryInput(
            input_id=input_id,
            request_id=request.request_id,
            document_id=manifest.document_id,
            source_checksum_sha256=manifest.checksum_sha256,
            target_scope_id=request.target_scope.scope_id,
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


def _policy_checksum(policy: PageDiscoveryPolicy) -> str:
    serialized = json.dumps(policy.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
