"""Experiment harness (member D, section 4.5).

Runs every puzzle in puzzles/ in a separate process with a timeout, so failures
and timeouts are recorded instead of silently dropped.

  python tools/benchmark.py --backend reference            # works today (brute force)
  python tools/benchmark.py --backend team --timeout 60 --repeats 3

Outputs in experiments/results/: benchmark_<backend>.{csv,json,md,tex}
"""
from __future__ import annotations

import argparse
import csv
import json
import multiprocessing as mp
import queue
import statistics
import sys
import time
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

COLUMNS = ["puzzle", "size", "difficulty", "status", "primary_vars", "aux_vars", "clauses", "sat_calls",
           "decisions", "propagations", "backtracks", "steps", "waves", "runtime_s", "error"]
TABLE_COLS = ["puzzle", "status", "primary_vars", "aux_vars", "clauses", "sat_calls", "decisions",
              "propagations", "backtracks", "steps", "waves", "runtime_s"]
HEADERS = {"puzzle": "Puzzle", "status": "Status", "primary_vars": "Prim.", "aux_vars": "Aux.",
           "clauses": "Clauses", "sat_calls": "SAT calls", "decisions": "Dec.", "propagations": "Prop.",
           "backtracks": "BT", "steps": "Steps", "waves": "Waves", "runtime_s": "Time (s)"}


def _worker(backend: str, path: str, heuristic: str, strategy: str, q) -> None:
    try:
        sys.path.insert(0, str(TOOLS))
        import adapter
        if backend == "reference":
            res = adapter.run_reference(path)
        else:
            res = adapter.run_team(path, heuristic=heuristic, strategy=strategy)
        q.put(("ok", res))
    except BaseException as e:  # noqa: BLE001 - record any failure
        q.put(("error", f"{type(e).__name__}: {e}"))


def run_one(backend: str, path: str, timeout: float, heuristic: str = "first", strategy: str = "pruned"):
    q = mp.Queue()
    p = mp.Process(target=_worker, args=(backend, path, heuristic, strategy, q))
    t0 = time.perf_counter()
    p.start()
    deadline = t0 + timeout
    while True:
        try:
            kind, payload = q.get(timeout=0.2)
            break
        except queue.Empty:
            if not p.is_alive():
                try:
                    kind, payload = q.get(timeout=0.5)
                except queue.Empty:
                    kind, payload = "error", "worker process died"
                break
            if time.perf_counter() > deadline:
                kind, payload = "timeout", None
                break
    if p.is_alive():
        p.terminate()
    p.join()
    return kind, payload, time.perf_counter() - t0


def fmt(v) -> str:
    if v is None or v == "":
        return "--"
    if isinstance(v, float):
        return f"{v:.4f}"
    return str(v)


def benchmark(backend: str, files: list[Path], timeout: float, repeats: int,
              heuristic: str = "first", strategy: str = "pruned") -> list[dict]:
    from schema import load_puzzle
    rows = []
    for f in files:
        meta = load_puzzle(f)
        row = {"puzzle": meta["id"], "size": meta["size"], "difficulty": meta.get("difficulty", ""),
               "status": "", "error": ""}
        times, last = [], None
        for _ in range(repeats):
            kind, payload, wall = run_one(backend, str(f), timeout, heuristic=heuristic, strategy=strategy)
            if kind == "timeout":
                row["status"] = "TIMEOUT"
                break
            if kind == "error":
                row["status"], row["error"] = "ERROR", payload
                break
            last = payload
            times.append(payload.get("runtime_s") if payload.get("runtime_s") is not None else wall)
            row["status"] = "OK" if payload.get("solved") else "FAIL"
            if row["status"] == "FAIL":
                break
        if last:
            row.update({k: last.get(k) for k in COLUMNS if k in last})
        if times and row["status"] == "OK":
            row["runtime_s"] = statistics.median(times)
        rows.append(row)
        print(f"{row['puzzle']:<22}{row['status']:<9}{fmt(row.get('runtime_s')):>10}  {row['error']}")
    return rows


def write_outputs(rows: list[dict], outdir: Path, backend: str) -> None:
    outdir.mkdir(parents=True, exist_ok=True)
    base = outdir / f"benchmark_{backend}"
    with open(f"{base}.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)
    Path(f"{base}.json").write_text(json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8")
    md = ["| " + " | ".join(HEADERS[c] for c in TABLE_COLS) + " |",
          "|" + "|".join("---" for _ in TABLE_COLS) + "|"]
    md += ["| " + " | ".join(fmt(r.get(c)) for c in TABLE_COLS) + " |" for r in rows]
    Path(f"{base}.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    esc = lambda s: s.replace("_", r"\_")  # noqa: E731
    tex = [r"\begin{tabular}{l l " + "r " * (len(TABLE_COLS) - 2) + "}", r"\hline",
           " & ".join(HEADERS[c] for c in TABLE_COLS) + r" \\", r"\hline"]
    tex += [" & ".join(esc(fmt(r.get(c))) for c in TABLE_COLS) + r" \\" for r in rows]
    tex += [r"\hline", r"\end{tabular}"]
    Path(f"{base}.tex").write_text("\n".join(tex) + "\n", encoding="utf-8")
    print(f"\nwrote {base}.csv / .json / .md / .tex")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backend", choices=("reference", "team"), default="reference")
    ap.add_argument("--heuristic", choices=("first", "jw"), default="first", help="DPLL branching heuristic (team only)")
    ap.add_argument("--strategy", choices=("pruned", "naive"), default="pruned", help="entailment strategy (team only)")
    ap.add_argument("--tag", default="", help="optional output filename tag instead of backend name")
    ap.add_argument("--puzzles", default=str(ROOT / "puzzles"))
    ap.add_argument("--timeout", type=float, default=60.0, help="seconds per puzzle run")
    ap.add_argument("--repeats", type=int, default=1, help="runs per puzzle; median runtime is reported")
    ap.add_argument("--out", default=str(ROOT / "experiments" / "results"))
    ap.add_argument("--only", default="", help="substring filter on file names, e.g. 4x4")
    a = ap.parse_args()
    files = sorted(p for p in Path(a.puzzles).glob("*.json") if a.only in p.name)
    if not files:
        print("no puzzles found")
        return 1
    rows = benchmark(a.backend, files, a.timeout, a.repeats, heuristic=a.heuristic, strategy=a.strategy)
    write_outputs(rows, Path(a.out), a.tag or a.backend)
    return 0 if all(r["status"] == "OK" for r in rows) else 2


if __name__ == "__main__":
    sys.exit(main())