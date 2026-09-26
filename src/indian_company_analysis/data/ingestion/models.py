"""Strict records for local document intake and raw-evidence verification."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

from pydantic import Field, field_validator, model_validator

from indian_company_analysis.domain.enums import DocumentType, LicenceCategory, SourceKind
from indian_company_analysis.domain.models import DomainModel, SourceReference


class LocalDocumentIntakeRequest(DomainModel):
    """Metadata supplied when a permitted document is manually placed locally."""

    document_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    company_id: str = Field(min_length=1)
    document_type: DocumentType
    source_kind: SourceKind
    source_organization: str = Field(min_length=1)
    source_document: str = Field(min_length=1)
    source_locator: str = Field(min_length=1)
    source_publication_date: date | None = None
    retrieved_at: datetime
    licence_category: LicenceCategory
    input_path: Path
    parser_version: str | None = None
    is_synthetic: bool = False

    @model_validator(mode="after")
    def synthetic_flag_matches_kind(self) -> LocalDocumentIntakeRequest:
        if (self.source_kind is SourceKind.SYNTHETIC) != self.is_synthetic:
            raise ValueError("synthetic source kind and is_synthetic flag must agree")
        return self


class RawDocumentManifest(DomainModel):
    """A durable, evidence-bearing pointer to exactly one raw document version."""

    document_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    company_id: str = Field(min_length=1)
    document_type: DocumentType
    source_reference: SourceReference
    licence_category: LicenceCategory
    original_filename: str = Field(min_length=1)
    content_type: str = Field(min_length=1)
    byte_size: int = Field(gt=0)
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    stored_relative_path: str = Field(min_length=1)
    ingested_at: datetime
    storage_version: str = Field(default="1.0.0", min_length=1)

    @field_validator("stored_relative_path")
    @classmethod
    def stored_path_is_safe_relative_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("stored_relative_path must remain below the raw-data root")
        return value

    @model_validator(mode="after")
    def checksum_matches_source_reference(self) -> RawDocumentManifest:
        if self.source_reference.checksum_sha256 != self.checksum_sha256:
            raise ValueError("manifest checksum must match its source reference checksum")
        return self


class DocumentIngestionResult(DomainModel):
    manifest: RawDocumentManifest
    storage_created: bool


class RawDocumentVerificationResult(DomainModel):
    document_id: str
    valid: bool
    message: str
    actual_checksum_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
