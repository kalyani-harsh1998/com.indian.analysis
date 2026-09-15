from pathlib import Path

import pytest


@pytest.fixture
def demo_fixture_path() -> Path:
    return Path(__file__).parents[1] / "data" / "fixtures" / "demo" / "it_services.json"
