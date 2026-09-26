"""Simple deterministic step orchestration without an agent framework."""

from collections.abc import Callable, Iterable
from typing import Any


class ControlledOrchestrator:
    def __init__(self, steps: Iterable[Callable[[Any], Any]]) -> None:
        self._steps = tuple(steps)

    def run(self, initial_value: Any) -> Any:
        value = initial_value
        for step in self._steps:
            value = step(value)
        return value
