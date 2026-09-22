"""Hex Minesweeper on the same cube coords as SoMaCoSF/hex-map-wfc.

Pointy-top axial/cube: q, r, s=-q-r.
Neighbors = CUBE_DIRS from hex-map-wfc NOTES.md / Red Blob Games.
A board of radius R has 3R(R+1)+1 cells (R=3 -> 37, R=4 -> 61).
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from jev_client.client import JevAnswer
from .protocol import Action, Observation

CUBE_DIRS = (
    (1, 0, -1),
    (1, -1, 0),
    (0, -1, 1),
    (-1, 0, 1),
    (-1, 1, 0),
    (0, 1, -1),
)

PRESETS = {
    "hex-tiny": {"radius": 2, "mines": 5},
    "hex-small": {"radius": 3, "mines": 8},
    "hex-beginner": {"radius": 4, "mines": 12},
    "hex-grid": {"radius": 8, "mines": 40},
}


def cube_key(q: int, r: int, s: int | None = None) -> str:
    if s is None:
        s = -q - r
    return f"{q},{r},{s}"


def parse_key(k: str) -> tuple[int, int, int]:
    q, r, s = (int(x) for x in k.split(","))
    return q, r, s


def hex_cells(radius: int) -> list[tuple[int, int, int]]:
    out = []
    for q in range(-radius, radius + 1):
        r1 = max(-radius, -q - radius)
        r2 = min(radius, -q + radius)
        for r in range(r1, r2 + 1):
            out.append((q, r, -q - r))
    return out


def neighbors(q: int, r: int, s: int, radius: int) -> list[tuple[int, int, int]]:
    out = []
    for dq, dr, ds in CUBE_DIRS:
        nq, nr, ns = q + dq, r + dr, s + ds
        if max(abs(nq), abs(nr), abs(ns)) <= radius:
            out.append((nq, nr, ns))
    return out


def axial_art(radius: int, glyph) -> str:
    lines = [f"hex radius={radius} cells={3*radius*(radius+1)+1} (cube q,r,s)"]
    for row in range(-radius, radius + 1):
        pad = " " * (radius - row)
        cells = []
        for q in range(-radius, radius + 1):
            r = row
            s = -q - r
            if max(abs(q), abs(r), abs(s)) > radius:
                continue
            cells.append(f"{glyph(q, r, s):>3}")
        lines.append(pad + " ".join(cells) + f"   r={row}")
    return "\n".join(lines)


@dataclass
class HexMinesweeperWorld:
    name: str = "hex"
    preset: str = "hex-small"
    style: str = "digested"
    safe_th: float = 0.07
    mine_th: float = 0.85
    radius: int = 3
    mines: int = 8
    rng: random.Random = field(default_factory=random.Random)
    cells: list[tuple[int, int, int]] = field(default_factory=list)
    mine_set: set[tuple[int, int, int]] = field(default_factory=set)
    revealed: set[tuple[int, int, int]] = field(default_factory=set)
    flagged: set[tuple[int, int, int]] = field(default_factory=set)
    numbers: dict[tuple[int, int, int], int] = field(default_factory=dict)
    dead: bool = False
    won_flag: bool = False
    first_click_pending: bool = True
    seed: int = 0

    def __post_init__(self) -> None:
        spec = PRESETS.get(self.preset, {"radius": self.radius, "mines": self.mines})
        self.radius = spec["radius"]
        self.mines = spec["mines"]
        self.cells = hex_cells(self.radius)

    def reset(self, seed: int | None = None) -> Observation:
        self.seed = 0 if seed is None else seed
        self.rng = random.Random(self.seed)
        self.revealed.clear()
        self.flagged.clear()
        self.mine_set = set()
        self.numbers = {}
        self.dead = False
        self.won_flag = False
        self.first_click_pending = True
        return self.observe()

    def _place(self, safe: tuple[int, int, int]) -> None:
        pool = [c for c in self.cells if c != safe]
        self.rng.shuffle(pool)
        self.mine_set = set(pool[: self.mines])
        self.numbers = {}
        for c in self.cells:
            if c in self.mine_set:
                continue
            self.numbers[c] = sum(1 for n in neighbors(*c, self.radius) if n in self.mine_set)

    def _flood(self, start: tuple[int, int, int]) -> None:
        stack = [start]
        while stack:
            cell = stack.pop()
            if cell in self.revealed or cell in self.mine_set:
                continue
            self.revealed.add(cell)
            if self.numbers.get(cell, 0) == 0:
                stack.extend(neighbors(*cell, self.radius))

    def _remaining(self) -> int:
        return self.mines - len(self.flagged)

    def _frontier(self) -> list[tuple[int, int, int]]:
        seen: set[tuple[int, int, int]] = set()
        out: list[tuple[int, int, int]] = []
        for cell in self.revealed:
            for n in neighbors(*cell, self.radius):
                if n not in self.revealed and n not in self.flagged and n not in seen:
                    seen.add(n)
                    out.append(n)
        if not out:
            out = [c for c in self.cells if c not in self.revealed and c not in self.flagged]
        return out

    def _clues(self) -> list[str]:
        lines = []
        for c in sorted(self.revealed):
            n = self.numbers.get(c, 0)
            nbs = neighbors(*c, self.radius)
            flags = [x for x in nbs if x in self.flagged]
            hidden = [x for x in nbs if x not in self.revealed and x not in self.flagged]
            need = n - len(flags)
            hid = ", ".join(cube_key(*h) for h in hidden) or "(none)"
            lines.append(
                f"{cube_key(*c)} shows {n}/6; {len(flags)} flagged; needs {need} more among {len(hidden)}: {hid}"
            )
        return lines

    def _glyph(self, q: int, r: int, s: int) -> str:
        c = (q, r, s)
        if c in self.flagged:
            return "F"
        if c not in self.revealed:
            return "."
        return str(self.numbers.get(c, 0))

    def observe(self) -> Observation:
        terminal = self.dead or self.won_flag
        frontier = self._frontier()
        questions: dict[str, Any] = {}
        for cell in frontier:
            k = f"mine_{cube_key(*cell)}"
            if self.style == "raw":
                instr = (
                    f"Hex Minesweeper, cube coords q,r,s. Pointy-top, 6 neighbors. "
                    f"Is cell {cube_key(*cell)} a mine given the visible board?"
                )
            else:
                local = [line for line in self._clues() if cube_key(*cell) in line]
                instr = (
                    f"Is hex {cube_key(*cell)} a mine? "
                    f"Neighbors are 6 cube directions. Mines remaining {self._remaining()}.\n"
                    + "\n".join(local[:10])
                )
            questions[k] = {"type": "noul", "instructions": instr}
        art = axial_art(self.radius, self._glyph)
        state: Any = {
            "lattice": "hex-cube",
            "orientation": "pointy-top",
            "source": "SoMaCoSF/hex-map-wfc cube coords",
            "radius": self.radius,
            "cells": len(self.cells),
            "mines": self.mines,
            "mines_remaining": self._remaining(),
            "board": art,
            "clues": self._clues(),
            "frontier": [cube_key(*c) for c in frontier],
            "flagged": [cube_key(*c) for c in sorted(self.flagged)],
            "dirs": ["+q", "+q-r", "-r", "-q", "-q+r", "+r"],
        }
        if self.style == "raw":
            state = art
        return Observation(
            state=state,
            questions=questions,
            terminal=terminal,
            won=False if self.dead else (True if self.won_flag else None),
            info={"frontier": [cube_key(*c) for c in frontier], "dead": self.dead, "seed": self.seed, "radius": self.radius},
        )

    def step(self, action: Action) -> Observation:
        if self.dead or self.won_flag:
            return self.observe()
        cell = parse_key(action.target)
        if action.kind == "flag":
            if cell not in self.revealed:
                self.flagged.discard(cell) if cell in self.flagged else self.flagged.add(cell)
        elif action.kind == "reveal":
            if self.first_click_pending:
                self._place(cell)
                self.first_click_pending = False
            if cell in self.flagged:
                return self.observe()
            if cell in self.mine_set:
                self.dead = True
            else:
                self._flood(cell)
        hidden = len(self.cells) - len(self.revealed)
        if not self.dead and hidden == self.mines:
            self.won_flag = True
            self.flagged.update(self.mine_set)
        return self.observe()

    def policy(self, answers: dict, observation: Observation) -> Action:
        if self.first_click_pending:
            return Action("reveal", cube_key(0, 0, 0), {"reason": "hex-center"})
        scored: list[tuple[float, str]] = []
        for name, ans in answers.items():
            if not name.startswith("mine_"):
                continue
            cell = name[len("mine_"):]
            p = float(ans.noul) if getattr(ans, "noul", None) is not None else 0.5
            scored.append((p, cell))
        if not scored:
            fr = observation.info.get("frontier") or ["0,0,0"]
            return Action("reveal", fr[0], {"reason": "empty"})
        scored.sort()
        for p, cell in reversed(scored):
            if p >= self.mine_th:
                return Action("flag", cell, {"p": p, "reason": "mine-threshold"})
        for p, cell in scored:
            if p <= self.safe_th:
                return Action("reveal", cell, {"p": p, "reason": "safe-threshold"})
        p, cell = scored[0]
        return Action("reveal", cell, {"p": p, "reason": "lowest-p-guess"})

    def mock_answers(self, state: Any, questions: dict) -> dict:
        derived = self._local_probs()
        out = {}
        for name in questions:
            cell_s = name[len("mine_"):] if name.startswith("mine_") else name
            out[name] = JevAnswer(type="noul", raw={}, noul=derived.get(cell_s, 0.5))
        return out

    def _local_probs(self) -> dict[str, float]:
        forced_mine: set[tuple[int, int, int]] = set()
        forced_safe: set[tuple[int, int, int]] = set()
        for _ in range(8):
            changed = False
            for cell in list(self.revealed):
                n = self.numbers.get(cell, 0)
                nbs = neighbors(*cell, self.radius)
                flags = [x for x in nbs if x in self.flagged or x in forced_mine]
                hidden = [x for x in nbs if x not in self.revealed and x not in self.flagged and x not in forced_mine and x not in forced_safe]
                need = n - len(flags)
                if need <= 0:
                    for h in hidden:
                        if h not in forced_safe:
                            forced_safe.add(h)
                            changed = True
                elif need >= len(hidden) and hidden:
                    for h in hidden:
                        if h not in forced_mine:
                            forced_mine.add(h)
                            changed = True
            if not changed:
                break
        hidden_all = [c for c in self.cells if c not in self.revealed and c not in self.flagged]
        rem = max(self._remaining() - len(forced_mine), 0)
        unk = [h for h in hidden_all if h not in forced_mine and h not in forced_safe]
        base = (rem / len(unk)) if unk else 0.5
        out: dict[str, float] = {}
        for h in hidden_all:
            if h in forced_mine:
                out[cube_key(*h)] = 0.99
            elif h in forced_safe:
                out[cube_key(*h)] = 0.01
            else:
                out[cube_key(*h)] = min(0.9, max(0.1, base))
        return out

    def oracle(self, observation: Observation) -> dict[str, Any]:
        truth = {}
        if not self.first_click_pending:
            for k in observation.info.get("frontier") or []:
                truth[k] = parse_key(k) in self.mine_set
        return {"is_mine": truth, "local_p": self._local_probs(), "lattice": "hex-cube"}
