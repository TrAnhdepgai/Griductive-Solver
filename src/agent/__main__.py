"""Command line: run the logic agent on puzzle files and print the deduction trace.

    python -m src.agent puzzles/3x3_easy_01.json            # trace + summary
    python -m src.agent puzzles/*.json --summary             # one line per puzzle
    python -m src.agent puzzles/4x4_hard_01.json --queries   # also list every SAT query
    python -m src.agent puzzles/4x4_hard_01.json --json out.json --heuristic jw --strategy naive
"""
from __future__ import annotations

import argparse
import glob
import json
import sys

from src.sat import HEURISTICS

from .agent import LogicAgent, format_trace
from .local_engine import LocalGameEngine
from .uniqueness import check_puzzle_uniqueness


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m src.agent", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("puzzles", nargs="+", help="puzzle JSON files (globs allowed)")
    ap.add_argument("--heuristic", choices=HEURISTICS, default="first")
    ap.add_argument("--strategy", choices=("pruned", "naive"), default="pruned")
    ap.add_argument("--queries", action="store_true", help="print every SAT query")
    ap.add_argument("--summary", action="store_true", help="one line per puzzle, no trace")
    ap.add_argument("--json", help="write the full result(s) as JSON to this file")
    args = ap.parse_args(argv)

    paths = [p for pat in args.puzzles for p in (sorted(glob.glob(pat)) or [pat])]
    dump, failures = [], 0
    for path in paths:
        engine = LocalGameEngine.load(path)
        uniq = check_puzzle_uniqueness(engine.full_puzzle)    # validation only, not used by the agent
        res = LogicAgent(engine, heuristic=args.heuristic, strategy=args.strategy).run()
        ok = res.solved and engine.is_solved()
        failures += not ok
        s = res.sat_stats
        line = (f"{engine.puzzle_id or path:<16} {res.status:<12} uniq={uniq.summary().split()[0]:<9} "
                f"steps={res.steps:<3} waves={res.waves:<3} vars={res.max_kb_stats['primary_vars']}"
                f"+{res.max_kb_stats['aux_vars']} clauses={res.max_kb_stats['clauses']:<5} "
                f"sat={s.calls:<4} dec={s.decisions:<5} prop={s.propagations:<6} bt={s.backtracks:<5} "
                f"t={res.runtime_s:.3f}s")
        if not args.summary:
            print(f"=== {path}  (uniqueness: {uniq.summary()})")
            print(format_trace(res, show_queries=args.queries))
            print()
        else:
            print(line)
        dump.append({"puzzle": path, "uniqueness": uniq.summary(), **res.as_dict()})
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(dump, f, indent=2, default=str)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
