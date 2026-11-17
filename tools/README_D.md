# Member D tools: puzzles, verification, experiments

Requires `numpy` (add it to `requirements.txt`). Run everything from `Source/`.

```
python tools/generate_puzzles.py --preset      # regenerate puzzles/ (deterministic seeds)
python tools/verify_puzzles.py                 # brute-force validity check of every puzzle
python tools/cross_check.py                    # A's evaluator + CNF encoder vs brute force
python tools/benchmark.py --backend reference  # works now (brute force, no SAT stats)
python tools/benchmark.py --backend team --timeout 60 --repeats 3   # after wiring adapter.py
```

Wire the team's code in **`tools/adapter.py` only**: `run_team`, `team_evaluate`, `team_encode`.
Results go to `experiments/results/benchmark_<backend>.{csv,json,md,tex}`.

## Conventions (everyone should follow)

* Cell id = column letter + row number (`C2`). Row-major index `i = (row-1)*N + col`.
* CNF variable of cell `i` = `i + 1` (3x3: A1=1, B1=2, C1=3, A2=4 ... C3=9). Aux variables are `> N*N`.
* Names are alphabetical, filled column by column (A1, A2, ... then B1, ...), like the original game.

## Puzzle JSON schema

```json
{
  "id": "3x3_easy_01", "size": 3, "difficulty": "easy",
  "cells": [{"id": "A1", "row": 1, "col": "A", "name": "Abel", "profession": "Clerk"}, "... row-major"],
  "solution": {"A1": "CRIMINAL", "...": "INNOCENT"},        // Game Engine ONLY
  "initial_revealed": ["B2"],                                // face-up at start: status + clue are public
  "clues": {"A1": {"type": "EXACTLY", "region": {"kind": "row", "row": 1}, "k": 2}, "...": {}},
  "meta": {"seed": 1, "reveal_order": ["A1", "..."], "extensions": []}
}
```

Clue objects (one per cell, all TRUE under `solution`):

| type | fields |
|---|---|
| FACT | `cell`, `status` (`CRIMINAL`/`INNOCENT`) |
| SAME / DIFFERENT | `a`, `b` |
| EXACTLY / AT_LEAST / AT_MOST | `region`, `k` |
| PARITY (ext.) | `region`, `parity` (`EVEN`/`ODD`) |
| COMPARE (ext.) | `left`, `right` (regions), `op` (`<`, `==`, `>`) |

Regions: `{"kind":"row","row":2}`, `{"kind":"column","col":"B"}`,
`{"kind":"neighbors","of":"B2"}`, `{"kind":"cells","cells":["A1","C3"]}`.

PARITY and COMPARE are only generated with `--extensions parity,compare` and are **off in the preset
set**. Team members A and D must agree on which two extensions the project implements; if they differ,
change `EXT_TYPES`, `make_candidate` (generator) and `clues_ref.evaluate`.

## Guarantees of generated puzzles

1. Every clue is true under the hidden solution.
2. The complete clue set alone has exactly one model (brute-force checked).
3. The no-guess loop solves it: at each step at least one card is forced, and the row-major
   choice reproduces `meta.reveal_order`.

`waves` (also reported by `simulate`): a new wave starts when every card forced at the start of the
previous wave has been revealed. Use the same definition for the team backend, or state your own in the report.