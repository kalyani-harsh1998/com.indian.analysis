"""Local registry records for controlled onboarding evaluation corpus cases."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from indian_company_analysis.data.extraction.models import DocumentExtractionLink
from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.onboarding.catalog import _safe_path_component
from indian_company_analysis.data.onboarding.evaluation import OnboardingEvaluationFixture
from indian_company_analysis.data.onboarding.models import DocumentOnboardingRequest
from indian_company_analysis.domain.enums import ExtractionReviewStatus, LicenceCategory
from indian_company_analysis.domain.models import DomainModel

CorpusScope = Literal["synthetic", "permitted_real"]
CorpusReviewStatus = Literal[
    "ready_for_ca_review",
    "provisional_internal_review",
    "approved_for_evaluation",
    "rejected",
]


class EvaluationCorpusEntry(DomainModel):
    """One controlled real-filing golden case with complete lineage.

    The registry stores only local metadata and the reviewed golden fixture.  Raw source
    documents and any locally generated evaluation reports remain outside Git.
    """

    entry_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    corpus_version: str = Field(min_length=1)
    corpus_scope: CorpusScope
    source_manifest: RawDocumentManifest
    extraction_link: DocumentExtractionLink
    onboarding_request: DocumentOnboardingRequest
    fixture: OnboardingEvaluationFixture | None = None
    fixture_checksum_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    review_status: CorpusReviewStatus
    reviewed_by: str | None = None
    reviewed_at: datetime | None = None
    review_policy_version: str | None = None
    review_notes: tuple[str, ...] = ()

    @model_validator(mode="after")
    def lineage_and_review_state_are_consistent(self) -> EvaluationCorpusEntry:
        source = self.source_manifest
        request = self.onboarding_request
        link = self.extraction_link

        if self.corpus_scope == "synthetic":
            if not source.source_reference.is_synthetic:
                raise ValueError("synthetic corpus entries require a synthetic source manifest")
        elif source.source_reference.is_synthetic:
            raise ValueError("permitted_real corpus entries cannot use synthetic source manifests")
        elif source.licence_category in {
            LicenceCategory.UNASSESSED,
            LicenceCategory.RESTRICTED,
        }:
            raise ValueError(
                "permitted_real corpus entries require a non-restricted assessed licence"
            )

        if (
            request.document_id != source.document_id
            or request.company_id != source.company_id
            or request.document_type is not source.document_type
            or request.source_reference_id != source.source_reference.source_id
            or request.source_checksum_sha256 != source.checksum_sha256
            or request.source_organization != source.source_reference.source_organization
        ):
            raise ValueError("onboarding request must match its raw source manifest")
        if (
            link.source_document_id != source.document_id
            or link.source_document_type is not source.document_type
            or link.source_checksum_sha256 != source.checksum_sha256
            or link.extraction_id != request.extraction_id
            or link.profile_version != request.extraction_profile_version
        ):
            raise ValueError(
                "extraction link must match the source manifest and onboarding request"
            )
        if link.review_status is not ExtractionReviewStatus.REVIEWED:
            raise ValueError("evaluation corpus entries require a reviewed extraction link")

        review_metadata = (
            self.reviewed_by,
            self.reviewed_at,
            self.review_policy_version,
        )
        if any(note == "" for note in self.review_notes):
            raise ValueError("review notes must not be blank")
        if self.fixture is not None:
            if self.fixture.request != request:
                raise ValueError(
                    "evaluation fixture request must match the corpus onboarding request"
                )
            expected_checksum = _fixture_checksum(self.fixture)
            if self.fixture_checksum_sha256 != expected_checksum:
                raise ValueError("fixture checksum must match the canonical fixture contents")
        elif self.fixture_checksum_sha256 is not None:
            raise ValueError("fixture checksum requires an evaluation fixture")

        if self.review_status == "ready_for_ca_review":
            if self.fixture is None:
                raise ValueError("CA review requires a candidate evaluation fixture")
            if any(value is not None for value in review_metadata) or self.review_notes:
                raise ValueError("unreviewed corpus entries cannot carry CA review metadata")
        elif self.review_status == "provisional_internal_review":
            if self.corpus_scope != "permitted_real":
                raise ValueError(
                    "only permitted_real corpus cases may receive provisional internal review"
                )
            if self.fixture is None or any(value is None for value in review_metadata):
                raise ValueError(
                    "provisional internal review requires fixture and reviewer metadata"
                )
            if not self.review_notes:
                raise ValueError("provisional internal review requires reviewer notes")
            if self.reviewed_at is None or (
                self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None
            ):
                raise ValueError("provisional internal review timestamp must include a timezone")
        elif self.review_status == "approved_for_evaluation":
            if self.corpus_scope != "permitted_real":
                raise ValueError("only permitted_real corpus cases may be approved for evaluation")
            if self.fixture is None or any(value is None for value in review_metadata):
                raise ValueError("approved corpus entries require fixture and CA review metadata")
            if not self.review_notes:
                raise ValueError("approved corpus entries require CA review notes")
            if self.reviewed_at is None or (
                self.reviewed_at.tzinfo is None or self.reviewed_at.utcoffset() is None
            ):
                raise ValueError("approved corpus review timestamp must include a timezone")
        else:
            if any(value is None for value in review_metadata) or not self.review_notes:
                raise ValueError("rejected corpus entries require reviewer metadata and reasons")
            if self.fixture is not None:
                raise ValueError("rejected corpus entries must not retain an evaluable fixture")
        return self

    @property
    def is_approved_for_evaluation(self) -> bool:
        """Whether this case is eligible to act as a real-model quality gate."""

        return self.review_status == "approved_for_evaluation"

    @property
    def is_provisionally_reviewed_for_internal_evaluation(self) -> bool:
        """Whether this case may be used only for clearly labelled internal testing."""

        return self.review_status == "provisional_internal_review"


def _fixture_checksum(fixture: OnboardingEvaluationFixture) -> str:
    """Return a reproducible digest of the complete golden fixture, including values."""

    serialized = json.dumps(
        fixture.model_dump(mode="json"),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def provisionally_review_entry(
    entry: EvaluationCorpusEntry,
    *,
    corpus_version: str,
    reviewed_by: str,
    reviewed_at: datetime,
    review_policy_version: str,
    review_notes: tuple[str, ...],
) -> EvaluationCorpusEntry:
    """Create a new append-only internal-review version from a candidate entry."""

    if entry.review_status != "ready_for_ca_review":
        raise ValueError("only a ready_for_ca_review entry may receive provisional internal review")
    entry_data = entry.model_dump(mode="json")
    entry_data.update(
        {
            "corpus_version": corpus_version,
            "review_status": "provisional_internal_review",
            "reviewed_by": reviewed_by,
            "reviewed_at": reviewed_at,
            "review_policy_version": review_policy_version,
            "review_notes": review_notes,
        }
    )
    return EvaluationCorpusEntry.model_validate(entry_data)


class LocalEvaluationCorpusCatalog:
    """Append-only local store for evaluation-corpus registry entries."""

    def __init__(self, catalog_root: Path) -> None:
        self._catalog_root = catalog_root

    def register(self, entry: EvaluationCorpusEntry) -> bool:
        path = self.path_for(entry)
        serialized = entry.model_dump_json(indent=2) + "\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as catalog_file:
                catalog_file.write(serialized)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != serialized:
                raise ValueError(f"catalog already contains a different record at {path}") from None
            return False
        return True

    def get_approved(
        self,
        *,
        entry_id: str,
        corpus_version: str,
    ) -> EvaluationCorpusEntry:
        entry = EvaluationCorpusEntry.model_validate_json(
            self._path_for(entry_id=entry_id, corpus_version=corpus_version).read_text(
                encoding="utf-8"
            )
        )
        if entry.entry_id != entry_id or entry.corpus_version != corpus_version:
            raise ValueError("evaluation corpus entry identity does not match its catalog path")
        if not entry.is_approved_for_evaluation:
            raise ValueError("evaluation corpus entry has not received CA approval")
        return entry

    def get_provisionally_reviewed_for_internal_evaluation(
        self,
        *,
        entry_id: str,
        corpus_version: str,
    ) -> EvaluationCorpusEntry:
        """Return only an explicitly provisional entry for internal evaluation."""

        entry = EvaluationCorpusEntry.model_validate_json(
            self._path_for(entry_id=entry_id, corpus_version=corpus_version).read_text(
                encoding="utf-8"
            )
        )
        if entry.entry_id != entry_id or entry.corpus_version != corpus_version:
            raise ValueError("evaluation corpus entry identity does not match its catalog path")
        if not entry.is_provisionally_reviewed_for_internal_evaluation:
            raise ValueError("evaluation corpus entry has not received provisional internal review")
        return entry

    def path_for(self, entry: EvaluationCorpusEntry) -> Path:
        return self._path_for(entry_id=entry.entry_id, corpus_version=entry.corpus_version)

    def _path_for(self, *, entry_id: str, corpus_version: str) -> Path:
        safe_entry_id = _safe_path_component(entry_id, field_name="entry_id")
        safe_version = _safe_path_component(corpus_version, field_name="corpus_version")
        return self._catalog_root / safe_entry_id / f"{safe_version}.json"
