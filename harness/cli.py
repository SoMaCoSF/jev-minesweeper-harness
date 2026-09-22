"""Run Jev against a world and write JSONL traces."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from jev_client.client import JevAnswer, JevClient
from worlds.generic import GenericWorld
from worlds.minesweeper import MinesweeperWorld


def build_world(args: argparse.Namespace):
    if args.world == "generic":
        return GenericWorld(spec_path=args.spec)
    return MinesweeperWorld(preset=args.preset, style=args.style, safe_th=args.safe, mine_th=args.mine)


def run_game(world, client: JevClient, seed: int, mode: str, max_moves: int) -> dict:
    obs = world.reset(seed)
    moves = []
    tokens = 0
    t0 = time.perf_counter()
    for i in range(max_moves):
        if obs.terminal:
            break
        result_meta = {"mocked": True, "model": "local-solver", "latency_ms": 0.0, "input_tokens": 0}
        if mode == "solver" and hasattr(world, "_local_probs"):
            derived = world._local_probs()
            answers = {
                name: JevAnswer(type="noul", raw={}, noul=derived.get(name[len("mine_"):], 0.5))
                for name in obs.questions
            }
        else:
            if mode == "mock":
                client.mock = True
                client.mock_fn = world.mock_answers
            result = client.decide(obs.state, obs.questions)
            answers = result.answers
            tokens += result.input_tokens
            result_meta = {
                "mocked": result.mocked,
                "model": result.model,
                "latency_ms": result.latency_ms,
                "input_tokens": result.input_tokens,
            }
            if mode == "hybrid" and hasattr(world, "_local_probs"):
                local = world._local_probs()
                confident = False
                for ans in answers.values():
                    p = ans.noul if ans.noul is not None else 0.5
                    if p <= world.safe_th or p >= world.mine_th:
                        confident = True
                        break
                if not confident:
                    answers = {
                        name: JevAnswer(type="noul", raw={}, noul=local.get(name[len("mine_"):], 0.5))
                        for name in obs.questions
                    }
                    result_meta["routed"] = "solver"
        action = world.policy(answers, obs)
        oracle = world.oracle(obs)
        moves.append({
            "move": i,
            "action": action.__dict__,
            "answers": {
                k: {"type": v.type, "noul": v.noul, "choice": v.choice, "score": v.score, "confidence": v.confidence}
                for k, v in answers.items()
            },
            "oracle": oracle,
            "meta": result_meta,
        })
        obs = world.step(action)
    return {
        "seed": seed,
        "world": world.name,
        "won": bool(obs.won),
        "dead": bool(getattr(world, "dead", False)),
        "moves": len(moves),
        "tokens": tokens,
        "ms": (time.perf_counter() - t0) * 1000,
        "trace": moves,
        "terminal": obs.terminal,
    }


def main() -> None:
    p = argparse.ArgumentParser(description="Jev world harness")
    p.add_argument("--world", choices=["minesweeper", "generic"], default="minesweeper")
    p.add_argument("--mode", choices=["mock", "jev", "hybrid", "solver"], default="mock")
    p.add_argument("--preset", default="beginner")
    p.add_argument("--style", choices=["raw", "digested"], default="digested")
    p.add_argument("--games", type=int, default=5)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--safe", type=float, default=0.07)
    p.add_argument("--mine", type=float, default=0.85)
    p.add_argument("--max-moves", type=int, default=120)
    p.add_argument("--spec", default=None)
    p.add_argument("--out", default="runs/latest.jsonl")
    args = p.parse_args()

    world = build_world(args)
    client = JevClient(mock=args.mode != "jev")
    if args.mode == "jev":
        client.mock = False
        if not client.api_key:
            raise SystemExit("TYPESAFE_API_KEY required for --mode jev")

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    wins = 0
    with out_path.open("w", encoding="utf-8") as fh:
        for i in range(args.games):
            summary = run_game(world, client, args.seed + i, args.mode, args.max_moves)
            wins += int(summary["won"])
            print(f"game {i} seed={summary['seed']} won={summary['won']} moves={summary['moves']} tokens={summary['tokens']}")
            fh.write(json.dumps(summary) + "\n")
    print(f"winrate {wins}/{args.games} -> {out_path}")


if __name__ == "__main__":
    main()
