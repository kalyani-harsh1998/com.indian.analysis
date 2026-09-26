"""Immutable local-document intake and verification."""

from indian_company_analysis.data.ingestion.local_intake import ImmutableRawDocumentStore
from indian_company_analysis.data.ingestion.models import (
    DocumentIngestionResult,
    LocalDocumentIntakeRequest,
    RawDocumentManifest,
    RawDocumentVerificationResult,
)
from indian_company_analysis.data.ingestion.verification import verify_raw_document

__all__ = [
    "DocumentIngestionResult",
    "ImmutableRawDocumentStore",
    "LocalDocumentIntakeRequest",
    "RawDocumentManifest",
    "RawDocumentVerificationResult",
    "verify_raw_document",
]
