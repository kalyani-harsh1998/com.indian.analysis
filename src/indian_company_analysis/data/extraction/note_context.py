"""Deterministic, source-verified extraction of small PDF note-context regions."""

from __future__ import annotations

import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

import pdfplumber
from pdfplumber.pdf import PDF

from indian_company_analysis.data.extraction.models import (
    PdfNoteContextExtractionSpec,
    PdfNoteContextSnippetSpec,
)
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document
from indian_company_analysis.data.onboarding.model_input import (
    LocatorBoundContextBundle,
    LocatorBoundContextProvenance,
    LocatorBoundContextSnippet,
)
from indian_company_analysis.data.onboarding.models import DocumentOnboardingRequest


class PdfNoteContextExtractor:
    """Extract configured note-text regions without inferring their accounting meaning.

    Every region must be supplied in a versioned profile. The extractor verifies the immutable
    source file and request identity before producing a checksummed context bundle. It does not
    search a filing, select pages, call a provider, or treat extracted text as an approved fact.
    """

    tool_name = "pdfplumber"

    def extract(
        self,
        manifest: RawDocumentManifest,
        raw_root: Path,
        request: DocumentOnboardingRequest,
        spec: PdfNoteContextExtractionSpec,
    ) -> LocatorBoundContextBundle:
        """Return a bounded bundle of configured text excerpts from a verified source PDF."""

        self._validate_identity(manifest, raw_root, request)
        if request.target_scope is None:
            raise ValueError("note-context extraction requires an explicit onboarding target scope")
        if manifest.content_type != "application/pdf":
            raise ValueError("note-context extraction accepts only application/pdf manifests")

        allowed_metric_ids = set(request.target_scope.metric_ids)
        for snippet_spec in spec.snippets:
            if not set(snippet_spec.metric_ids) <= allowed_metric_ids:
                raise ValueError(
                    "note-context snippet targets are outside the onboarding target scope"
                )

        stored_path = raw_root / manifest.stored_relative_path
        with pdfplumber.open(stored_path) as pdf:
            snippets = tuple(
                self._extract_snippet(pdf, snippet_spec) for snippet_spec in spec.snippets
            )

        return LocatorBoundContextBundle.for_request(
            request,
            bundle_id=spec.bundle_id,
            snippets=snippets,
            extraction_provenance=LocatorBoundContextProvenance(
                source_document_id=manifest.document_id,
                extraction_profile_version=spec.profile_version,
                extraction_profile_checksum_sha256=_profile_checksum(spec),
                extraction_tool=self.tool_name,
                extraction_tool_version=str(pdfplumber.__version__),
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

    @classmethod
    def _extract_snippet(
        cls,
        pdf: PDF,
        snippet_spec: PdfNoteContextSnippetSpec,
    ) -> LocatorBoundContextSnippet:
        page_number = snippet_spec.source_locator.page_number
        if page_number > len(pdf.pages):
            raise ValueError("note-context source page does not exist in the source PDF")
        page = pdf.pages[page_number - 1]
        cls._validate_crop_bounds(
            snippet_spec.x0,
            snippet_spec.top,
            snippet_spec.x1,
            snippet_spec.bottom,
            page_width=Decimal(str(page.width)),
            page_height=Decimal(str(page.height)),
        )
        cropped_page = page.crop(
            (
                float(snippet_spec.x0),
                float(snippet_spec.top),
                float(snippet_spec.x1),
                float(snippet_spec.bottom),
            )
        )
        extracted = cropped_page.extract_text(
            x_tolerance=float(snippet_spec.x_tolerance),
            y_tolerance=float(snippet_spec.y_tolerance),
        )
        text = cls._normalise_text(extracted)
        if not text:
            raise ValueError(f"note-context region {snippet_spec.context_id!r} contains no text")
        if len(text) > snippet_spec.maximum_characters:
            raise ValueError(
                f"note-context region {snippet_spec.context_id!r} exceeds its character limit"
            )
        return LocatorBoundContextSnippet(
            context_id=snippet_spec.context_id,
            source_locator=snippet_spec.source_locator,
            metric_ids=snippet_spec.metric_ids,
            text=text,
        )

    @staticmethod
    def _validate_crop_bounds(
        x0: Decimal,
        top: Decimal,
        x1: Decimal,
        bottom: Decimal,
        *,
        page_width: Decimal,
        page_height: Decimal,
    ) -> None:
        if x1 > page_width or bottom > page_height:
            raise ValueError("note-context region exceeds the source PDF page bounds")
        if x0 >= page_width or top >= page_height:
            raise ValueError("note-context region starts outside the source PDF page bounds")

    @staticmethod
    def _normalise_text(extracted: str | None) -> str:
        """Produce one prompt-safe textual representation without retaining layout controls."""

        if extracted is None:
            return ""
        text = re.sub(r"\s+", " ", extracted).strip()
        if any(ord(character) < 32 for character in text):
            raise ValueError("note-context text contains unsupported control characters")
        return text


def _profile_checksum(spec: PdfNoteContextExtractionSpec) -> str:
    serialized = json.dumps(
        spec.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
