"""Griductive puzzle generator (member D).

Every puzzle produced is
  * consistent: each card's clue is TRUE under the hidden solution;
  * solvable with NO guessing: built by simulating the deduction loop, so at
    every step at least one unresolved card is logically forced;
  * unique: the complete clue set has exactly one model (re-checked by brute
    force after generation).

Usage
-----
  python tools/generate_puzzles.py --preset                       # default benchmark set
  python tools/generate_puzzles.py --size 4 --count 3 --difficulty hard --seed 7
  python tools/generate_puzzles.py --size 3 --count 2 --extensions parity,compare
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from clues_ref import evaluate, region_mask
from reference import count_solutions, enumerate_models, filter_models, forced_masks, simulate, status_clue
from schema import COLS, EXT_TYPES, all_cells, cell_id, cell_index, region_cells, validate_puzzle

NAMES = ["Abel", "Bea", "Clara", "Derek", "Eliza", "Franz", "Grant", "Hannah", "Ivy", "Jonas",
         "Karl", "Leo", "Mara", "Noah", "Owen", "Priya", "Quilla", "Roy", "Sophia", "Tom",
         "Uma", "Victor", "Wendy", "Xavier", "Yara"]
PROFESSIONS = ["Astronaut", "Clerk", "Cook", "Detective", "Farmer", "Guard", "Painter"]
DEFAULT_INIT = {3: 1, 4: 2, 5: 3}   # number of face-up cards at the start

# (size, difficulty, seed)  -> ids like 3x3_easy_01
PRESET = [(3, "easy", 1), (3, "medium", 2), (3, "medium", 3), (3, "hard", 4), (3, "hard", 5),
          (4, "easy", 11), (4, "medium", 12), (4, "medium", 13), (4, "hard", 14), (4, "hard", 15),
          (5, "medium", 21), (5, "hard", 22),
          # --- batch 2 (appended, so batch 1 ids/seeds stay unchanged)
          (3, "easy", 31), (3, "easy", 32), (3, "medium", 33), (3, "hard", 34),
          (4, "easy", 41), (4, "easy", 42), (4, "medium", 43), (4, "medium", 44),
          (4, "hard", 45), (4, "hard", 46),
          (5, "medium", 51), (5, "hard", 52)]


# ----------------------------------------------------------- candidates ----
def _random_region(n, rng, owner):
    cells = all_cells(n)
    kind = rng.choices(["row", "column", "neighbors", "cells"], [2, 2, 3, 3])[0]
    if kind == "row":
        return {"kind": "row", "row": rng.randint(1, n)}
    if kind == "column":
        return {"kind": "column", "col": COLS[rng.randrange(n)]}
    if kind == "neighbors":
        of = owner if rng.random() < 0.4 else rng.choice(cells)
        return {"kind": "neighbors", "of": of}
    chosen = rng.sample(cells, rng.randint(2, min(5, n * n - 1)))
    return {"kind": "cells", "cells": sorted(chosen, key=lambda c: cell_index(c, n))}


def _count_in(sol, region, n):
    return bin(sol & region_mask(region, n)).count("1")


def make_candidate(n, sol, owner, rng, exts):
    """A random clue that is TRUE under the solution bitmask `sol`."""
    cells = all_cells(n)
    others = [c for c in cells if c != owner]
    crim = lambda c: (sol >> cell_index(c, n)) & 1  # noqa: E731

    if exts and rng.random() < 0.15:
        kind = rng.choice(exts)
        if kind == "parity":
            reg = _random_region(n, rng, owner)
            return {"type": "PARITY", "region": reg,
                    "parity": "EVEN" if _count_in(sol, reg, n) % 2 == 0 else "ODD"}
        left, right = _random_region(n, rng, owner), _random_region(n, rng, owner)
        if region_mask(left, n) != region_mask(right, n):
            a, b = _count_in(sol, left, n), _count_in(sol, right, n)
            return {"type": "COMPARE", "left": left, "right": right,
                    "op": "<" if a < b else (">" if a > b else "==")}

    r = rng.random()
    if r < 0.08:
        c = rng.choice(others)
        return {"type": "FACT", "cell": c, "status": "CRIMINAL" if crim(c) else "INNOCENT"}
    if r < 0.20:
        a, b = rng.sample(others, 2)
        return {"type": "SAME" if crim(a) == crim(b) else "DIFFERENT", "a": a, "b": b}

    reg = _random_region(n, rng, owner)
    size, cnt = len(region_cells(reg, n)), _count_in(sol, reg, n)
    r2 = rng.random()
    if r2 < 0.6 or (r2 < 0.8 and cnt == 0) or (r2 >= 0.8 and cnt == size):
        return {"type": "EXACTLY", "region": reg, "k": cnt}
    if r2 < 0.8:
        return {"type": "AT_LEAST", "region": reg, "k": rng.randint(max(1, cnt - 1), cnt)}
    return {"type": "AT_MOST", "region": reg, "k": rng.randint(cnt, min(cnt + 1, size - 1))}


def _choose_clue(models, n, sol, owner, unrev_mask, need_progress, difficulty, rng, exts,
                 batch=14, rounds=6):
    """Pick a true clue for `owner`.
    easy = most informative, hard = least informative that still keeps a forced
    card available (when need_progress), medium = random informative one."""
    scored = []
    for _ in range(rounds):
        seen = set()
        for _ in range(batch):
            c = make_candidate(n, sol, owner, rng, exts)
            key = json.dumps(c, sort_keys=True)
            if key in seen:
                continue
            seen.add(key)
            new = filter_models(models, c, n)
            if need_progress:
                cr, inn = forced_masks(new, n)
                if not ((cr | inn) & unrev_mask):
                    continue
            scored.append((len(models) - len(new), c))
        if scored:
            break
    if not scored:
        return None
    pool = [s for s in scored if s[0] > 0] or scored
    if difficulty == "easy":
        best = max(g for g, _ in pool)
        pool = [s for s in pool if s[0] == best]
    elif difficulty == "hard":
        worst = min(g for g, _ in pool)
        pool = [s for s in pool if s[0] == worst]
    return rng.choice(pool)[1]


# ------------------------------------------------------------- building ----
def _try_build(n, difficulty, seed, exts, n_init, rng):
    n2, cells = n * n, all_cells(n)
    lo, hi = max(1, round(0.3 * n2)), min(n2 - 1, round(0.6 * n2))
    while True:
        sol = rng.getrandbits(n2)
        if lo <= bin(sol).count("1") <= hi:
            break
    status = lambda c: "CRIMINAL" if (sol >> cell_index(c, n)) & 1 else "INNOCENT"  # noqa: E731
    init = [cells[i] for i in sorted(rng.sample(range(n2), n_init))]
    models = enumerate_models(n, [status_clue(c, status(c)) for c in init])
    unrev_mask, clues = (1 << n2) - 1, {}

    for j, c in enumerate(init):
        unrev_mask &= ~(1 << cell_index(c, n))
        clue = _choose_clue(models, n, sol, c, unrev_mask, j == len(init) - 1, difficulty, rng, exts)
        if clue is None:
            return None
        clues[c] = clue
        models = filter_models(models, clue, n)

    order, unrevealed = [], [c for c in cells if c not in init]
    while unrevealed:
        cr, inn = forced_masks(models, n)
        forced = [c for c in unrevealed if ((cr | inn) >> cell_index(c, n)) & 1]
        if not forced:
            return None
        c = forced[0]
        unrev_mask &= ~(1 << cell_index(c, n))
        clue = _choose_clue(models, n, sol, c, unrev_mask, len(unrevealed) > 1, difficulty, rng, exts)
        if clue is None:
            return None
        clues[c] = clue
        models = filter_models(models, clue, n)
        unrevealed.remove(c)
        order.append(c)
    if len(models) != 1:
        return None

    names = sorted(rng.sample(NAMES, n2))       # alphabetical, filled column by column
    info = [{"id": cell_id(r, col), "row": r + 1, "col": COLS[col],
             "name": names[col * n + r], "profession": rng.choice(PROFESSIONS)}
            for r in range(n) for col in range(n)]
    return {"size": n, "difficulty": difficulty, "cells": info,
            "solution": {c: status(c) for c in cells},
            "initial_revealed": init, "clues": {c: clues[c] for c in cells},
            "meta": {"seed": seed, "reveal_order": order, "extensions": list(exts)}}


def build_puzzle(pid, n, difficulty, seed, exts=(), n_init=None, max_tries=300):
    n_init = n_init or DEFAULT_INIT[n]
    for attempt in range(max_tries):
        rng = random.Random(seed * 1000 + attempt)
        p = _try_build(n, difficulty, seed, tuple(exts), n_init, rng)
        if p is None:
            continue
        p = {"id": pid, **p}
        p["meta"]["attempt"] = attempt
        # independent re-verification (full enumeration)
        assert not validate_puzzle(p), validate_puzzle(p)
        # The complete clue set ALONE (without the face-up statuses) must be unique,
        # because the agent's uniqueness check only sees clues.
        if count_solutions(p) != 1:
            continue
        sim = simulate(p)
        assert sim["solved"] and [t["cell"] for t in sim["trace"]] == p["meta"]["reveal_order"]
        return p
    raise RuntimeError(f"could not build {pid} in {max_tries} tries")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", action="store_true", help="generate the default benchmark set")
    ap.add_argument("--size", type=int, choices=(3, 4, 5))
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--difficulty", choices=("easy", "medium", "hard"), default="medium")
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--init", type=int, help="number of initially face-up cards")
    ap.add_argument("--extensions", default="", help="comma list from: " + ",".join(EXT_TYPES).lower())
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent.parent / "puzzles"))
    a = ap.parse_args()
    exts = [e for e in a.extensions.lower().split(",") if e]

    if not a.preset and not a.size:
        a.preset = True   # no mode given (e.g. IDE Run button): build the default set
    jobs = []
    if a.preset:
        counters = {}
        for n, d, s in PRESET:
            counters[(n, d)] = counters.get((n, d), 0) + 1
            jobs.append((f"{n}x{n}_{d}_{counters[(n, d)]:02d}", n, d, s))
    elif a.size:
        jobs = [(f"{a.size}x{a.size}_{a.difficulty}_{a.seed + i:02d}", a.size, a.difficulty, a.seed + i)
                for i in range(a.count)]

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for pid, n, d, s in jobs:
        p = build_puzzle(pid, n, d, s, exts, a.init)
        (out / f"{pid}.json").write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {out / (pid + '.json')}  (attempt {p['meta']['attempt']}, {len(p['meta']['reveal_order'])} reveals)")


if __name__ == "__main__":
    main()