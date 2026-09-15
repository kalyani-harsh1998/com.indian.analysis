"""Command-line entry point for local POC workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from indian_company_analysis.config import Settings
from indian_company_analysis.data.sources.local_files import LocalFixtureDataSource
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
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    settings = Settings.from_environment()
    args = build_parser(settings).parse_args(argv)
    if args.command == "demo":
        result = CompanyAnalysisWorkflow(LocalFixtureDataSource(args.fixture)).run()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(result.model_dump_json(indent=2), encoding="utf-8")
        print(f"Synthetic demo written to {args.output}")
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
