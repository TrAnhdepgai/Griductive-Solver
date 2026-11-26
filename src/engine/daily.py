"""Daily puzzles: a brand-new puzzle for every calendar date, kept for 6 months.

* Each date gets its own puzzle. The generator seed is derived from the date
  (2026-11-26 -> 20261126), so two different dates never share a seed and the
  same date always rebuilds the same puzzle on any machine.
* Difficulty follows the weekday ladder of ``tools/generate_weekly.py``
  (easy Monday ... evil Sunday), like the original game.
* The playable window is a fixed ``WINDOW_DAYS`` = 183 days (about 6 months)
  ending today. Each new day adds exactly one puzzle (today) and drops exactly
  one (the oldest); every other date keeps its puzzle and its place. A
  calendar "6 months ago" would not do that: from 28 Feb to 1 Mar it would
  drop four days at once. Old files are deleted by :meth:`DailyStore.prune`;
  nothing is ever recycled.
* A generated puzzle is written once to ``puzzles/daily/<YYYY-MM-DD>.json`` and
  never rewritten, so the same date always shows the same puzzle, even if the
  generator code changes later. The cache is outside ``puzzles/*.json`` so the
  benchmark set is not affected.
"""
from __future__ import annotations

import json
import os
import sys
import threading
from datetime import date, timedelta
from pathlib import Path
from typing import Callable, Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools"
DAILY_DIR = ROOT / "puzzles" / "daily"
RETENTION_MONTHS = 6    # shown to players; the exact window is WINDOW_DAYS
WINDOW_DAYS = 183       # today + the 182 days before it
MAX_SEEDS = 25          # seeds tried per date to land inside the weekday's wave band (then keep the closest)


def _tools():
    """Import member D's generator lazily (it needs numpy and tools/ on sys.path)."""
    if str(TOOLS) not in sys.path:
        sys.path.insert(0, str(TOOLS))
    from generate_puzzles import build_puzzle
    from generate_weekly import LADDER
    from reference import simulate
    return LADDER, build_puzzle, simulate


def earliest_date(today: date) -> date:
    """First playable date: the window always holds exactly WINDOW_DAYS dates."""
    return today - timedelta(days=WINDOW_DAYS - 1)


def puzzle_id(d: date) -> str:
    return f"daily_{d.isoformat()}"


def date_seed(d: date) -> int:
    return d.year * 10000 + d.month * 100 + d.day


def generate_for_date(d: date, max_seeds: int = MAX_SEEDS) -> dict:
    """Build the puzzle of date `d` (deterministic for a given date)."""
    ladder, build_puzzle, simulate = _tools()
    day, label, n, mode, n_init, (lo, hi) = ladder[d.weekday()]   # Monday = 0
    best: Optional[Tuple[int, dict, int]] = None   # (distance to band, puzzle, waves)
    for k in range(max_seeds):
        seed = date_seed(d) * 1000 + k
        try:
            p = build_puzzle(puzzle_id(d), n, mode, seed, (), n_init, max_tries=20)
        except RuntimeError:
            continue
        waves = simulate(p)["waves"]
        dist = 0 if lo <= waves <= hi else min(abs(waves - lo), abs(waves - hi))
        if best is None or dist < best[0]:
            best = (dist, p, waves)
        if dist == 0:
            break
    if best is None:
        raise RuntimeError(f"could not generate a {n}x{n} puzzle for {d}")
    _, p, waves = best
    p["difficulty"] = label
    p["weekday"] = day
    p["date"] = d.isoformat()
    p["meta"].update(mode=mode, waves=waves, date=d.isoformat(), wave_band=[lo, hi])
    return p


