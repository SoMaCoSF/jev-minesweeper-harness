"""HOLD world: Jev places walls/towers; BFS and combat stay in code."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jev_client.client import JevAnswer
from worlds.protocol import Action, Observation

DIRS = [(1, 0, -1), (1, -1, 0), (0, -1, 1), (-1, 0, 1), (-1, 1, 0), (0, 1, -1)]


def _cells(R: int):
    out = []
    for q in range(-R, R + 1):
        r1 = max(-R, -q - R)
        r2 = min(R, -q + R)
        for r in range(r1, r2 + 1):
            out.append((q, r, -q - r))
    return out


def _key(c):
    return f"{c[0]},{c[1]},{c[2]}"


class HoldWorld:
    name = "hold"

    def __init__(self, radius: int = 3, waves: int = 6):
        self.R = radius
        self.max_waves = waves
        self.safe_th = 0.07
        self.mine_th = 0.85
        self.reset(1)

    def reset(self, seed: int | None = None) -> Observation:
        self.seed = seed or 1
        self.tiles = {k: "empty" for k in map(_key, _cells(self.R))}
        self.tiles[_key((-self.R, 0, self.R))] = "spawn"
        self.tiles[_key((self.R, 0, -self.R))] = "base"
        self.gold = 12
        self.lives = 8
        self.wave = 0
        self.dead = False
        self.won = False
        return self.observe()

    def _nbs(self, q, r, s):
        out = []
        for dq, dr, ds in DIRS:
            k = _key((q + dq, r + dr, s + ds))
            if k in self.tiles:
                out.append(k)
        return out

    def path(self):
        start = _key((-self.R, 0, self.R))
        goal = _key((self.R, 0, -self.R))
        q = [start]
        seen = {start}
        prev = {}
        while q:
            c = q.pop(0)
            if c == goal:
                path = [c]
                while path[0] in prev:
                    path.insert(0, prev[path[0]])
                return path
            qq, rr, ss = (int(x) for x in c.split(","))
            for nk in self._nbs(qq, rr, ss):
                if nk in seen or self.tiles[nk] == "wall":
                    continue
                seen.add(nk)
                prev[nk] = c
                q.append(nk)
        return None

    def observe(self) -> Observation:
        p = self.path()
        legal = [k for k, v in self.tiles.items() if v == "empty"]
        questions: dict[str, Any] = {
            "tool": {
                "type": "choice",
                "prompt": "wall, tower, or wave?",
                "criteria": {"wall": "block and lengthen path", "tower": "damage adjacent path", "wave": "spend a wave now"},
            }
        }
        for k in legal[:40]:
            questions[f"wall_{k}"] = {"type": "noul", "prompt": f"place wall at {k}?"}
            questions[f"tower_{k}"] = {"type": "noul", "prompt": f"place tower at {k}?"}
        questions["path_value"] = {"type": "score", "prompt": "how good is current path length vs gold"}
        state = {
            "radius": self.R,
            "tiles": self.tiles,
            "gold": self.gold,
            "lives": self.lives,
            "wave": self.wave,
            "path_len": len(p) if p else 0,
            "lattice": "hex-map-wfc cube + odd-r offset render",
        }
        terminal = self.dead or self.won or self.wave >= self.max_waves
        return Observation(state=state, questions=questions, terminal=terminal, won=self.won, info={"path": p})

    def step(self, action: Action) -> Observation:
        if action.kind == "wave":
            self._resolve_wave()
        elif action.kind in ("wall", "tower") and action.target in self.tiles:
            if self.tiles[action.target] == "empty" and self.gold >= (1 if action.kind == "wall" else 3):
                prev = self.tiles[action.target]
                self.tiles[action.target] = action.kind
                if action.kind == "wall" and not self.path():
                    self.tiles[action.target] = prev
                else:
                    self.gold -= 1 if action.kind == "wall" else 3
        return self.observe()

    def _resolve_wave(self):
        p = self.path()
        if not p:
            self.dead = True
            return
        self.wave += 1
        hp = 3 + self.wave
        dmg = 0
        for step in p:
            q, r, s = (int(x) for x in step.split(","))
            if self.tiles[step] == "tower":
                dmg += 1
            for nk in self._nbs(q, r, s):
                if self.tiles[nk] == "tower":
                    dmg += 1
        if dmg >= hp:
            self.gold += 2
        else:
            self.lives -= 1
            if self.lives <= 0:
                self.dead = True
        if self.wave >= self.max_waves and not self.dead:
            self.won = True

    def policy(self, answers: dict, observation: Observation) -> Action:
        tool = "wall"
        if "tool" in answers and getattr(answers["tool"], "choice", None):
            tool = answers["tool"].choice
        if tool == "wave":
            return Action(kind="wave", target="")
        best, best_v = None, -1.0
        prefix = f"{tool}_"
        for name, ans in answers.items():
            if not name.startswith(prefix):
                continue
            v = ans.noul if getattr(ans, "noul", None) is not None else 0.0
            if v > best_v:
                best, best_v = name[len(prefix) :], v
        if not best:
            empty = [k for k, v in self.tiles.items() if v == "empty"]
            best = empty[0] if empty else ""
        return Action(kind=tool if tool in ("wall", "tower") else "wall", target=best)

    def mock_answers(self, state: Any, questions: dict) -> dict:
        p = set(self.path() or [])
        out = {}
        for name, q in questions.items():
            if q.get("type") == "choice":
                out[name] = JevAnswer(type="choice", raw={}, choice="wall", confidence=0.6, probabilities={"wall": 0.5, "tower": 0.3, "wave": 0.2})
            elif q.get("type") == "score":
                out[name] = JevAnswer(type="score", raw={}, score=float(len(p)), confidence=0.7)
            else:
                k = name.split("_", 1)[-1]
                nbs = 0
                if k.count(",") == 2:
                    q0, r0, s0 = (int(x) for x in k.split(","))
                    nbs = sum(1 for nk in self._nbs(q0, r0, s0) if nk in p)
                noul = min(0.95, 0.2 + 0.15 * nbs)
                if name.startswith("tower_"):
                    noul = min(0.95, 0.1 + 0.2 * nbs)
                out[name] = JevAnswer(type="noul", raw={}, noul=noul, confidence=0.55)
        return out

    def oracle(self, observation: Observation) -> dict[str, Any]:
        p = self.path()
        return {"path_len": len(p) if p else 0, "gold": self.gold, "lives": self.lives, "wave": self.wave}
