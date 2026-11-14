"""Brute-force reference solver (member D).

Enumerates every complete assignment (2^(N*N)) with numpy, so it is exact but
only meant for testing / generating puzzles, NOT as the project's solver.
"""
from __future__ import annotations

import numpy as np

from clues_ref import evaluate
from schema import all_cells, cell_index

CHUNK_BITS = 22  # process at most 4M assignments at a time (keeps 5x5 memory sane)


def status_clue(cell: str, status: str) -> dict:
    return {"type": "FACT", "cell": cell, "status": status}


def enumerate_models(n: int, clues: list[dict]) -> np.ndarray:
    """All assignments (uint32 bitmasks) satisfying every clue."""
    bits = n * n
    chunk = 1 << min(bits, CHUNK_BITS)
    parts = []
    for start in range(0, 1 << bits, chunk):
        m = np.arange(start, start + chunk, dtype=np.uint32)
        for c in clues:
            if len(m) == 0:
                break
            m = m[evaluate(c, m, n)]
        parts.append(m)
    return np.concatenate(parts)


def filter_models(models: np.ndarray, clue: dict, n: int) -> np.ndarray:
    return models[evaluate(clue, models, n)]


def forced_masks(models: np.ndarray, n: int) -> tuple[int, int]:
    """(criminal_mask, innocent_mask): bits whose value is identical in all models."""
    if len(models) == 0:
        return 0, 0
    full = np.uint32((1 << (n * n)) - 1)
    return int(np.bitwise_and.reduce(models)), int(np.bitwise_and.reduce(~models & full))


def count_solutions(puzzle: dict) -> int:
    """Models of the COMPLETE clue set (uniqueness check). A valid puzzle gives 1."""
    n = puzzle["size"]
    return len(enumerate_models(n, [puzzle["clues"][c] for c in all_cells(n)]))


def simulate(puzzle: dict) -> dict:
    """Play the no-guess deduction loop with exact entailment (row-major choice).

    Initial face-up cards contribute their status (unit literal) and clue.
    Each step reveals the first forced unresolved cell and adds its clue.
    `waves`: a new wave starts whenever every cell that was forced at the
    start of the previous wave has been revealed.
    """
    n, sol, clues = puzzle["size"], puzzle["solution"], puzzle["clues"]
    cells = all_cells(n)
    revealed = list(puzzle["initial_revealed"])
    kb = [status_clue(c, sol[c]) for c in revealed] + [clues[c] for c in revealed]
    models = enumerate_models(n, kb)
    unrevealed = [c for c in cells if c not in revealed]
    trace, waves, pending, status = [], 0, set(), "SOLVED"
    while unrevealed:
        if len(models) == 0:
            status = "INCONSISTENT"
            break
        crim, inno = forced_masks(models, n)
        forced = [c for c in unrevealed if ((crim | inno) >> cell_index(c, n)) & 1]
        if not forced:
            status = "STUCK"
            break
        if not pending:
            waves += 1
            pending = set(forced)
        cell = forced[0]  # `unrevealed` stays in row-major order
        verdict = "CRIMINAL" if (crim >> cell_index(cell, n)) & 1 else "INNOCENT"
        before = len(models)
        models = filter_models(models, clues[cell], n)
        trace.append({"step": len(trace) + 1, "cell": cell, "verdict": verdict,
                      "clue": clues[cell], "models_before": before,
                      "models_after": len(models), "forced_available": len(forced)})
        pending.discard(cell)
        unrevealed.remove(cell)
    correct = all(t["verdict"] == sol[t["cell"]] for t in trace)
    return {"status": status, "solved": status == "SOLVED" and correct, "correct": correct,
            "steps": len(trace), "waves": waves, "trace": trace, "final_models": len(models)}