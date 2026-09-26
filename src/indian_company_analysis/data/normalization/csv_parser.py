"""Deterministic parser for controlled, row-oriented financial-statement CSV files."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

from pydantic import Field, ValidationError

from indian_company_analysis.data.ingestion.models import RawDocumentManifest
from indian_company_analysis.data.ingestion.verification import verify_raw_document
from indian_company_analysis.data.normalization.models import (
    MetricLabelMapping,
    MetricMappingSet,
    NormalizationIssue,
    NormalizedFact,
    NormalizedFactBatch,
    SourceFactLocator,
    normalize_reported_label,
)
from indian_company_analysis.domain.enums import PeriodType, ReportingBasis, ValueClassification
from indian_company_analysis.domain.models import DomainModel, MetricObservation, ReportingPeriod


class _ControlledCsvRow(DomainModel):
    company_id: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    table_id: str = Field(min_length=1)
    row_number: int = Field(ge=1)
    column_name: str = Field(min_length=1)
    reported_label: str = Field(min_length=1)
    value: Decimal
    unit: str = Field(min_length=1)
    period_label: str = Field(min_length=1)
    period_type: PeriodType
    period_start_date: date
    period_end_date: date
    reporting_basis: ReportingBasis


_REQUIRED_COLUMNS = frozenset(_ControlledCsvRow.model_fields)


class ControlledCsvFinancialParser:
    """Normalize explicit CSV rows; never infer labels, periods, units, or accounting bases."""

    parser_version = "controlled-csv-v1"

    def parse(
        self,
        manifest: RawDocumentManifest,
        raw_root: Path,
        mapping_set: MetricMappingSet,
    ) -> NormalizedFactBatch:
        verification = verify_raw_document(manifest, raw_root)
        if not verification.valid:
            raise ValueError(f"raw document verification failed: {verification.message}")
        if manifest.content_type != "text/csv":
            raise ValueError("controlled CSV parser accepts only text/csv manifests")
        self._validate_mapping_scope(manifest, mapping_set)

        mapping_lookup = {
            normalize_reported_label(item.reported_label): item for item in mapping_set.mappings
        }
        facts: list[NormalizedFact] = []
        issues: list[NormalizationIssue] = []
        seen_fact_keys: set[tuple[object, ...]] = set()
        stored_path = raw_root / manifest.stored_relative_path

        with stored_path.open(encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            fieldnames = set(reader.fieldnames or ())
            missing_columns = sorted(_REQUIRED_COLUMNS - fieldnames)
            if missing_columns:
                raise ValueError(
                    "controlled CSV is missing required columns: " + ", ".join(missing_columns)
                )
            for csv_record_number, raw_row in enumerate(reader, start=2):
                self._normalize_row(
                    raw_row=raw_row,
                    csv_record_number=csv_record_number,
                    manifest=manifest,
                    mapping_set=mapping_set,
                    mapping_lookup=mapping_lookup,
                    seen_fact_keys=seen_fact_keys,
                    facts=facts,
                    issues=issues,
                )

        parsed_source = manifest.source_reference.model_copy(
            update={"parser_version": self.parser_version}
        )
        return NormalizedFactBatch(
            document_id=manifest.document_id,
            source_checksum_sha256=manifest.checksum_sha256,
            source_reference=parsed_source,
            parser_version=self.parser_version,
            mapping_version=mapping_set.mapping_version,
            total_rows=len(facts) + len(issues),
            facts=tuple(facts),
            issues=tuple(issues),
            ready_for_analysis=not issues,
        )

    @staticmethod
    def _validate_mapping_scope(
        manifest: RawDocumentManifest, mapping_set: MetricMappingSet
    ) -> None:
        if mapping_set.source_organization != manifest.source_reference.source_organization:
            raise ValueError("mapping source organization does not match the document manifest")
        if mapping_set.document_type is not manifest.document_type:
            raise ValueError("mapping document type does not match the document manifest")

    def _normalize_row(
        self,
        *,
        raw_row: dict[str, str | None],
        csv_record_number: int,
        manifest: RawDocumentManifest,
        mapping_set: MetricMappingSet,
        mapping_lookup: dict[str, MetricLabelMapping],
        seen_fact_keys: set[tuple[object, ...]],
        facts: list[NormalizedFact],
        issues: list[NormalizationIssue],
    ) -> None:
        reported_label = raw_row.get("reported_label")
        try:
            row = _ControlledCsvRow.model_validate(raw_row)
        except ValidationError as error:
            issues.append(
                NormalizationIssue(
                    csv_record_number=csv_record_number,
                    code="invalid_row",
                    message=self._validation_message(error),
                    reported_label=reported_label,
                )
            )
            return
        if row.company_id != manifest.company_id:
            issues.append(
                NormalizationIssue(
                    csv_record_number=csv_record_number,
                    code="company_mismatch",
                    message="row company_id does not match the document manifest",
                    reported_label=row.reported_label,
                )
            )
            return
        mapping = mapping_lookup.get(normalize_reported_label(row.reported_label))
        if mapping is None:
            issues.append(
                NormalizationIssue(
                    csv_record_number=csv_record_number,
                    code="unmapped_label",
                    message="reported label has no exact canonical metric mapping",
                    reported_label=row.reported_label,
                )
            )
            return

        fact_key = (
            row.company_id,
            mapping.metric_id,
            row.period_start_date,
            row.period_end_date,
            row.reporting_basis,
        )
        if fact_key in seen_fact_keys:
            issues.append(
                NormalizationIssue(
                    csv_record_number=csv_record_number,
                    code="duplicate_fact",
                    message="document contains another fact for the same metric, period, and basis",
                    reported_label=row.reported_label,
                )
            )
            return
        seen_fact_keys.add(fact_key)

        locator = SourceFactLocator(
            page_number=row.page_number,
            table_id=row.table_id,
            row_number=row.row_number,
            column_name=row.column_name,
        )
        fact_id = f"{manifest.document_id}:{row.table_id}:{row.row_number}:{row.column_name}"
        observation = MetricObservation(
            observation_id=fact_id,
            company_id=row.company_id,
            metric_id=mapping.metric_id,
            value=row.value * mapping.sign_multiplier,
            unit=row.unit,
            period=ReportingPeriod(
                label=row.period_label,
                period_type=row.period_type,
                start_date=row.period_start_date,
                end_date=row.period_end_date,
            ),
            reporting_basis=row.reporting_basis,
            value_classification=ValueClassification.REPORTED,
            source_reference_ids=(manifest.source_reference.source_id,),
        )
        facts.append(
            NormalizedFact(
                fact_id=fact_id,
                document_id=manifest.document_id,
                source_checksum_sha256=manifest.checksum_sha256,
                source_locator=locator,
                reported_label=row.reported_label,
                raw_value=str(raw_row["value"]),
                observation=observation,
                parser_version=self.parser_version,
                mapping_version=mapping_set.mapping_version,
                mapping_confidence=mapping.confidence,
            )
        )

    @staticmethod
    def _validation_message(error: ValidationError) -> str:
        first_error = error.errors(include_url=False)[0]
        location = ".".join(str(part) for part in first_error["loc"])
        return f"{location}: {first_error['msg']}"
