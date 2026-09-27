"""Append-only local catalog for document-extraction links."""

from pathlib import Path

from indian_company_analysis.data.extraction.models import DocumentExtractionLink


class LocalExtractionLinkCatalog:
    def __init__(self, catalog_root: Path) -> None:
        self._catalog_root = catalog_root

    def register(self, link: DocumentExtractionLink) -> bool:
        path = self._catalog_root / f"{link.extraction_id}.json"
        serialized = link.model_dump_json(indent=2) + "\n"
        self._catalog_root.mkdir(parents=True, exist_ok=True)
        try:
            with path.open("x", encoding="utf-8") as catalog_file:
                catalog_file.write(serialized)
        except FileExistsError:
            if path.read_text(encoding="utf-8") != serialized:
                raise ValueError(
                    f"catalog already contains a different link for {link.extraction_id}"
                ) from None
            return False
        return True
