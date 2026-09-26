from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from indian_company_analysis.data.sources.local_files import LocalFixtureDataSource
from indian_company_analysis.domain.enums import SourceKind, ValueClassification
from indian_company_analysis.workflows.company_analysis import CompanyAnalysisWorkflow


def test_workflow_executes_with_synthetic_classification(demo_fixture_path: Path) -> None:
    fixed_time = datetime(2026, 4, 30, 12, tzinfo=UTC)
    workflow = CompanyAnalysisWorkflow(
        LocalFixtureDataSource(demo_fixture_path),
        clock=lambda: fixed_time,
        run_id_factory=lambda: "deterministic-test-run",
    )

    result = workflow.run()

    assert result.manifest.run_id == "deterministic-test-run"
    assert result.manifest.data_is_synthetic is True
    assert result.manifest.input_data_version == "1.0.0"
    assert result.manifest.source_kinds == frozenset({SourceKind.SYNTHETIC})
    assert result.manifest.output_observation_count == 15
    assert len(result.manifest.request.peers) == 4
    assert all(
        item.value_classification is ValueClassification.CALCULATED for item in result.observations
    )
    assert all(
        item.source_reference_ids == ("synthetic_demo_fixture",) for item in result.observations
    )
    assert result.source_references[0].is_synthetic is True

    values = {
        item.metric_id: item.value for item in result.observations if item.company_id == "demo_info"
    }
    assert values == {
        "revenue_growth": Decimal("0.12"),
        "operating_margin": Decimal("0.2142857142857142857142857143"),
        "cfo_to_pat_conversion": Decimal("1.2"),
    }


def test_result_serializes_to_structured_json(demo_fixture_path: Path, tmp_path: Path) -> None:
    result = CompanyAnalysisWorkflow(LocalFixtureDataSource(demo_fixture_path)).run()
    output = tmp_path / "result.json"
    output.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    serialized = output.read_text(encoding="utf-8")
    assert '"data_is_synthetic": true' in serialized
    assert '"workflow_name": "synthetic_company_analysis"' in serialized
    assert '"value_classification": "calculated"' in serialized
