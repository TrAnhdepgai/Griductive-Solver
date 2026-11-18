"""Tests for Part B: DPLL solver, entailment, uniqueness check and logic agent.

Run:  python -m unittest tests.test_sat_agent -v     (or python tests/run_tests.py)
"""
import glob
import itertools
import json
import random
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from src.logic.types import Verdict
from src.sat import HEURISTICS, DPLLSolver, EntailmentChecker, count_models, solve
from src.agent import (SOLVED, STUCK, INCONSISTENT, LocalGameEngine, LogicAgent, PublicState,
                       check_puzzle_uniqueness, check_uniqueness, classify_state, explain,
                       judge_verdict)
from src.agent.interface import ACCEPTED, CONTRADICTED, NOT_PROVABLE, cells_for_size

PUZZLES = sorted(glob.glob(str(ROOT / "puzzles" / "*.json")))


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def brute_sat(clauses, n):
    return any(all(any((l > 0) == bits[abs(l) - 1] for l in c) for c in clauses)
               for bits in itertools.product([False, True], repeat=n))


def satisfies(model, clauses):
    return all(any(model[abs(l)] == (l > 0) for l in c) for c in clauses)


class TestDPLL(unittest.TestCase):
    def test_spec_example(self):
        # Section 3.4: KB = (A | B) & (~A | B) entails B, A unknown.
        kb = [[1, 2], [-1, 2]]
        self.assertTrue(solve(kb).sat)
        self.assertFalse(solve(kb, assumptions=[-2]).sat)
        chk = EntailmentChecker(kb)
        self.assertEqual(chk.classify(2), Verdict.CRIMINAL)
        self.assertEqual(chk.classify(1), Verdict.UNKNOWN)

    def test_trivial_cases(self):
        self.assertTrue(solve([]).sat)
        self.assertFalse(solve([[]]).sat)
        self.assertFalse(solve([[1], [-1]]).sat)
        self.assertTrue(solve([[1, -1]]).sat)            # tautology
        r = solve([[1]], num_vars=4)
        self.assertEqual(sorted(r.assignment), [1, 2, 3, 4])  # complete assignment

    def test_random_vs_bruteforce(self):
        rng = random.Random(7)
        for _ in range(1500):
            n = rng.randint(1, 9)
            cls = [[rng.choice((1, -1)) * rng.randint(1, n) for _ in range(rng.randint(1, 4))]
                   for _ in range(rng.randint(0, 30))]
            expected = brute_sat(cls, n)
            for h in HEURISTICS:
                r = solve(cls, n, heuristic=h)
                self.assertEqual(r.sat, expected, (cls, h))
                if r.sat:
                    self.assertTrue(satisfies(r.assignment, cls))

    def test_pigeonhole_unsat_and_stats(self):
        # 4 pigeons, 3 holes: p(i,j) = 3*i + j + 1
        P, H = 4, 3
        v = lambda i, j: H * i + j + 1
        cls = [[v(i, j) for j in range(H)] for i in range(P)]
        cls += [[-v(i, j), -v(k, j)] for j in range(H) for i in range(P) for k in range(i + 1, P)]
        r = solve(cls)
        self.assertFalse(r.sat)
        self.assertGreater(r.stats.decisions, 0)
        self.assertGreater(r.stats.backtracks, 0)
        self.assertGreater(r.stats.propagations, 0)
        self.assertGreaterEqual(r.stats.runtime_s, 0)

    def test_deterministic(self):
        cls = [[1, 2, 3], [-1, -2], [-2, -3], [2, 4], [-4, -1, 3]]
        a = [DPLLSolver(cls).solve() for _ in range(3)]
        self.assertTrue(all(x.assignment == a[0].assignment for x in a))
        self.assertTrue(all(x.stats.decisions == a[0].stats.decisions for x in a))

    def test_reuse_with_assumptions(self):
        s = DPLLSolver([[1, 2], [-1, 3], [-2, 3]])
        self.assertTrue(s.solve().sat)
        self.assertFalse(s.solve([-3]).sat)
        self.assertTrue(s.solve([1]).sat)
        self.assertEqual(s.total_stats.calls, 3)

    def test_count_models(self):
        mc = count_models([[1, 2]], [1, 2], limit=None)
        self.assertEqual(mc.count, 3)
        self.assertTrue(mc.complete)
        # aux var 3 must not duplicate primary models: (1|2) with 3 free
        mc = count_models([[1, 2], [3, -3]], [1, 2], num_vars=3, limit=None)
        self.assertEqual(mc.count, 3)


