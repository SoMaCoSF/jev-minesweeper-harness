"""Any JSON spec becomes a one-shot Jev world."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jev_client.client import JevAnswer

from .protocol import Action, Observation


class GenericWorld:
    name = "generic"

    def __init__(self, spec_path: str | None = None, spec: dict | None = None) -> None:
        if spec is None:
            if not spec_path:
                raise ValueError("generic world needs --spec")
            spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
        self.spec = spec
        self.done = False
        self.last_answers: dict = {}

    def reset(self, seed: int | None = None) -> Observation:
        self.done = False
        self.last_answers = {}
        return self.observe()

    def observe(self) -> Observation:
        return Observation(
            state=self.spec.get("state"),
            questions=self.spec.get("questions") or {},
            terminal=self.done,
            won=True if self.done else None,
            info={"title": self.spec.get("title", "generic")},
        )

    def step(self, action: Action) -> Observation:
        self.done = True
        return Observation(
            state=self.spec.get("state"),
            questions={},
            terminal=True,
            won=True,
            info={"action": action.__dict__, "answers": {k: getattr(v, "raw", v) for k, v in self.last_answers.items()}},
        )

    def policy(self, answers: dict, observation: Observation) -> Action:
        self.last_answers = answers
        summary = []
        for name, ans in answers.items():
            if getattr(ans, "noul", None) is not None:
                summary.append(f"{name}=noul:{ans.noul:.3f}")
            elif getattr(ans, "choice", None) is not None:
                summary.append(f"{name}=choice:{ans.choice}")
            elif getattr(ans, "score", None) is not None:
                summary.append(f"{name}=score:{ans.score}")
        return Action("record", ",".join(summary) or "none")

    def mock_answers(self, state: Any, questions: dict) -> dict:
        out = {}
        for name, q in questions.items():
            t = (q or {}).get("type", "noul")
            if t == "choice":
                keys = list(((q or {}).get("criteria") or {"unknown": None}).keys())
                out[name] = JevAnswer(type="choice", raw={}, choice=keys[0], confidence=0.4, probabilities={keys[0]: 1.0})
            elif t == "score":
                out[name] = JevAnswer(type="score", raw={}, score=1.0, confidence=0.4)
            else:
                out[name] = JevAnswer(type="noul", raw={}, noul=0.5)
        return out

    def oracle(self, observation: Observation) -> dict[str, Any]:
        return {"expected": self.spec.get("expected")}
