"""Uniqueness check for the COMPLETE clue set (section 4.4).

Separate from the play loop: it is a puzzle-validation tool and therefore may
read every clue. It encodes all clues with member A's encoder and enumerates
models with DPLL + blocking clauses on the primary variables. A valid puzzle
has exactly one model.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Optional

from src.sat import SolverStats, count_models

from .interface import PublicState, cells_for_size
from .knowledge import build_kb


@dataclass
class UniquenessReport:
    unique: bool
    model_count: int            # number of models found (capped by `limit`)
    exhaustive: bool            # True if model_count is exact
    solution: Optional[Dict[str, str]]   # the model when unique
    models: list                # every model found, as cell -> status
    kb_stats: Dict[str, int]
    sat_stats: SolverStats

    def summary(self) -> str:
        if self.unique:
            return "UNIQUE (exactly one model)"
        if self.model_count == 0:
            return "NO SOLUTION (clue set is inconsistent)"
        more = "" if self.exhaustive else "+"
        return f"AMBIGUOUS ({self.model_count}{more} models)"


def check_uniqueness(clues: Dict[str, dict], size: int, facts: Optional[Dict[str, str]] = None,
                     limit: int = 2, heuristic: str = "first") -> UniquenessReport:
    """Count models of all `clues` (owner cell -> clue), optionally with known `facts`.

    limit=2 is enough to decide uniqueness; pass a bigger limit (or None) to
    list more alternative solutions of an ambiguous puzzle.
    """
    state = PublicState(size, cells_for_size(size), dict(facts or {}), dict(clues))
    kb = build_kb(state)
    primary = [kb.var_of[c] for c in state.cell_ids]
    mc = count_models(kb.clauses, primary, num_vars=kb.num_vars, limit=limit, heuristic=heuristic)
    models = [{kb.cell_of[v]: ("CRIMINAL" if val else "INNOCENT") for v, val in m.items()}
              for m in mc.models]
    unique = mc.count == 1 and mc.complete
    return UniquenessReport(unique, mc.count, mc.complete, models[0] if unique else None,
                            models, kb.stats(), mc.stats)


def check_puzzle_uniqueness(puzzle: dict, limit: int = 2, heuristic: str = "first") -> UniquenessReport:
    """Uniqueness of a puzzle dict in the team JSON schema (uses `clues` only, not `solution`)."""
    return check_uniqueness(puzzle["clues"], puzzle["size"], limit=limit, heuristic=heuristic)