class TestEntailmentOnPuzzles(unittest.TestCase):
    """classify_state must match brute-force forced literals on random partial states."""

    def test_against_reference(self):
        from reference import enumerate_models, forced_masks, status_clue
        from schema import all_cells, cell_index
        rng = random.Random(3)
        for path in [p for p in PUZZLES if "3x3" in p or "4x4" in p]:
            pz = load(path)
            n, cells = pz["size"], all_cells(pz["size"])
            for _ in range(4):
                shown = rng.sample(cells, rng.randint(1, len(cells) - 1))
                proved = {c: pz["solution"][c] for c in shown if rng.random() < 0.7}
                state = PublicState(n, cells_for_size(n), proved, {c: pz["clues"][c] for c in shown})
                kb = [status_clue(c, s) for c, s in proved.items()] + [pz["clues"][c] for c in shown]
                crim, inno = forced_masks(enumerate_models(n, kb), n)
                for strategy in ("naive", "pruned"):
                    got = classify_state(state, strategy=strategy).verdicts
                    for c, v in got.items():
                        i = cell_index(c, n)
                        exp = "CRIMINAL" if crim >> i & 1 else "INNOCENT" if inno >> i & 1 else "UNKNOWN"
                        self.assertEqual(v.value, exp, (path, c, strategy))

    def test_inconsistent_state(self):
        clues = {"A1": {"type": "FACT", "cell": "B1", "status": "CRIMINAL"},
                 "C1": {"type": "FACT", "cell": "B1", "status": "INNOCENT"}}
        st = PublicState(3, cells_for_size(3), {}, clues)
        cls = classify_state(st)
        self.assertFalse(cls.consistent)
        self.assertTrue(all(v == Verdict.INCONSISTENT for v in cls.verdicts.values()))

    def test_judge_verdict_codes(self):
        clues = {"A1": {"type": "SAME", "a": "A1", "b": "B1"}}
        st = PublicState(3, cells_for_size(3), {"A1": "CRIMINAL"}, clues)
        self.assertEqual(judge_verdict(st, "B1", "CRIMINAL"), ACCEPTED)
        self.assertEqual(judge_verdict(st, "B1", "INNOCENT"), CONTRADICTED)
        self.assertEqual(judge_verdict(st, "C3", "CRIMINAL"), NOT_PROVABLE)

    def test_explain_is_minimal(self):
        clues = {"A1": {"type": "SAME", "a": "A1", "b": "B1"},
                 "C1": {"type": "FACT", "cell": "C3", "status": "INNOCENT"},
                 "A2": {"type": "AT_MOST", "region": {"kind": "row", "row": 3}, "k": 3}}
        st = PublicState(3, cells_for_size(3), {"A1": "CRIMINAL", "C1": "INNOCENT"}, clues)
        sup_clues, sup_facts = explain(st, "B1", "CRIMINAL")
        self.assertEqual(sup_clues, ["A1"])
        self.assertEqual(sup_facts, ["A1"])


class TestUniqueness(unittest.TestCase):
    def test_all_puzzles_unique(self):
        for path in PUZZLES:
            pz = load(path)
            rep = check_puzzle_uniqueness(pz)
            self.assertTrue(rep.unique, path)
            self.assertEqual(rep.solution, pz["solution"], path)

    def test_ambiguous_and_inconsistent(self):
        rep = check_uniqueness({"A1": {"type": "EXACTLY", "region": {"kind": "row", "row": 1}, "k": 1}}, 3)
        self.assertFalse(rep.unique)
        self.assertEqual(rep.model_count, 2)
        self.assertFalse(rep.exhaustive)
        rep = check_uniqueness({"A1": {"type": "SAME", "a": "A1", "b": "B1"},
                                "B1": {"type": "DIFFERENT", "a": "A1", "b": "B1"}}, 3)
        self.assertEqual(rep.model_count, 0)
        self.assertTrue(rep.exhaustive)


