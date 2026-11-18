"""DPLL SAT solver (Part B, section 4.3).

Davis-Putnam-Logemann-Loveland procedure written from scratch:

1. Unit propagation      -- two-watched-literal scheme (`_propagate`).
2. Conflict detection    -- a clause whose literals are all false stops propagation.
3. Deterministic choice  -- static variable order ("first" = smallest index,
                            "jw" = Jeroslow-Wang score, ties broken by index).
4. Recursive branching   -- `_search` tries one polarity, undoes the trail and
   and backtracking         tries the other one (chronological backtracking).
5. Result                -- SAT with a COMPLETE assignment of 1..num_vars, or UNSAT.
6. Statistics            -- decisions, propagations, backtracks, conflicts, runtime.

Clauses use DIMACS integers: variable v > 0, literal +v (True) / -v (False).

The solver is built once for a clause set and can be queried many times with
different *assumptions* (temporary unit literals). This is exactly what the
entailment test needs: KB /\ ~C_i and KB /\ C_i share the same clause set.
"""
from __future__ import annotations

import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

HEURISTICS = ("first", "jw")


@dataclass
class SolverStats:
    """Counters of one SAT call, or accumulated over many calls."""

    calls: int = 0
    decisions: int = 0
    propagations: int = 0
    backtracks: int = 0
    conflicts: int = 0
    runtime_s: float = 0.0

    def add(self, other: "SolverStats") -> None:
        self.calls += other.calls
        self.decisions += other.decisions
        self.propagations += other.propagations
        self.backtracks += other.backtracks
        self.conflicts += other.conflicts
        self.runtime_s += other.runtime_s

    def copy(self) -> "SolverStats":
        return SolverStats(**asdict(self))

    def as_dict(self) -> Dict[str, float]:
        return asdict(self)


@dataclass
class SATResult:
    """Outcome of one SAT call."""

    sat: bool
    assignment: Optional[Dict[int, bool]]  # complete model (1..num_vars) when sat, else None
    stats: SolverStats = field(default_factory=SolverStats)

    @property
    def status(self) -> str:
        return "SAT" if self.sat else "UNSAT"

    def value(self, var: int) -> Optional[bool]:
        return None if self.assignment is None else self.assignment.get(var)


