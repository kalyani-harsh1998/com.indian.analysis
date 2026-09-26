"""Content-addressed, copy-only storage for locally supplied source documents."""

from __future__ import annotations

import hashlib
import mimetypes
import os
import shutil
import tempfile
from pathlib import Path

from indian_company_analysis.data.ingestion.models import (
    DocumentIngestionResult,
    LocalDocumentIntakeRequest,
    RawDocumentManifest,
)
from indian_company_analysis.domain.models import SourceReference

_HASH_CHUNK_SIZE = 1024 * 1024


def sha256_file(path: Path) -> str:
    """Return a SHA-256 digest without loading a potentially large filing into memory."""

    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(_HASH_CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


class ImmutableRawDocumentStore:
    """Copy locally provided evidence into a content-addressed immutable raw-data zone."""

    def __init__(self, raw_root: Path) -> None:
        self._raw_root = raw_root

    def ingest(self, request: LocalDocumentIntakeRequest) -> DocumentIngestionResult:
        input_path = request.input_path
        if input_path.is_symlink() or not input_path.is_file():
            raise ValueError("input_path must be an existing regular file, not a symlink")

        checksum = sha256_file(input_path)
        suffix = self._safe_suffix(input_path)
        stored_path = self._raw_root / checksum[:2] / f"{checksum}{suffix}"
        storage_created = self._copy_if_absent(input_path, stored_path, checksum)
        content_type = mimetypes.guess_type(input_path.name)[0] or "application/octet-stream"
        source_reference = SourceReference(
            source_id=request.document_id,
            source_kind=request.source_kind,
            source_organization=request.source_organization,
            source_document=request.source_document,
            locator=request.source_locator,
            retrieval_timestamp=request.retrieved_at,
            publication_date=request.source_publication_date,
            checksum_sha256=checksum,
            parser_version=request.parser_version,
            is_synthetic=request.is_synthetic,
        )
        manifest = RawDocumentManifest(
            document_id=request.document_id,
            company_id=request.company_id,
            document_type=request.document_type,
            source_reference=source_reference,
            licence_category=request.licence_category,
            original_filename=input_path.name,
            content_type=content_type,
            byte_size=input_path.stat().st_size,
            checksum_sha256=checksum,
            stored_relative_path=stored_path.relative_to(self._raw_root).as_posix(),
            ingested_at=request.retrieved_at,
        )
        return DocumentIngestionResult(manifest=manifest, storage_created=storage_created)

    @staticmethod
    def _safe_suffix(input_path: Path) -> str:
        suffix = input_path.suffix.lower()
        return suffix if suffix and suffix[1:].isalnum() and len(suffix) <= 16 else ""

    @staticmethod
    def _copy_if_absent(input_path: Path, stored_path: Path, checksum: str) -> bool:
        stored_path.parent.mkdir(parents=True, exist_ok=True)
        if stored_path.exists():
            if sha256_file(stored_path) != checksum:
                raise RuntimeError("content-addressed target exists with an unexpected checksum")
            return False

        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(dir=stored_path.parent, delete=False) as temporary:
                temporary_name = temporary.name
                with input_path.open("rb") as source:
                    shutil.copyfileobj(source, temporary, length=_HASH_CHUNK_SIZE)
                temporary.flush()
                os.fsync(temporary.fileno())
            temporary_path = Path(temporary_name)
            if sha256_file(temporary_path) != checksum:
                raise RuntimeError("input changed while it was being ingested")
            try:
                os.link(temporary_path, stored_path)
            except FileExistsError:
                if sha256_file(stored_path) != checksum:
                    raise RuntimeError(
                        "content-addressed target exists with an unexpected checksum"
                    ) from None
                return False
            stored_path.chmod(0o444)
            return True
        finally:
            if temporary_name is not None:
                Path(temporary_name).unlink(missing_ok=True)
