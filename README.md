# jev-minesweeper-harness

Jev does not chat. It returns typed probabilities. This repo treats that as a testable control loop, not a demo.

Russell Gokemeijer's MinesweeperBot (https://github.com/Russellgoke/MinesweeperBot) is a classic probability trainer. It has **no Jev**. Existing toys already prove the meme (jevsweeper.neato.fun, comoc/jev-minesweeper). This harness measures the model, then swaps the board for any other partial-observation world.

## Mapping

Minesweeper is a hidden-label field with local linear constraints. Same shape as tickets, posts, inventory, UUID routing, market resolution:

- mine/safe -> hidden boolean or class
- neighbor count -> local evidence bundle
- flag -> commit / quarantine / escalate
- reveal -> sample / fetch / open
- forced guess -> residual uncertainty
- explosion -> irreversible bad action

Loop: observe -> encode state -> batch Noul/Choice/Score -> policy on probabilities -> mutate world -> log vs oracle.

## What it reveals

1. Calibration of noul vs true P(mine|visible).
2. Missed deductions vs forced guesses (solver oracle before the death click).
3. Raw ASCII vs digested clues (does Jev do the arithmetic?).
4. Confidence-gated hybrid routing to solver/human.
5. Cost/latency envelope.
6. Question-shape disagreement (per-cell noul vs frontier choice vs guess score).

## Run

    pip install -r requirements.txt
    python -m harness.cli --world minesweeper --mode mock --games 20
    python -m harness.cli --world minesweeper --mode jev --style digested --games 10
    python -m harness.cli --world minesweeper --mode hybrid
    python -m harness.cli --world generic --spec examples/ticket_triage.json

TYPESAFE_API_KEY required for --mode jev. Traces: runs/latest.jsonl
