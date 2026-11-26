"""Tests for the daily puzzle store (src/engine/daily.py).

Only 3x3/4x4 weekdays (Mon-Thu) are generated for real; 5x5 days take seconds each.
"""
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agent import LocalGameEngine, LogicAgent, check_puzzle_uniqueness
from src.engine.daily import WINDOW_DAYS, DailyStore, earliest_date, generate_for_date

TODAY = date(2026, 11, 26)          # a Thursday
FIRST = date(2026, 5, 28)           # TODAY - 182 days
MON, TUE, WED, THU = (date(2026, 11, 23) + timedelta(days=i) for i in range(4))


def fake_store(tmp, today):
    return DailyStore(Path(tmp), today=lambda: today[0], generator=lambda d: {"id": d.isoformat()})


class TestWindow(unittest.TestCase):
    def test_window_is_fixed_size(self):
        self.assertEqual(earliest_date(TODAY), FIRST)
        d = date(2026, 1, 1)
        for _ in range(800):                              # every day of two years, month ends included
            self.assertEqual((d - earliest_date(d)).days + 1, WINDOW_DAYS)
            d += timedelta(days=1)

    def test_next_day_drops_only_the_oldest(self):
        """Opening the site on day N+1 shows day N's set minus its oldest date plus the new day."""
        with tempfile.TemporaryDirectory() as tmp:
            today = [date(2027, 2, 27)]
            store = fake_store(tmp, today)
            store.build_missing()
            for _ in range(4):                            # 27 Feb -> 3 Mar crosses a short month
                before = store.ready_dates()
                old = {f: store.path(date.fromisoformat(f)).read_text() for f in before}
                today[0] += timedelta(days=1)
                store.prune()
                store.build_missing()
                after = store.ready_dates()
                self.assertEqual(len(after), WINDOW_DAYS)
                self.assertEqual(after[:-1], before[1:])                 # same order, oldest gone
                self.assertEqual(after[-1], today[0].isoformat())        # one new day
                for f in after[:-1]:                                     # untouched content
                    self.assertEqual(store.path(date.fromisoformat(f)).read_text(), old[f])

    def test_same_day_reopen_changes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fake_store(tmp, [TODAY])
            self.assertEqual(store.build_missing(), WINDOW_DAYS)
            self.assertEqual(store.build_missing(), 0)
            self.assertEqual(store.prune(), [])

    def test_out_of_window_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            store = fake_store(tmp, [TODAY])
            with self.assertRaises(ValueError):
                store.get(TODAY + timedelta(days=1))          # future
            with self.assertRaises(ValueError):
                store.get(FIRST - timedelta(days=1))          # left the window
            store.get(FIRST)                                  # first day of the window is fine

    def test_prune_deletes_only_old_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            for name in ("2026-05-27", "2026-05-28", "2026-11-26", "notes"):
                (d / f"{name}.json").write_text("{}")
            store = DailyStore(d, today=lambda: TODAY)
            removed = [f.name for f in store.prune()]
            self.assertEqual(removed, ["2026-05-27.json"])
            self.assertEqual(store.ready_dates(), ["2026-05-28", "2026-11-26", "notes"])

    def test_generates_once_and_caches(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            store = DailyStore(Path(tmp), today=lambda: TODAY,
                               generator=lambda d: calls.append(d) or {"id": d.isoformat()})
            p1, p2 = store.get(TODAY), store.get(TODAY)
            self.assertEqual(p1, p2)
            self.assertEqual(calls, [TODAY])


class TestGeneratedPuzzles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.puzzles = {d: generate_for_date(d) for d in (MON, TUE, WED, THU)}

    def test_new_puzzle_every_day(self):
        sols = [json.dumps(p["solution"], sort_keys=True) + json.dumps(p["clues"], sort_keys=True)
                for p in self.puzzles.values()]
        self.assertEqual(len(set(sols)), len(sols))
        # a week later, the same weekday gets a different puzzle (no recycling)
        later = generate_for_date(MON + timedelta(days=7))
        self.assertNotEqual(later["clues"], self.puzzles[MON]["clues"])

    def test_same_date_is_deterministic(self):
        self.assertEqual(generate_for_date(MON)["clues"], self.puzzles[MON]["clues"])

    def test_weekday_ladder_and_metadata(self):
        self.assertEqual([self.puzzles[d]["size"] for d in (MON, TUE, WED, THU)], [3, 3, 4, 4])
        for d, p in self.puzzles.items():
            self.assertEqual(p["date"], d.isoformat())
            self.assertEqual(p["id"], f"daily_{d.isoformat()}")

    def test_unique_and_solvable_without_guessing(self):
        for d, p in self.puzzles.items():
            self.assertTrue(check_puzzle_uniqueness(p).unique, d)
            engine = LocalGameEngine(p)
            self.assertTrue(LogicAgent(engine).run().solved, d)
            self.assertTrue(engine.is_solved(), d)


if __name__ == "__main__":
    unittest.main()
