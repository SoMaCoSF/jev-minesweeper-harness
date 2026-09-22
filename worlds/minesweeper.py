"""Seeded Minesweeper world with a cheap constraint oracle."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from jev_client.client import JevAnswer
from .protocol import Action, Observation

PRESETS = {"beginner": (9, 9, 10), "intermediate": (16, 16, 40)}


def _neighbors(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols:
                out.append((rr, cc))
    return out


def _key(r: int, c: int) -> str:
    return f"{r},{c}"


@dataclass
class MinesweeperWorld:
    name: str = "minesweeper"
    preset: str = "beginner"
    style: str = "digested"
    safe_th: float = 0.07
    mine_th: float = 0.85
    rows: int = 9
    cols: int = 9
    mines: int = 10
    rng: random.Random = field(default_factory=random.Random)
    mine_set: set[tuple[int, int]] = field(default_factory=set)
    revealed: set[tuple[int, int]] = field(default_factory=set)
    flagged: set[tuple[int, int]] = field(default_factory=set)
    numbers: dict[tuple[int, int], int] = field(default_factory=dict)
    dead: bool = False
    won_flag: bool = False
    first_click_pending: bool = True
    seed: int = 0

    def __post_init__(self) -> None:
        self.rows, self.cols, self.mines = PRESETS.get(self.preset, (self.rows, self.cols, self.mines))

    def reset(self, seed: int | None = None) -> Observation:
        self.seed = 0 if seed is None else seed
        self.rng = random.Random(self.seed)
        self.revealed.clear()
        self.flagged.clear()
        self.dead = False
        self.won_flag = False
        self.first_click_pending = True
        self.mine_set = set()
        self.numbers = {}
        return self.observe()

    def _place_mines(self, safe: tuple[int, int]) -> None:
        cells = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) != safe]
        self.rng.shuffle(cells)
        self.mine_set = set(cells[: self.mines])
        self.numbers = {}
        for r in range(self.rows):
            for c in range(self.cols):
                if (r, c) in self.mine_set:
                    continue
                self.numbers[(r, c)] = sum(1 for nb in _neighbors(r, c, self.rows, self.cols) if nb in self.mine_set)

    def _flood(self, start: tuple[int, int]) -> None:
        stack = [start]
        while stack:
            cell = stack.pop()
            if cell in self.revealed or cell in self.mine_set:
                continue
            self.revealed.add(cell)
            if self.numbers.get(cell, 0) == 0:
                stack.extend(_neighbors(*cell, self.rows, self.cols))

    def _ascii(self) -> str:
        lines = [f"Minesweeper {self.rows}x{self.cols} mines={self.mines} remaining={self._remaining()}"]
        lines.append("    " + " ".join(f"{c:2d}" for c in range(self.cols)))
        for r in range(self.rows):
            cells = []
            for c in range(self.cols):
                if (r, c) in self.flagged:
                    cells.append(" F")
                elif (r, c) not in self.revealed:
                    cells.append(" .")
                else:
                    cells.append(f" {self.numbers.get((r, c), 0)}")
            lines.append(f"{r:2d} " + "".join(cells))
        return "\n".join(lines)

    def _frontier(self) -> list[tuple[int, int]]:
        seen: set[tuple[int, int]] = set()
        out: list[tuple[int, int]] = []
        for cell in self.revealed:
            for nb in _neighbors(*cell, self.rows, self.cols):
                if nb not in self.revealed and nb not in self.flagged and nb not in seen:
                    seen.add(nb)
                    out.append(nb)
        if not out:
            out = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in self.revealed and (r, c) not in self.flagged]
        return out

    def _remaining(self) -> int:
        return self.mines - len(self.flagged)

    def _clue_lines(self) -> list[str]:
        lines = []
        for r, c in sorted(self.revealed):
            n = self.numbers.get((r, c), 0)
            nbs = _neighbors(r, c, self.rows, self.cols)
            flags = [nb for nb in nbs if nb in self.flagged]
            hidden = [nb for nb in nbs if nb not in self.revealed and nb not in self.flagged]
            need = n - len(flags)
            hid = ", ".join(_key(*h) for h in hidden) or "(none)"
            lines.append(f"{_key(r,c)} shows {n}; {len(flags)} flagged; needs {need} more mine(s) among {len(hidden)} hidden: {hid}")
        return lines

    def observe(self) -> Observation:
        terminal = self.dead or self.won_flag
        frontier = self._frontier()
        questions: dict[str, Any] = {}
        for cell in frontier:
            k = f"mine_{_key(*cell)}"
            if self.style == "raw":
                instr = f"Given the visible Minesweeper board, is cell {_key(*cell)} a mine? Answer yes only if the visible numbers force it."
            else:
                local = [line for line in self._clue_lines() if _key(*cell) in line]
                instr = f"Is hidden cell {_key(*cell)} a mine? Mines remaining: {self._remaining()}. Local clues:\n" + "\n".join(local[:12])
            questions[k] = {"type": "noul", "instructions": instr}
        if self.style == "raw":
            state: Any = self._ascii()
        else:
            state = {
                "preset": self.preset,
                "rows": self.rows,
                "cols": self.cols,
                "mines": self.mines,
                "mines_remaining": self._remaining(),
                "board_ascii": self._ascii(),
                "clues": self._clue_lines(),
                "frontier": [_key(*c) for c in frontier],
                "flagged": [_key(*c) for c in sorted(self.flagged)],
            }
        return Observation(
            state=state,
            questions=questions,
            terminal=terminal,
            won=False if self.dead else (True if self.won_flag else None),
            info={"frontier": [_key(*c) for c in frontier], "dead": self.dead, "seed": self.seed, "style": self.style},
        )

    def step(self, action: Action) -> Observation:
        if self.dead or self.won_flag:
            return self.observe()
        r, c = (int(x) for x in action.target.split(","))
        cell = (r, c)
        if action.kind == "flag":
            if cell not in self.revealed:
                self.flagged.discard(cell) if cell in self.flagged else self.flagged.add(cell)
        elif action.kind == "reveal":
            if self.first_click_pending:
                self._place_mines(cell)
                self.first_click_pending = False
            if cell in self.flagged:
                return self.observe()
            if cell in self.mine_set:
                self.dead = True
            else:
                self._flood(cell)
        hidden = self.rows * self.cols - len(self.revealed)
        if not self.dead and hidden == self.mines:
            self.won_flag = True
            self.flagged.update(self.mine_set)
        return self.observe()

    def policy(self, answers: dict, observation: Observation) -> Action:
        if self.first_click_pending:
            return Action("reveal", _key(self.rows // 2, self.cols // 2), {"reason": "opening"})
        scored: list[tuple[float, str]] = []
        for name, ans in answers.items():
            if not name.startswith("mine_"):
                continue
            cell = name[len("mine_"):]
            p = float(ans.noul) if getattr(ans, "noul", None) is not None else 0.5
            scored.append((p, cell))
        if not scored:
            fr = observation.info.get("frontier") or ["0,0"]
            return Action("reveal", fr[0], {"reason": "empty-answers"})
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
        out: dict[str, JevAnswer] = {}
        for name in questions:
            cell_s = name[len("mine_"):] if name.startswith("mine_") else name
            out[name] = JevAnswer(type="noul", raw={}, noul=derived.get(cell_s, 0.5))
        return out

    def _local_probs(self) -> dict[str, float]:
        forced_mine: set[tuple[int, int]] = set()
        forced_safe: set[tuple[int, int]] = set()
        for _ in range(8):
            changed = False
            for cell in list(self.revealed):
                n = self.numbers.get(cell, 0)
                nbs = _neighbors(*cell, self.rows, self.cols)
                flags = [nb for nb in nbs if nb in self.flagged or nb in forced_mine]
                hidden = [nb for nb in nbs if nb not in self.revealed and nb not in self.flagged and nb not in forced_mine and nb not in forced_safe]
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
        hidden_all = [(r, c) for r in range(self.rows) for c in range(self.cols) if (r, c) not in self.revealed and (r, c) not in self.flagged]
        rem = max(self._remaining() - len(forced_mine), 0)
        unk = [h for h in hidden_all if h not in forced_mine and h not in forced_safe]
        base = (rem / len(unk)) if unk else 0.5
        out: dict[str, float] = {}
        for h in hidden_all:
            if h in forced_mine:
                out[_key(*h)] = 0.99
            elif h in forced_safe:
                out[_key(*h)] = 0.01
            else:
                out[_key(*h)] = min(0.9, max(0.1, base))
        return out

    def oracle(self, observation: Observation) -> dict[str, Any]:
        truth = {}
        if not self.first_click_pending:
            for cell_s in observation.info.get("frontier") or []:
                r, c = (int(x) for x in cell_s.split(","))
                truth[cell_s] = (r, c) in self.mine_set
        return {"is_mine": truth, "local_p": self._local_probs(), "first_click": self.first_click_pending}