class _SpyEngine:
    """Wraps LocalGameEngine and records every call the agent makes."""

    def __init__(self, inner):
        self.inner, self.calls = inner, []

    def public_state(self):
        self.calls.append("public_state")
        return self.inner.public_state()

    def submit_verdict(self, cell, verdict):
        self.calls.append(("submit", cell, verdict))
        return self.inner.submit_verdict(cell, verdict)


class TestAgent(unittest.TestCase):
    def test_solves_every_puzzle_in_reference_order(self):
        for path in PUZZLES:
            pz = load(path)
            for strategy in ("pruned", "naive"):
                eng = LocalGameEngine(pz)
                res = LogicAgent(eng, strategy=strategy).run()
                self.assertEqual(res.status, SOLVED, path)
                self.assertTrue(eng.is_solved(), path)
                order = [t.cell for t in res.trace if t.cell]
                self.assertEqual(order, pz["meta"]["reveal_order"], (path, strategy))

    def test_waves_match_reference(self):
        from reference import simulate
        for path in PUZZLES[:12]:
            pz = load(path)
            res = LogicAgent(LocalGameEngine(pz)).run()
            self.assertEqual(res.waves, simulate(pz)["waves"], path)

    def test_only_public_interface_and_no_rejections(self):
        spy = _SpyEngine(LocalGameEngine(load(PUZZLES[0])))
        res = LogicAgent(spy).run()
        self.assertEqual(res.status, SOLVED)
        self.assertTrue(all(c == "public_state" or c[0] == "submit" for c in spy.calls))
        self.assertTrue(all(t.engine_status == ACCEPTED for t in res.trace if t.cell))

    def test_trace_contents(self):
        res = LogicAgent(LocalGameEngine(load(PUZZLES[0]))).run()
        t = res.trace[0]
        self.assertEqual(t.step, 1)
        self.assertTrue(t.active_clues)
        self.assertTrue(t.queries)
        self.assertIn(t.verdict, ("CRIMINAL", "INNOCENT"))
        self.assertEqual(t.revealed_clue_id, f"clue@{t.cell}")
        self.assertIsNotNone(t.revealed_clue)
        self.assertEqual(res.sat_stats.calls, sum(len(x.queries) for x in res.trace))

    def test_stuck_without_guessing(self):
        pz = load(PUZZLES[0])
        pz["clues"] = {c: {"type": "AT_MOST", "region": {"kind": "row", "row": 1}, "k": 3}
                       for c in pz["clues"]}
        eng = LocalGameEngine(pz)
        res = LogicAgent(eng).run()
        self.assertEqual(res.status, STUCK)
        self.assertEqual(res.steps, 0)
        self.assertEqual(eng.submissions, 0)

    def test_hint_does_not_change_state(self):
        eng = LocalGameEngine(load(PUZZLES[0]))
        before = eng.public_state()
        h = LogicAgent(eng).hint()
        self.assertIsNotNone(h.cell)
        self.assertTrue(h.supporting_clues)
        self.assertEqual(eng.public_state().proved, before.proved)
        self.assertEqual(judge_verdict(before, h.cell, h.verdict), ACCEPTED)

    def test_extension_clues_with_aux_vars(self):
        # PARITY over 3+ cells makes the encoder allocate auxiliary variables.
        pz = load(PUZZLES[0])
        sol = pz["solution"]
        row1 = [c for c in sol if c.endswith("1")]
        odd = sum(sol[c] == "CRIMINAL" for c in row1) % 2
        owner = pz["initial_revealed"][0]
        pz["clues"][owner] = {"type": "PARITY", "region": {"kind": "row", "row": 1},
                              "parity": "ODD" if odd else "EVEN"}
        st = LocalGameEngine(pz).public_state()
        cls = classify_state(st)
        self.assertGreater(cls.kb.aux_vars, 0)
        self.assertTrue(cls.consistent)


if __name__ == "__main__":
    unittest.main()
