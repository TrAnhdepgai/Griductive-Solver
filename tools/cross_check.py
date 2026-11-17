"""Cross-check member A's evaluator and CNF encoder against brute force (member D).

For many clues (all clues in puzzles/ + random true/false-capable ones) and many
complete assignments it checks:
  1. adapter.team_evaluate(clue, assignment)  ==  reference evaluator
  2. CNF from adapter.team_encode(clue) is satisfiable with the primary
     variables fixed to the assignment  <=>  the clue is true there
     (auxiliary variables are existentially quantified).

  python tools/cross_check.py                 # 3x3 exhaustive, 4x4/5x5 sampled
  python tools/cross_check.py --samples 5000 --random-clues 300 --skip-encoder
"""
from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

import adapter
from clues_ref import evaluate
from generate_puzzles import make_candidate
from schema import all_cells, load_puzzle


def _assign(clauses, lit):
    out = []
    for c in clauses:
        if lit in c:
            continue
        if -lit in c:
            c = [x for x in c if x != -lit]
            if not c:
                return None
        out.append(c)
    return out


def tiny_sat(clauses) -> bool:
    """Minimal DPLL used only to test CNFs (independent from member B's solver)."""
    if any(len(c) == 0 for c in clauses):
        return False
    while True:
        unit = next((c[0] for c in clauses if len(c) == 1), None)
        if unit is None:
            break
        clauses = _assign(clauses, unit)
        if clauses is None:
            return False
    if not clauses:
        return True
    lit = clauses[0][0]
    for l in (lit, -lit):
        r = _assign(clauses, l)
        if r is not None and tiny_sat(r):
            return True
    return False


def test_clues(files, n, random_clues, rng):
    clues = []
    for f in files:
        p = load_puzzle(f)
        if p["size"] == n:
            clues += list(p["clues"].values())
    for _ in range(random_clues):
        clues.append(make_candidate(n, rng.getrandbits(n * n), rng.choice(all_cells(n)), rng, ["parity", "compare"]))
    return clues


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--samples", type=int, default=400, help="random assignments per clue for N=4,5")
    ap.add_argument("--random-clues", type=int, default=60, help="extra random clues per size")
    ap.add_argument("--skip-encoder", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    files = sorted((Path(__file__).resolve().parent.parent / "puzzles").glob("*.json"))
    failures = checked = 0
    try:
        for n in (3, 4, 5):
            cells = all_cells(n)
            clues = test_clues(files, n, a.random_clues, rng)
            masks = list(range(1 << (n * n))) if n == 3 else [rng.getrandbits(n * n) for _ in range(a.samples)]
            for clue in clues:
                cnf = None if a.skip_encoder else adapter.team_encode(clue, n)
                for m in masks:
                    assignment = {c: bool((m >> i) & 1) for i, c in enumerate(cells)}
                    want = bool(evaluate(clue, m, n))
                    checked += 1
                    got = bool(adapter.team_evaluate(clue, assignment, n))
                    if got != want:
                        failures += 1
                        print(f"[EVAL ] N={n} mask={m:0{n*n}b} clue={clue} team={got} ref={want}")
                    if cnf is not None:
                        units = [[(i + 1) if (m >> i) & 1 else -(i + 1)] for i in range(n * n)]
                        sat = tiny_sat([list(c) for c in cnf] + units)
                        if sat != want:
                            failures += 1
                            print(f"[CNF  ] N={n} mask={m:0{n*n}b} clue={clue} cnf_sat={sat} ref={want}")
                    if failures >= 20:
                        print("stopping after 20 failures")
                        return 1
            print(f"N={n}: {len(clues)} clues x {len(masks)} assignments checked")
    except NotImplementedError as e:
        print(f"adapter not wired yet: {e}")
        return 2
    print(f"\n{checked} checks, {failures} failures")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())