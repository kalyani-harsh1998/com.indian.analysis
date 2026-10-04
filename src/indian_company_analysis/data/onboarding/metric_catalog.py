"""Versioned, company-independent metric context for onboarding providers.

These are interpretation boundaries, not label aliases or issuer-specific mappings.
The canonical financial engine dictionary remains the source of base definitions.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

from pydantic import Field, model_validator

from indian_company_analysis.domain.enums import MetricNature, StatementType, UnitType
from indian_company_analysis.domain.metrics import METRIC_DEFINITIONS, MetricId
from indian_company_analysis.domain.models import DomainModel

_SCOPE_NOTES: dict[MetricId, str] = {
    MetricId.REVENUE: (
        "Do not substitute total income including other income for operating revenue."
    ),
    MetricId.COST_OF_REVENUE: (
        "Operating expenses or employee costs are not automatically cost of revenue. "
        "Require evidence of the direct-cost scope."
    ),
    MetricId.EBITDA: (
        "Use an explicitly reported, definition-compatible amount. Adjusted EBITDA is not "
        "automatically equivalent. Leave analytical reconstruction to the calculation engine."
    ),
    MetricId.EBIT: (
        "Do not substitute profit before tax or reconstruct operating profit from unrelated "
        "statement totals. Leave analytical reconstruction to the calculation engine."
    ),
    MetricId.FINANCE_COST: (
        "Prefer the reported finance-cost amount. Aggregate only components explicitly supported "
        "as belonging to that scope. Foreign-exchange and derivative losses are not automatically "
        "finance costs merely because they appear among expenses. Interest alone is not a full "
        "finance-cost amount when other relevant components are unresolved. Do not net finance "
        "income or add capitalised costs without a compatible definition."
    ),
    MetricId.PROFIT_BEFORE_TAX: (
        "Prefer the reported full-period PBT for the request's entity/basis. A subtotal before "
        "exceptional items or for only one segment is not automatically the full amount."
    ),
    MetricId.TAX_EXPENSE: (
        "Profit-and-loss tax expense, including current and deferred tax where applicable. "
        "Keep credits negative; do not include tax recorded only in OCI or equity."
    ),
    MetricId.PROFIT_AFTER_TAX: (
        "Require compatible profit scope. If group total, owners' profit, non-controlling "
        "interests, or continuing/discontinued operations create competing interpretations, "
        "state the unresolved definition rather than silently treating them as equivalent. "
        "Prefer the compatible reported amount over reconstructing PBT less tax."
    ),
    MetricId.TRADE_RECEIVABLES: (
        "Gross and net receivables are not interchangeable; flag competing definitions when "
        "the requested scope cannot be established."
    ),
    MetricId.CAPITAL_EXPENDITURE: (
        "Use cash expenditure, not balance-sheet asset additions or total investing cash flow. "
        "Preserve the evidence sign; convert a cash outflow to the positive capex convention once."
    ),
}


class OnboardingMetricDefinition(DomainModel):
    metric_id: MetricId
    display_name: str
    statement_type: StatementType
    nature: MetricNature
    unit_type: UnitType
    description: str
    scope_notes: str


class OnboardingMetricCatalog(DomainModel):
    version: Literal["onboarding-metric-catalog-v1"] = "onboarding-metric-catalog-v1"
    definitions: tuple[OnboardingMetricDefinition, ...] = Field(min_length=1)
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def definitions_are_unique_and_checksummed(self) -> OnboardingMetricCatalog:
        ids = [item.metric_id for item in self.definitions]
        if len(ids) != len(set(ids)):
            raise ValueError("onboarding metric catalog contains duplicate metrics")
        if any(METRIC_DEFINITIONS[item].nature is MetricNature.DERIVED for item in ids):
            raise ValueError("onboarding metric catalog cannot contain derived metrics")
        if self.checksum_sha256 != _catalog_checksum(self.version, self.definitions):
            raise ValueError("onboarding metric catalog checksum does not match its definitions")
        return self


def build_onboarding_metric_catalog() -> OnboardingMetricCatalog:
    """Snapshot eligible definitions without inferring scope from company names or labels."""

    definitions = tuple(
        OnboardingMetricDefinition(
            metric_id=definition.metric_id,
            display_name=definition.display_name,
            statement_type=definition.statement_type,
            nature=definition.nature,
            unit_type=definition.unit_type,
            description=definition.description,
            scope_notes=_SCOPE_NOTES.get(
                definition.metric_id,
                "Match scope, period, basis and units; do not infer missing components.",
            ),
        )
        for definition in METRIC_DEFINITIONS.values()
        if definition.nature is not MetricNature.DERIVED
    )
    version = "onboarding-metric-catalog-v1"
    return OnboardingMetricCatalog(
        definitions=definitions, checksum_sha256=_catalog_checksum(version, definitions)
    )


def _catalog_checksum(version: str, definitions: tuple[OnboardingMetricDefinition, ...]) -> str:
    payload = {
        "version": version,
        "definitions": [item.model_dump(mode="json") for item in definitions],
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
