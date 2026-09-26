"""Small contracts that keep future agents independent of orchestration vendors."""

from typing import Protocol, TypeVar

InputT = TypeVar("InputT", contravariant=True)
OutputT = TypeVar("OutputT", covariant=True)


class AnalysisStep(Protocol[InputT, OutputT]):
    def run(self, input_value: InputT) -> OutputT: ...


class AnalysisAgent(Protocol[InputT, OutputT]):
    @property
    def name(self) -> str: ...

    def analyze(self, input_value: InputT) -> OutputT: ...
