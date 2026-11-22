"""Weekly puzzle ladder (member D).

The real Griductive ramps up through the week: easy Monday, medium midweek,
tricky Thursday/Friday, hard Saturday, evil Sunday. This script builds one
puzzle per weekday with a difficulty that never goes down from T2 to CN:

  * the board never shrinks (3x3 -> 4x4 -> 5x5);
  * inside one board size, the number of deduction waves never decreases
    (more waves = more steps where the solver must re-derive before
    something new becomes provable);
  * fewer face-up cards at the start on the hardest days.

Files are named 00_daily_<n>_<day>_<NxN>.json. The leading "00_" matters:
the GUI server lists puzzles/*.json alphabetically and maps weekday i to the
i-th file, so these 7 must sort before everything else.

  python tools/generate_weekly.py            # writes puzzles/00_daily_*.json
  python tools/generate_weekly.py --check    # only validate the existing ones
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_puzzles import build_puzzle
from reference import count_solutions, simulate

# day, label shown to players, size, generator mode, face-up cards, allowed waves (min, max)
LADDER = [
    ("mon", "easy",   3, "easy",   2, (2, 3)),
    ("tue", "medium", 3, "hard",   1, (6, 8)),
    ("wed", "medium", 4, "medium", 3, (3, 6)),
    ("thu", "tricky", 4, "hard",   2, (11, 14)),
    ("fri", "tricky", 5, "medium", 3, (6, 12)),
    ("sat", "hard",   5, "hard",   3, (16, 20)),
    ("sun", "evil",   5, "hard",   2, (21, 23)),
]
OUT = Path(__file__).resolve().parent.parent / "puzzles"


def build_day(idx, day, label, n, mode, n_init, band, max_seeds=150):
    pid = f"daily_{idx}_{day}"
    for k in range(max_seeds):
        seed = 700 + idx * 100 + k
        try:
            p = build_puzzle(pid, n, mode, seed, (), n_init, max_tries=20)
        except RuntimeError:
            continue
        waves = simulate(p)["waves"]
        if band[0] <= waves <= band[1]:
            p["difficulty"] = label
            p["weekday"] = day
            p["meta"]["mode"] = mode
            p["meta"]["waves"] = waves
            return p
    raise RuntimeError(f"no {n}x{n} puzzle with waves in {band} found for {day}")


def summarize(p):
    sim = simulate(p)
    return {"id": p["id"], "size": p["size"], "level": p["difficulty"], "init": len(p["initial_revealed"]),
            "steps": sim["steps"], "waves": sim["waves"], "unique": count_solutions(p) == 1, "ok": sim["solved"]}


def check_ladder(rows):
    key = [(r["size"], r["waves"]) for r in rows]
    mono = all(a <= b for a, b in zip(key, key[1:]))
    allok = all(r["unique"] and r["ok"] for r in rows)
    print(f"{'day':<5}{'level':<8}{'size':>5}{'init':>6}{'steps':>7}{'waves':>7}  valid")
    for r in rows:
        print(f"{r['id'].split('_')[-1]:<5}{r['level']:<8}{r['size']:>5}{r['init']:>6}{r['steps']:>7}"
              f"{r['waves']:>7}  {'OK' if r['unique'] and r['ok'] else 'FAIL'}")
    print(f"\nmonotone (size, waves) from Mon to Sun: {mono};  all valid: {allok}")
    return mono and allok


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="only check existing 00_daily_*.json files")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    if a.check:
        files = sorted(out.glob("00_daily_*.json"))
        rows = [summarize(json.loads(f.read_text(encoding="utf-8"))) for f in files]
        return 0 if len(rows) == 7 and check_ladder(rows) else 1

    rows = []
    for i, (day, label, n, mode, n_init, band) in enumerate(LADDER, start=1):
        p = build_day(i, day, label, n, mode, n_init, band)
        path = out / f"00_daily_{i}_{day}_{n}x{n}.json"
        path.write_text(json.dumps(p, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"wrote {path.name}")
        rows.append(summarize(p))
    print()
    return 0 if check_ladder(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())