class DPLLSolver:
    """Reusable DPLL solver for one fixed CNF formula.

    >>> s = DPLLSolver([[1, 2], [-1, 2]])
    >>> s.solve().sat, s.solve(assumptions=[-2]).sat
    (True, False)
    """

    def __init__(
        self,
        clauses: Iterable[Sequence[int]],
        num_vars: Optional[int] = None,
        heuristic: str = "first",
    ):
        if heuristic not in HEURISTICS:
            raise ValueError(f"unknown heuristic {heuristic!r}; choose one of {HEURISTICS}")
        self.heuristic = heuristic

        # ---- normalise input: drop duplicate literals and tautologies -------
        self.has_empty_clause = False
        self.unit_literals: List[int] = []      # clauses of length 1
        self.clauses: List[List[int]] = []      # clauses of length >= 2 (watched)
        max_var = 0
        for raw in clauses:
            lits: List[int] = []
            seen = set()
            tautology = False
            for lit in raw:
                lit = int(lit)
                if lit == 0:
                    raise ValueError("literal 0 is not allowed (DIMACS terminator)")
                if -lit in seen:
                    tautology = True
                    break
                if lit not in seen:
                    seen.add(lit)
                    lits.append(lit)
                max_var = max(max_var, abs(lit))
            if tautology:
                continue
            if not lits:
                self.has_empty_clause = True
            elif len(lits) == 1:
                self.unit_literals.append(lits[0])
            else:
                self.clauses.append(lits)

        self.num_vars = max(num_vars or 0, max_var)
        n = self.num_vars

        # ---- watch lists: literal index 2v (positive) / 2v+1 (negative) ----
        self._watches: List[List[int]] = [[] for _ in range(2 * n + 2)]
        for ci, c in enumerate(self.clauses):
            self._watches[self._widx(c[0])].append(ci)
            self._watches[self._widx(c[1])].append(ci)

        # ---- deterministic static branching order ---------------------------
        occurring = sorted({abs(l) for c in self.clauses for l in c} | {abs(l) for l in self.unit_literals})
        self._phase = [True] * (n + 1)          # polarity tried first
        if heuristic == "first":
            self._order = occurring
        else:  # Jeroslow-Wang: J(l) = sum over clauses containing l of 2^-|c|
            score = [0.0] * (2 * n + 2)
            for c in self.clauses:
                w = 2.0 ** -len(c)
                for lit in c:
                    score[self._widx(lit)] += w
            self._order = sorted(occurring, key=lambda v: (-(score[2 * v] + score[2 * v + 1]), v))
            for v in occurring:
                self._phase[v] = score[2 * v] >= score[2 * v + 1]

        # ---- search state (reset on every call) -----------------------------
        self._val = [0] * (n + 1)               # 0 unassigned, 1 True, -1 False
        self._trail: List[int] = []
        self._qhead = 0
        self._stats = SolverStats()
        self.total_stats = SolverStats()        # accumulated over all calls on this instance

    # ------------------------------------------------------------------ utils
    @staticmethod
    def _widx(lit: int) -> int:
        return 2 * lit if lit > 0 else -2 * lit + 1

    def _lit_value(self, lit: int) -> int:
        v = self._val[lit if lit > 0 else -lit]
        return v if lit > 0 else -v

    def _assign(self, lit: int) -> None:
        self._val[lit if lit > 0 else -lit] = 1 if lit > 0 else -1
        self._trail.append(lit)

    def _undo(self, mark: int) -> None:
        """Unassign everything on the trail above position `mark`."""
        trail, val = self._trail, self._val
        while len(trail) > mark:
            lit = trail.pop()
            val[lit if lit > 0 else -lit] = 0
        self._qhead = mark

    # ------------------------------------------------------- unit propagation
    def _propagate(self) -> bool:
        """Two-watched-literal unit propagation. Returns False on conflict."""
        trail, clauses, watches, stats = self._trail, self.clauses, self._watches, self._stats
        while self._qhead < len(trail):
            false_lit = -trail[self._qhead]
            self._qhead += 1
            wl = watches[self._widx(false_lit)]
            i = 0
            while i < len(wl):
                ci = wl[i]
                c = clauses[ci]
                if c[0] == false_lit:            # keep the falsified watch in slot 1
                    c[0], c[1] = c[1], c[0]
                other = c[0]
                if self._lit_value(other) == 1:  # clause already satisfied
                    i += 1
                    continue
                moved = False
                for k in range(2, len(c)):       # look for a replacement watch
                    if self._lit_value(c[k]) != -1:
                        c[1], c[k] = c[k], c[1]
                        watches[self._widx(c[1])].append(ci)
                        wl[i] = wl[-1]
                        wl.pop()
                        moved = True
                        break
                if moved:
                    continue
                if self._lit_value(other) == -1:  # every literal false -> conflict
                    stats.conflicts += 1
                    return False
                self._assign(other)              # clause is unit -> forced literal
                stats.propagations += 1
                i += 1
        return True

    # ---------------------------------------------------- branching / search
    def _pick_branch_var(self) -> Optional[int]:
        val = self._val
        for v in self._order:
            if val[v] == 0:
                return v
        return None

    def _search(self) -> bool:
        if not self._propagate():
            return False
        var = self._pick_branch_var()
        if var is None:                          # everything assigned, no conflict -> model
            return True
        first = var if self._phase[var] else -var
        for lit in (first, -first):
            mark = len(self._trail)
            self._stats.decisions += 1
            self._assign(lit)
            if self._search():
                return True
            self._undo(mark)                     # chronological backtracking
            self._stats.backtracks += 1
        return False

    # ---------------------------------------------------------------- public
    def solve(self, assumptions: Iterable[int] = ()) -> SATResult:
        """Decide satisfiability of  formula /\\ assumptions.

        Assumptions are temporary unit literals; they never change the stored
        formula, so the same instance can answer many entailment queries.
        """
        t0 = time.perf_counter()
        self._stats = SolverStats(calls=1)
        self._val = [0] * (self.num_vars + 1)
        self._trail = []
        self._qhead = 0

        sat = self._solve_inner(list(assumptions))

        assignment = None
        if sat:
            # Variables that occur in no clause are unconstrained: set them False
            # so that the returned model is complete over 1..num_vars.
            assignment = {v: self._val[v] == 1 for v in range(1, self.num_vars + 1)}
        self._stats.runtime_s = time.perf_counter() - t0
        stats = self._stats
        self.total_stats.add(stats)
        return SATResult(sat=sat, assignment=assignment, stats=stats)

    def _solve_inner(self, assumptions: List[int]) -> bool:
        if self.has_empty_clause:
            self._stats.conflicts += 1
            return False
        # Level 0: unit clauses of the formula, then the assumptions.
        for lit in self.unit_literals:
            v = self._lit_value(lit)
            if v == -1:
                self._stats.conflicts += 1
                return False
            if v == 0:
                self._assign(lit)
                self._stats.propagations += 1
        for lit in assumptions:
            if abs(lit) > self.num_vars or lit == 0:
                raise ValueError(f"assumption {lit} is outside 1..{self.num_vars}")
            v = self._lit_value(lit)
            if v == -1:
                self._stats.conflicts += 1
                return False
            if v == 0:
                self._assign(lit)
        # Recursion depth <= number of variables; make sure Python allows it.
        need = self.num_vars + 200
        if sys.getrecursionlimit() < need:
            sys.setrecursionlimit(need)
        return self._search()


def solve(
    clauses: Iterable[Sequence[int]],
    num_vars: Optional[int] = None,
    assumptions: Iterable[int] = (),
    heuristic: str = "first",
) -> SATResult:
    """One-shot convenience wrapper around :class:`DPLLSolver`."""
    return DPLLSolver(clauses, num_vars=num_vars, heuristic=heuristic).solve(assumptions)
