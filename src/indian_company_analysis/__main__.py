"""Command-line entry point for local POC workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from indian_company_analysis.config import Settings
from indian_company_analysis.data.ingestion.local_intake import ImmutableRawDocumentStore
from indian_company_analysis.data.ingestion.manifest_catalog import LocalManifestCatalog
from indian_company_analysis.data.ingestion.models import (
    LocalDocumentIntakeRequest,
    RawDocumentManifest,
)
from indian_company_analysis.data.normalization.csv_parser import ControlledCsvFinancialParser
from indian_company_analysis.data.normalization.models import MetricMappingSet
from indian_company_analysis.data.sources.local_files import LocalFixtureDataSource
from indian_company_analysis.domain.enums import DocumentType, LicenceCategory, SourceKind
from indian_company_analysis.workflows.company_analysis import CompanyAnalysisWorkflow


def build_parser(settings: Settings) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Indian company analysis POC")
    subparsers = parser.add_subparsers(dest="command", required=True)
    demo = subparsers.add_parser("demo", help="run the synthetic deterministic demo")
    demo.add_argument(
        "--fixture",
        type=Path,
        default=settings.data_directory / "fixtures" / "demo" / "it_services.json",
    )
    demo.add_argument(
        "--output",
        type=Path,
        default=settings.output_directory / "demo_analysis.json",
    )
    intake = subparsers.add_parser(
        "intake", help="copy a manually supplied document into immutable local raw storage"
    )
    intake.add_argument("--file", type=Path, required=True)
    intake.add_argument("--document-id", required=True)
    intake.add_argument("--company-id", required=True)
    intake.add_argument("--document-type", choices=list(DocumentType), required=True)
    intake.add_argument("--source-kind", choices=list(SourceKind), required=True)
    intake.add_argument("--source-organization", required=True)
    intake.add_argument("--source-document", required=True)
    intake.add_argument("--source-locator", required=True)
    intake.add_argument("--publication-date", type=date.fromisoformat)
    intake.add_argument(
        "--licence-category", choices=list(LicenceCategory), default=LicenceCategory.UNASSESSED
    )
    intake.add_argument("--synthetic", action="store_true")
    normalize = subparsers.add_parser(
        "normalize-csv",
        help="normalize a verified controlled CSV through an explicit metric mapping",
    )
    normalize.add_argument("--manifest", type=Path, required=True)
    normalize.add_argument("--mapping", type=Path, required=True)
    normalize.add_argument("--output", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    settings = Settings.from_environment()
    args = build_parser(settings).parse_args(argv)
    if args.command == "demo":
        analysis_result = CompanyAnalysisWorkflow(LocalFixtureDataSource(args.fixture)).run()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(analysis_result.model_dump_json(indent=2), encoding="utf-8")
        print(f"Synthetic demo written to {args.output}")
        return 0
    if args.command == "intake":
        request = LocalDocumentIntakeRequest(
            document_id=args.document_id,
            company_id=args.company_id,
            document_type=args.document_type,
            source_kind=args.source_kind,
            source_organization=args.source_organization,
            source_document=args.source_document,
            source_locator=args.source_locator,
            source_publication_date=args.publication_date,
            retrieved_at=datetime.now(UTC),
            licence_category=args.licence_category,
            input_path=args.file,
            is_synthetic=args.synthetic,
        )
        raw_store = ImmutableRawDocumentStore(settings.data_directory / "raw")
        ingestion_result = raw_store.ingest(request)
        catalog = LocalManifestCatalog(settings.data_directory / "interim" / "manifests")
        catalog_created = catalog.register(ingestion_result.manifest)
        action = "stored" if ingestion_result.storage_created else "already present"
        catalog_action = "registered" if catalog_created else "already registered"
        print(
            f"Raw document {action}; manifest {catalog_action}: "
            f"{ingestion_result.manifest.document_id}"
        )
        return 0
    if args.command == "normalize-csv":
        manifest = RawDocumentManifest.model_validate_json(
            args.manifest.read_text(encoding="utf-8")
        )
        mapping_set = MetricMappingSet.model_validate_json(args.mapping.read_text(encoding="utf-8"))
        batch = ControlledCsvFinancialParser().parse(
            manifest,
            settings.data_directory / "raw",
            mapping_set,
        )
        output = args.output or (
            settings.data_directory
            / "processed"
            / "normalized"
            / manifest.document_id
            / f"{batch.parser_version}--{batch.mapping_version}.json"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = batch.model_dump_json(indent=2) + "\n"
        if output.exists() and output.read_text(encoding="utf-8") != serialized:
            raise ValueError(f"refusing to overwrite different normalized output: {output}")
        output.write_text(serialized, encoding="utf-8")
        status = "ready for analysis" if batch.ready_for_analysis else "has normalization issues"
        print(f"Normalized {batch.total_rows} rows to {output}; result {status}")
        return 0 if batch.ready_for_analysis else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
