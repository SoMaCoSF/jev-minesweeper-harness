"""Thin TypeSafe Jev client + deterministic mock."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

import httpx

DECIDE_URL = os.environ.get("JEV_DECIDE_URL", "https://api.typesafe.ai/v1/system-one")
ALT_URL = os.environ.get("JEV_ALT_URL", "https://jevtypesafeai.com/api/v1/decide")


@dataclass
class JevAnswer:
    type: str
    raw: dict
    noul: float | None = None
    choice: str | None = None
    score: float | None = None
    confidence: float | None = None
    probabilities: dict[str, float] = field(default_factory=dict)


@dataclass
class DecideResult:
    answers: dict[str, JevAnswer]
    model: str
    input_tokens: int
    latency_ms: float
    mocked: bool


class JevClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = "jev-latest",
        mock: bool = False,
        mock_fn: Callable[[Any, Mapping[str, Any]], dict[str, JevAnswer]] | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = api_key or os.environ.get("TYPESAFE_API_KEY") or os.environ.get("JEV_API_KEY")
        self.model = model
        self.mock = mock or not self.api_key
        self.mock_fn = mock_fn
        self.timeout = timeout

    def decide(self, state: Any, questions: Mapping[str, Any]) -> DecideResult:
        if self.mock:
            t0 = time.perf_counter()
            if self.mock_fn:
                answers = self.mock_fn(state, questions)
            else:
                answers = _default_mock(questions)
            return DecideResult(
                answers=answers,
                model="mock",
                input_tokens=0,
                latency_ms=(time.perf_counter() - t0) * 1000,
                mocked=True,
            )
        payload = {"model": self.model, "state": state, "questions": dict(questions)}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        t0 = time.perf_counter()
        last_exc: Exception | None = None
        data: dict[str, Any] | None = None
        for url in (DECIDE_URL, ALT_URL):
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    r = client.post(url, json=payload, headers=headers)
                    if r.status_code >= 400:
                        last_exc = RuntimeError(f"{url} {r.status_code}: {r.text[:400]}")
                        continue
                    data = r.json()
                    break
            except Exception as exc:
                last_exc = exc
        if data is None:
            raise RuntimeError(f"Jev decide failed: {last_exc}")
        answers = {k: _parse_answer(v) for k, v in (data.get("answers") or {}).items()}
        usage = data.get("usage") or {}
        return DecideResult(
            answers=answers,
            model=str(data.get("model", self.model)),
            input_tokens=int(usage.get("input_tokens") or 0),
            latency_ms=(time.perf_counter() - t0) * 1000,
            mocked=False,
        )


def _parse_answer(v: dict) -> JevAnswer:
    return JevAnswer(
        type=str(v.get("type", "")),
        raw=v,
        noul=_maybe_float(v.get("noul")),
        choice=v.get("choice"),
        score=_maybe_float(v.get("score")),
        confidence=_maybe_float(v.get("confidence")),
        probabilities={str(k): float(p) for k, p in (v.get("probabilities") or {}).items()},
    )


def _maybe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _default_mock(questions: Mapping[str, Any]) -> dict[str, JevAnswer]:
    out: dict[str, JevAnswer] = {}
    for name, q in questions.items():
        qtype = (q or {}).get("type", "noul")
        if qtype == "choice":
            keys = list(((q or {}).get("criteria") or {"a": None}).keys())
            probs = {k: (1.0 if i == 0 else 0.0) for i, k in enumerate(keys)}
            out[name] = JevAnswer(type="choice", raw={}, choice=keys[0], confidence=0.5, probabilities=probs)
        elif qtype == "score":
            out[name] = JevAnswer(type="score", raw={}, score=0.0, confidence=0.5)
        else:
            out[name] = JevAnswer(type="noul", raw={}, noul=0.5)
    return out
