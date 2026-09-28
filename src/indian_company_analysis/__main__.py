"""Command-line entry point for local POC workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import UTC, date, datetime
from pathlib import Path

from indian_company_analysis.config import Settings
from indian_company_analysis.data.extraction.models import DocumentExtractionLink
from indian_company_analysis.data.ingestion.local_intake import ImmutableRawDocumentStore
from indian_company_analysis.data.ingestion.manifest_catalog import LocalManifestCatalog
from indian_company_analysis.data.ingestion.models import (
    LocalDocumentIntakeRequest,
    RawDocumentManifest,
)
from indian_company_analysis.data.normalization.csv_parser import ControlledCsvFinancialParser
from indian_company_analysis.data.normalization.models import MetricMappingSet
from indian_company_analysis.data.onboarding.catalog import (
    LocalOnboardingConfigurationCatalog,
    LocalOnboardingReviewCatalog,
)
from indian_company_analysis.data.onboarding.evaluation import (
    OnboardingEvaluationFixture,
    OnboardingProposalEvaluator,
)
from indian_company_analysis.data.onboarding.models import (
    ApprovedOnboardingConfiguration,
    DocumentOnboardingProposal,
    DocumentOnboardingRequest,
)
from indian_company_analysis.data.onboarding.normalization_workflow import (
    OnboardingNormalizationWorkflow,
)
from indian_company_analysis.data.onboarding.reuse import OnboardingReuseAssessor
from indian_company_analysis.data.onboarding.review import approve_proposal, reject_proposal
from indian_company_analysis.data.onboarding.static_provider import StaticProposalProvider
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
    onboarding = subparsers.add_parser(
        "normalize-onboarding",
        help="persist reviewed direct mappings and aggregations as one normalized batch",
    )
    onboarding.add_argument("--source-manifest", type=Path, required=True)
    onboarding.add_argument("--extraction-manifest", type=Path, required=True)
    onboarding.add_argument("--extraction-link", type=Path, required=True)
    onboarding.add_argument("--request", type=Path, required=True)
    onboarding.add_argument("--configuration", type=Path, required=True)
    onboarding.add_argument("--output", type=Path)
    evaluation = subparsers.add_parser(
        "evaluate-onboarding",
        help="score a saved onboarding proposal against a versioned golden fixture",
    )
    evaluation.add_argument("--fixture", type=Path, required=True)
    evaluation.add_argument("--proposal", type=Path, required=True)
    evaluation.add_argument("--evaluated-at", type=datetime.fromisoformat)
    evaluation.add_argument("--output", type=Path)
    approve = subparsers.add_parser(
        "approve-onboarding",
        help="record human approval and register its reviewed onboarding configuration",
    )
    _add_review_inputs(approve)
    approve.add_argument("--configuration-version", required=True)
    approve.add_argument("--aggregation-rule-version", required=True)
    reject = subparsers.add_parser(
        "reject-onboarding",
        help="record a human rejection without changing the original proposal",
    )
    _add_review_inputs(reject)
    reject.add_argument(
        "--rejection-reason",
        action="append",
        required=True,
        help="repeat for each reviewer rejection reason",
    )
    reuse = subparsers.add_parser(
        "assess-onboarding-reuse",
        help="compare a reviewed configuration with a new filing without applying it",
    )
    reuse.add_argument("--configuration", type=Path, required=True)
    reuse.add_argument("--request", type=Path, required=True)
    reuse.add_argument("--assessment-id", required=True)
    reuse.add_argument("--assessed-at", type=datetime.fromisoformat, required=True)
    reuse.add_argument("--output", type=Path)
    return parser


def _add_review_inputs(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--proposal", type=Path, required=True)
    parser.add_argument("--decision-id", required=True)
    parser.add_argument("--reviewed-by", required=True)
    parser.add_argument("--reviewed-at", type=datetime.fromisoformat, required=True)
    parser.add_argument("--approval-policy-version", required=True)
    parser.add_argument("--review-rationale", required=True)


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
    if args.command == "normalize-onboarding":
        source_manifest = RawDocumentManifest.model_validate_json(
            args.source_manifest.read_text(encoding="utf-8")
        )
        extraction_manifest = RawDocumentManifest.model_validate_json(
            args.extraction_manifest.read_text(encoding="utf-8")
        )
        extraction_link = DocumentExtractionLink.model_validate_json(
            args.extraction_link.read_text(encoding="utf-8")
        )
        onboarding_request = DocumentOnboardingRequest.model_validate_json(
            args.request.read_text(encoding="utf-8")
        )
        configuration = ApprovedOnboardingConfiguration.model_validate_json(
            args.configuration.read_text(encoding="utf-8")
        )
        workflow = OnboardingNormalizationWorkflow()
        onboarding_batch = workflow.normalize(
            source_manifest=source_manifest,
            extraction_manifest=extraction_manifest,
            extraction_link=extraction_link,
            request=onboarding_request,
            configuration=configuration,
            raw_root=settings.data_directory / "raw",
        )
        output = args.output or (
            settings.data_directory
            / "processed"
            / "normalized"
            / onboarding_request.document_id
            / f"{workflow.parser_version}--{configuration.configuration_version}.json"
        )
        workflow.persist(onboarding_batch, output)
        status = (
            "ready for analysis"
            if onboarding_batch.ready_for_analysis
            else "has blockers or issues"
        )
        print(
            f"Normalized {onboarding_batch.total_evidence_rows} onboarding rows to {output}; "
            f"result {status}"
        )
        return 0 if onboarding_batch.ready_for_analysis else 1
    if args.command == "evaluate-onboarding":
        fixture = OnboardingEvaluationFixture.model_validate_json(
            args.fixture.read_text(encoding="utf-8")
        )
        proposal = DocumentOnboardingProposal.model_validate_json(
            args.proposal.read_text(encoding="utf-8")
        )
        evaluator = OnboardingProposalEvaluator()
        report = evaluator.evaluate(
            fixture,
            StaticProposalProvider(proposal),
            evaluated_at=args.evaluated_at or datetime.now(UTC),
        )
        output = args.output or (
            settings.data_directory
            / "interim"
            / "evaluations"
            / fixture.case_id
            / f"{proposal.proposal_id}.json"
        )
        evaluator.persist(report, output)
        status = "passed" if report.passed else "failed"
        print(f"Evaluated proposal {proposal.proposal_id} to {output}; result {status}")
        return 0 if report.passed else 1
    if args.command in {"approve-onboarding", "reject-onboarding"}:
        onboarding_request = DocumentOnboardingRequest.model_validate_json(
            args.request.read_text(encoding="utf-8")
        )
        proposal = DocumentOnboardingProposal.model_validate_json(
            args.proposal.read_text(encoding="utf-8")
        )
        if args.command == "approve-onboarding":
            decision = approve_proposal(
                onboarding_request,
                proposal,
                decision_id=args.decision_id,
                configuration_version=args.configuration_version,
                aggregation_rule_version=args.aggregation_rule_version,
                reviewed_by=args.reviewed_by,
                reviewed_at=args.reviewed_at,
                approval_policy_version=args.approval_policy_version,
                review_rationale=args.review_rationale,
            )
            configuration_catalog = LocalOnboardingConfigurationCatalog(
                settings.data_directory / "interim" / "onboarding-configurations"
            )
            approved_configuration = decision.configuration
            if approved_configuration is None:
                raise RuntimeError("approved review decision is missing its configuration")
            configuration_registered = configuration_catalog.register(approved_configuration)
            configuration_path = configuration_catalog.path_for(approved_configuration)
            configuration_action = (
                "registered" if configuration_registered else "already registered"
            )
        else:
            decision = reject_proposal(
                onboarding_request,
                proposal,
                decision_id=args.decision_id,
                reviewed_by=args.reviewed_by,
                reviewed_at=args.reviewed_at,
                approval_policy_version=args.approval_policy_version,
                review_rationale=args.review_rationale,
                rejection_reasons=tuple(args.rejection_reason),
            )
            configuration_action = None
            configuration_path = None
        review_catalog = LocalOnboardingReviewCatalog(
            settings.data_directory / "interim" / "onboarding-reviews"
        )
        decision_registered = review_catalog.register(decision)
        decision_action = "recorded" if decision_registered else "already recorded"
        message = f"Review decision {decision_action}: {decision.decision_id}"
        if configuration_path is not None:
            message += f"; configuration {configuration_action}: {configuration_path}"
        print(message)
        return 0
    if args.command == "assess-onboarding-reuse":
        configuration = ApprovedOnboardingConfiguration.model_validate_json(
            args.configuration.read_text(encoding="utf-8")
        )
        target_request = DocumentOnboardingRequest.model_validate_json(
            args.request.read_text(encoding="utf-8")
        )
        assessor = OnboardingReuseAssessor()
        assessment = assessor.assess(
            configuration,
            target_request,
            assessment_id=args.assessment_id,
            assessed_at=args.assessed_at,
        )
        output = args.output or (
            settings.data_directory
            / "interim"
            / "onboarding-reuse-assessments"
            / f"{assessment.assessment_id}.json"
        )
        assessor.persist(assessment, output)
        print(
            f"Assessed {len(assessment.decision_assessments)} prior decisions to {output}; "
            f"{assessment.reusable_candidate_count} reuse candidates and "
            f"{assessment.review_required_count} requiring review"
        )
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
