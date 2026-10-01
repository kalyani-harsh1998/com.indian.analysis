"""Aggregate only provisionally reviewed corpus cases for internal evaluation."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from indian_company_analysis.data.onboarding.corpus import EvaluationCorpusEntry
from indian_company_analysis.data.onboarding.evaluation import (
    OnboardingEvaluationReport,
    OnboardingProposalEvaluator,
)
from indian_company_analysis.data.onboarding.models import DocumentOnboardingProposal
from indian_company_analysis.data.onboarding.static_provider import StaticProposalProvider
from indian_company_analysis.domain.models import DomainModel

_RATE_QUANTUM = Decimal("0.000001")


class ProvisionalCorpusEvaluationPolicy(DomainModel):
    """Explicit thresholds for a local-only collection of provisional cases."""

    policy_version: str = Field(min_length=1)
    minimum_case_count: int = Field(default=1, ge=1)
    minimum_distinct_company_count: int = Field(default=1, ge=1)
    minimum_pass_rate: Decimal = Field(default=Decimal("1"), ge=0, le=1)
    maximum_failed_case_count: int = Field(default=0, ge=0)


class ProvisionalCorpusCaseEvaluation(DomainModel):
    """One evaluated provisional case and the source identity it represents."""

    entry_id: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    company_id: str = Field(min_length=1)
    source_checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    report: OnboardingEvaluationReport

    @model_validator(mode="after")
    def report_is_provisional(self) -> ProvisionalCorpusCaseEvaluation:
        if self.report.evaluation_qualification != "provisional_internal_review":
            raise ValueError("provisional corpus cases require provisional evaluation reports")
        return self


class ProvisionalCorpusEvaluationReport(DomainModel):
    """A transparent internal summary that can never authorize a live provider."""

    run_id: str = Field(pattern=r"^[a-z0-9][a-z0-9._-]*$")
    evaluated_at: datetime
    evaluation_qualification: Literal["provisional_internal_review"] = "provisional_internal_review"
    policy: ProvisionalCorpusEvaluationPolicy
    cases: tuple[ProvisionalCorpusCaseEvaluation, ...] = Field(min_length=1)
    total_case_count: int = Field(ge=1)
    passed_case_count: int = Field(ge=0)
    failed_case_count: int = Field(ge=0)
    distinct_company_count: int = Field(ge=1)
    pass_rate: Decimal = Field(ge=0, le=1)
    internal_failure_reasons: tuple[str, ...]
    internal_gate_passed: bool
    live_model_eligible: Literal[False] = False
    live_model_blockers: tuple[str, ...] = (
        "provisional internal review cannot authorize a live model",
    )

    @model_validator(mode="after")
    def status_and_counts_are_consistent(self) -> ProvisionalCorpusEvaluationReport:
        if self.evaluated_at.tzinfo is None or self.evaluated_at.utcoffset() is None:
            raise ValueError("corpus evaluation timestamp must include a timezone")
        if self.total_case_count != len(self.cases):
            raise ValueError("total case count must match the case records")
        passed = sum(case.report.passed for case in self.cases)
        if self.passed_case_count != passed:
            raise ValueError("passed case count must match the case reports")
        if self.failed_case_count != self.total_case_count - passed:
            raise ValueError("failed case count must match the case reports")
        expected_rate = (Decimal(passed) / Decimal(self.total_case_count)).quantize(_RATE_QUANTUM)
        if self.pass_rate != expected_rate:
            raise ValueError("pass rate must match the case reports")
        if self.distinct_company_count != len({case.company_id for case in self.cases}):
            raise ValueError("distinct company count must match the case records")
        if self.internal_gate_passed != (not self.internal_failure_reasons):
            raise ValueError("internal gate status must match its failure reasons")
        if self.live_model_eligible:
            raise ValueError("a provisional corpus report can never authorize a live model")
        if not self.live_model_blockers:
            raise ValueError("a provisional corpus report must state live-model blockers")
        return self


class ProvisionalCorpusEvaluator:
    """Evaluate a bounded set of provisional cases under an explicit local policy."""

    def evaluate(
        self,
        entries: tuple[EvaluationCorpusEntry, ...],
        proposals: tuple[DocumentOnboardingProposal, ...],
        *,
        run_id: str,
        policy: ProvisionalCorpusEvaluationPolicy,
        evaluated_at: datetime,
    ) -> ProvisionalCorpusEvaluationReport:
        if not entries:
            raise ValueError("provisional corpus evaluation requires at least one entry")
        if len(entries) != len(proposals):
            raise ValueError("provisional corpus entries and proposals must have equal counts")

        entry_keys = [(entry.entry_id, entry.corpus_version) for entry in entries]
        if len(entry_keys) != len(set(entry_keys)):
            raise ValueError("provisional corpus evaluation contains duplicate entry versions")

        evaluator = OnboardingProposalEvaluator()
        cases: list[ProvisionalCorpusCaseEvaluation] = []
        for entry, proposal in zip(entries, proposals, strict=True):
            if not entry.is_provisionally_reviewed_for_internal_evaluation:
                raise ValueError("all corpus entries must have provisional internal review")
            fixture = entry.fixture
            if fixture is None:
                raise ValueError("provisional corpus entry is missing its evaluation fixture")
            report = evaluator.evaluate(
                fixture,
                StaticProposalProvider(proposal),
                evaluated_at=evaluated_at,
                evaluation_qualification="provisional_internal_review",
            )
            cases.append(
                ProvisionalCorpusCaseEvaluation(
                    entry_id=entry.entry_id,
                    corpus_version=entry.corpus_version,
                    company_id=entry.source_manifest.company_id,
                    source_checksum_sha256=entry.source_manifest.checksum_sha256,
                    report=report,
                )
            )

        passed_case_count = sum(case.report.passed for case in cases)
        total_case_count = len(cases)
        failed_case_count = total_case_count - passed_case_count
        distinct_company_count = len({case.company_id for case in cases})
        pass_rate = (Decimal(passed_case_count) / Decimal(total_case_count)).quantize(_RATE_QUANTUM)
        failure_reasons: list[str] = []
        if total_case_count < policy.minimum_case_count:
            failure_reasons.append(
                f"case count {total_case_count} is below required {policy.minimum_case_count}"
            )
        if distinct_company_count < policy.minimum_distinct_company_count:
            failure_reasons.append(
                "distinct company count "
                f"{distinct_company_count} is below required "
                f"{policy.minimum_distinct_company_count}"
            )
        if pass_rate < policy.minimum_pass_rate:
            failure_reasons.append(
                f"pass rate {pass_rate} is below required {policy.minimum_pass_rate}"
            )
        if failed_case_count > policy.maximum_failed_case_count:
            failure_reasons.append(
                "failed case count "
                f"{failed_case_count} exceeds permitted {policy.maximum_failed_case_count}"
            )

        return ProvisionalCorpusEvaluationReport(
            run_id=run_id,
            evaluated_at=evaluated_at,
            policy=policy,
            cases=tuple(cases),
            total_case_count=total_case_count,
            passed_case_count=passed_case_count,
            failed_case_count=failed_case_count,
            distinct_company_count=distinct_company_count,
            pass_rate=pass_rate,
            internal_failure_reasons=tuple(failure_reasons),
            internal_gate_passed=not failure_reasons,
        )

    @staticmethod
    def persist(report: ProvisionalCorpusEvaluationReport, output: Path) -> None:
        """Persist one immutable-style local corpus report without replacement."""

        output.parent.mkdir(parents=True, exist_ok=True)
        serialized = report.model_dump_json(indent=2) + "\n"
        if output.exists() and output.read_text(encoding="utf-8") != serialized:
            raise ValueError(f"refusing to overwrite different corpus report: {output}")
        output.write_text(serialized, encoding="utf-8")
