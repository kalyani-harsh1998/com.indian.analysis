"""Append-only local catalog of raw-document manifests."""

from __future__ import annotations

from pathlib import Path

from indian_company_analysis.data.ingestion.models import RawDocumentManifest


class LocalManifestCatalog:
    """Persist a manifest once; refuse a conflicting record for the same document ID."""

    def __init__(self, catalog_root: Path) -> None:
        self._catalog_root = catalog_root

    def register(self, manifest: RawDocumentManifest) -> bool:
        path = self._catalog_root / f"{manifest.document_id}.json"
        serialized = manifest.model_dump_json(indent=2) + "\n"
        self._catalog_root.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as catalog_file:
                catalog_file.write(serialized)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != serialized:
                raise ValueError(
                    f"catalog already contains a different manifest for {manifest.document_id}"
                ) from None
            return False
        return True
