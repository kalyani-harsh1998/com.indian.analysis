"""Local, secret-free configuration for the foundational POC."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class Settings:
    project_root: Path
    data_directory: Path
    output_directory: Path

    @classmethod
    def from_environment(cls) -> Settings:
        project_root = Path(__file__).resolve().parents[2]
        data_directory = Path(os.getenv("ICA_DATA_DIRECTORY", project_root / "data"))
        output_directory = Path(os.getenv("ICA_OUTPUT_DIRECTORY", project_root / "outputs"))
        return cls(
            project_root=project_root,
            data_directory=data_directory,
            output_directory=output_directory,
        )
