"""Verify puzzle files by brute force (member D).

Checks per puzzle: schema, every clue true under the solution, the complete
clue set has exactly one model, and the no-guess deduction loop solves it.

  python tools/verify_puzzles.py                 # all of puzzles/
  python tools/verify_puzzles.py puzzles/3x3_easy_01.json
"""
from __future__ import annotations

import sys
from pathlib import Path

from clues_ref import evaluate
from reference import count_solutions, simulate
from schema import all_cells, load_puzzle, solution_mask, validate_puzzle


def check_file(path) -> dict:
    p = load_puzzle(path)
    errs = validate_puzzle(p)
    res = {"file": Path(path).name, "errors": errs, "models": None, "steps": None, "waves": None}
    if errs:
        return res
    n, mask = p["size"], solution_mask(p)
    for c in all_cells(n):
        if not evaluate(p["clues"][c], mask, n):
            errs.append(f"clue of {c} is false under the stored solution")
    res["models"] = count_solutions(p)
    if res["models"] != 1:
        errs.append(f"complete clue set has {res['models']} models (need exactly 1)")
    sim = simulate(p)
    res["steps"], res["waves"] = sim["steps"], sim["waves"]
    if not sim["solved"]:
        errs.append(f"deduction loop ended with status {sim['status']}")
    order = p.get("meta", {}).get("reveal_order")
    if order and order != [t["cell"] for t in sim["trace"]]:
        errs.append("meta.reveal_order differs from the simulated row-major order")
    return res


def main(argv):
    root = Path(__file__).resolve().parent.parent / "puzzles"
    files = [Path(a) for a in argv] or sorted(root.glob("*.json"))
    if not files:
        print("no puzzle files found")
        return 1
    bad = 0
    print(f"{'file':<24}{'models':>7}{'steps':>7}{'waves':>7}  result")
    for f in files:
        r = check_file(f)
        ok = not r["errors"]
        bad += not ok
        print(f"{r['file']:<24}{str(r['models']):>7}{str(r['steps']):>7}{str(r['waves']):>7}  "
              f"{'OK' if ok else 'FAIL: ' + '; '.join(r['errors'])}")
    print(f"\n{len(files) - bad}/{len(files)} puzzles valid")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))