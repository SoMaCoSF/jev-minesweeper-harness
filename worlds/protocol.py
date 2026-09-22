from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class Action:
    kind: str
    target: str
    meta: dict[str, Any] = field(default_factory=dict)


@dataclass
class Observation:
    state: Any
    questions: dict[str, Any]
    terminal: bool
    won: bool | None = None
    info: dict[str, Any] = field(default_factory=dict)


class World(Protocol):
    name: str

    def reset(self, seed: int | None = None) -> Observation: ...
    def observe(self) -> Observation: ...
    def step(self, action: Action) -> Observation: ...
    def policy(self, answers: dict, observation: Observation) -> Action: ...
    def mock_answers(self, state: Any, questions: dict) -> dict: ...
    def oracle(self, observation: Observation) -> dict[str, Any]: ...
