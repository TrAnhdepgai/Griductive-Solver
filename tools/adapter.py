"""Glue between member D's tools and the other members' code.

Only THIS file needs editing once A/B/C have a first working version:
  * run_team(path)      -> used by  benchmark.py --backend team
  * team_evaluate(...)  -> used by  cross_check.py   (member A's semantic evaluator)
  * team_encode(...)    -> used by  cross_check.py   (member A's CNF encoder)

`run_reference` already works (brute force) so the benchmark harness can be
tested before the real agent exists.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

SOURCE_ROOT = Path(__file__).resolve().parent.parent   # Source/  (so `import engine`, `import agent` ... work)
if str(SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(SOURCE_ROOT))

# Keys every backend should return. Use None when a number does not apply.
METRIC_KEYS = ["primary_vars", "aux_vars", "clauses", "sat_calls", "decisions",
               "propagations", "backtracks", "steps", "waves", "runtime_s", "solved"]


def run_reference(path: str) -> dict:
    """Brute-force backend: only steps/waves/runtime are meaningful (no SAT stats)."""
    from reference import simulate
    from schema import load_puzzle
    p = load_puzzle(path)
    t0 = time.perf_counter()
    sim = simulate(p)
    dt = time.perf_counter() - t0
    out = dict.fromkeys(METRIC_KEYS)
    out.update(primary_vars=p["size"] ** 2, steps=sim["steps"], waves=sim["waves"],
               runtime_s=dt, solved=sim["solved"])
    return out


def run_team(path: str) -> dict:
    """TODO(D + B): run the team's full pipeline on one puzzle file and return METRIC_KEYS.

    Sketch (rename to match the real modules):

        from engine import GameEngine            # member C
        from agent import LogicAgent             # member B
        engine = GameEngine.load(path)
        agent = LogicAgent(engine)               # agent only gets public state
        t0 = time.perf_counter()
        result = agent.run()                     # runs until solved / stuck / inconsistent
        dt = time.perf_counter() - t0
        cnf, sat = agent.cnf_stats, agent.sat_stats
        return {
            "primary_vars": cnf.primary_vars, "aux_vars": cnf.aux_vars, "clauses": cnf.clauses,
            "sat_calls": sat.calls, "decisions": sat.decisions,
            "propagations": sat.propagations, "backtracks": sat.backtracks,
            "steps": len(result.trace), "waves": result.waves,
            "runtime_s": dt, "solved": engine.is_solved(),
        }
    """
    raise NotImplementedError("Edit run_team() in tools/adapter.py to call the team's agent.")


def team_evaluate(clue: dict, assignment: dict, n: int) -> bool:
    """TODO(A): call the team's direct semantic evaluator.
    `assignment` maps cell id -> True (criminal) / False (innocent) for ALL cells."""
    raise NotImplementedError("Edit team_evaluate() in tools/adapter.py.")


def team_encode(clue: dict, n: int) -> list[list[int]]:
    """TODO(A): return the CNF clauses (DIMACS ints) for ONE clue.
    Primary variables must be 1..n*n in row-major order (see schema.py);
    auxiliary variables, if any, must be > n*n."""
    raise NotImplementedError("Edit team_encode() in tools/adapter.py.")