class DailyStore:
    """Cache of generated daily puzzles with a rolling 6-month window."""

    def __init__(self, directory: Path = DAILY_DIR, today: Callable[[], date] = date.today,
                 generator: Callable[[date], dict] = generate_for_date):
        self.dir = Path(directory)
        self.today = today
        self.generator = generator
        self._locks: Dict[str, threading.Lock] = {}
        self._guard = threading.Lock()

    # ------------------------------------------------------------- window
    def window(self) -> Tuple[date, date]:
        t = self.today()
        return earliest_date(t), t

    def in_window(self, d: date) -> bool:
        lo, hi = self.window()
        return lo <= d <= hi

    def path(self, d: date) -> Path:
        return self.dir / f"{d.isoformat()}.json"

    def is_ready(self, d: date) -> bool:
        return self.path(d).exists()

    # ------------------------------------------------------------- access
    def get(self, d: date) -> Path:
        """Path of the puzzle file for `d`, generating it on first use."""
        if not self.in_window(d):
            lo, hi = self.window()
            raise ValueError(f"{d} is outside the playable range {lo} .. {hi}")
        path = self.path(d)
        if path.exists():
            return path
        with self._guard:
            lock = self._locks.setdefault(d.isoformat(), threading.Lock())
        with lock:                       # two requests for the same new date generate it once
            if not path.exists():
                self.save(d, self.generator(d))
        return path

    def save(self, d: date, puzzle: dict) -> Path:
        """Write a generated puzzle once. An existing file is never overwritten."""
        path = self.path(d)
        if path.exists():
            return path
        self.dir.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(f"{path.stem}.{os.getpid()}.{threading.get_ident()}.tmp")
        tmp.write_text(json.dumps(puzzle, indent=2, ensure_ascii=False), encoding="utf-8")
        if path.exists():                # someone else finished first: keep their file
            tmp.unlink(missing_ok=True)
        else:
            os.replace(tmp, path)        # atomic: readers never see a half-written file
        return path

    def missing(self) -> List[date]:
        """Dates of the window without a puzzle yet, newest first."""
        lo, hi = self.window()
        return [hi - timedelta(days=i) for i in range((hi - lo).days + 1)
                if not self.is_ready(hi - timedelta(days=i))]

    def build_missing(self, jobs: int = 1, on_done: Optional[Callable[[date, float], None]] = None) -> int:
        """Generate every missing date of the window, newest first, on `jobs` processes."""
        import time
        todo = self.missing()
        if not todo:
            return 0
        if jobs <= 1 or self.generator is not generate_for_date:
            for d in todo:
                t0 = time.perf_counter()
                self.get(d)
                if on_done:
                    on_done(d, time.perf_counter() - t0)
            return len(todo)
        from concurrent.futures import ProcessPoolExecutor, as_completed
        with ProcessPoolExecutor(max_workers=jobs) as pool:
            started = time.perf_counter()
            futures = {pool.submit(generate_for_date, d): d for d in todo}   # submitted newest first
            for fut in as_completed(futures):
                d = futures[fut]
                if self.in_window(d):     # the day may have rolled over meanwhile
                    self.save(d, fut.result())
                if on_done:
                    on_done(d, time.perf_counter() - started)
        return len(todo)

    def prune(self) -> List[Path]:
        """Delete cached puzzles older than the window. Returns the removed files."""
        lo, _ = self.window()
        removed = []
        for f in self.dir.glob("*.json"):
            try:
                d = date.fromisoformat(f.stem)
            except ValueError:
                continue
            if d < lo:
                f.unlink(missing_ok=True)
                removed.append(f)
        return removed

    def ready_dates(self) -> List[str]:
        return sorted(f.stem for f in self.dir.glob("*.json"))

    def warm_up(self, jobs: Optional[int] = None) -> threading.Thread:
        """Background: drop puzzles that left the window, build today's puzzle first,
        then fill every other missing date of the window (newest first) in parallel.
        With a full cache this only builds the one new puzzle of the day.
        A date requested meanwhile is still generated at once by the request itself."""
        jobs = jobs or max(1, (os.cpu_count() or 2) // 2)

        def job():
            try:
                removed = self.prune()
                new_today = not self.is_ready(self.today())
                self.get(self.today())
                n = self.build_missing(jobs) + new_today
                if removed or n:
                    print(f"[daily] window ready: +{n} new, -{len(removed)} old", flush=True)
            except Exception as e:  # noqa: BLE001 - never kill the server for this
                print(f"[daily] warm-up failed: {e}", flush=True)
        th = threading.Thread(target=job, name="daily-warmup", daemon=True)
        th.start()
        return th


def main(argv=None) -> int:
    """Build every missing puzzle of the 183-day window in parallel, then exit.

    python -m src.engine.daily              # all CPU cores
    python -m src.engine.daily --jobs 4     # limit the number of processes
    """
    import argparse
    import time

    ap = argparse.ArgumentParser(description=main.__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 1, help="worker processes (default: all cores)")
    a = ap.parse_args(argv)

    store = DailyStore()
    for f in store.prune():
        print(f"removed {f.name} (left the {WINDOW_DAYS}-day window)")
    lo, hi = store.window()
    todo = len(store.missing())
    print(f"window {lo} .. {hi}: {WINDOW_DAYS - todo} cached, {todo} to build on {a.jobs} process(es)", flush=True)
    t0, done = time.perf_counter(), [0]

    def progress(d, _elapsed):
        done[0] += 1
        print(f"  [{done[0]:>3}/{todo}] {d} ({d.strftime('%a')})  {time.perf_counter() - t0:6.1f}s", flush=True)

    store.build_missing(a.jobs, progress)
    print(f"done in {time.perf_counter() - t0:.1f}s: {len(store.ready_dates())} puzzle(s) in {store.dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
