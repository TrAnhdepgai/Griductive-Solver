"""Entailment classification and model counting on top of DPLL (Part B).

Section 3.4 of the project statement:

    KB |=  C_i   <=>   KB /\\ ~C_i  is UNSAT      -> CRIMINAL
    KB |= ~C_i   <=>   KB /\\  C_i  is UNSAT      -> INNOCENT
    both satisfiable                              -> UNKNOWN
    KB itself unsatisfiable                       -> INCONSISTENT

Every SAT call is logged as a :class:`SATQuery` so the agent can put the exact
queries into its deduction trace.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence

from src.logic.types import Verdict

from .dpll import DPLLSolver, SATResult, SolverStats

Formatter = Callable[[int], str]


@dataclass
class SATQuery:
    """One logged SAT call: the formula asked and the answer."""

    label: str                  # e.g. "KB_3 & ~C[B2]"
    assumptions: List[int]
    result: str                 # "SAT" / "UNSAT"
    decisions: int
    propagations: int
    backtracks: int
    runtime_s: float

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def _default_fmt(lit: int) -> str:
    return f"{'~' if lit < 0 else ''}x{abs(lit)}"


class EntailmentChecker:
    """Answers entailment questions about one fixed knowledge base.

    The underlying DPLL instance is built once and reused for every query
    (queries only differ by their assumption literals).
    """

    def __init__(
        self,
        clauses: Iterable[Sequence[int]],
        num_vars: Optional[int] = None,
        heuristic: str = "first",
        kb_name: str = "KB",
        fmt_literal: Formatter = _default_fmt,
    ):
        self.solver = DPLLSolver(clauses, num_vars=num_vars, heuristic=heuristic)
        self.kb_name = kb_name
        self.fmt = fmt_literal
        self.queries: List[SATQuery] = []
        self._consistency: Optional[SATResult] = None

    @property
    def stats(self) -> SolverStats:
        """Statistics accumulated over every query made through this checker."""
        return self.solver.total_stats

    # ------------------------------------------------------------- queries
    def query(self, assumptions: Sequence[int] = ()) -> SATResult:
        res = self.solver.solve(assumptions)
        label = self.kb_name + "".join(f" & {self.fmt(l)}" for l in assumptions)
        s = res.stats
        self.queries.append(SATQuery(label, list(assumptions), res.status, s.decisions,
                                     s.propagations, s.backtracks, s.runtime_s))
        return res

    def consistency(self) -> SATResult:
        """SAT call on KB alone (cached)."""
        if self._consistency is None:
            self._consistency = self.query(())
        return self._consistency

    def is_consistent(self) -> bool:
        return self.consistency().sat

    def entails(self, lit: int) -> bool:
        """KB |= lit  <=>  KB /\\ ~lit is UNSAT."""
        return not self.query([-lit]).sat

    # ------------------------------------------------------ classification
    def classify(self, var: int) -> Verdict:
        """Textbook classification of one primary variable: two SAT calls."""
        if not self.is_consistent():
            return Verdict.INCONSISTENT
        criminal = not self.query([-var]).sat     # KB & ~C_i UNSAT
        innocent = not self.query([var]).sat      # KB & C_i  UNSAT
        if criminal and innocent:                 # cannot happen when KB is SAT
            return Verdict.INCONSISTENT
        if criminal:
            return Verdict.CRIMINAL
        if innocent:
            return Verdict.INNOCENT
        return Verdict.UNKNOWN

    def classify_many(self, variables: Sequence[int], strategy: str = "pruned") -> Dict[int, Verdict]:
        """Classify several variables.

        strategy="naive"  -- two SAT calls per variable (exactly section 3.4).
        strategy="pruned" -- same answers, fewer calls: every model found so far
            is a *witness*. If witnesses already show both values of C_i, then
            C_i is UNKNOWN without any new call; if they only show value b, a
            single call on KB /\\ (C_i != b) decides it. Soundness: C_i is forced
            to b  <=>  KB /\\ (C_i != b) has no model.
        """
        if strategy not in ("naive", "pruned"):
            raise ValueError(f"unknown strategy {strategy!r}")
        base = self.consistency()
        if not base.sat:
            return {v: Verdict.INCONSISTENT for v in variables}
        if strategy == "naive":
            return {v: self.classify(v) for v in variables}

        seen: Dict[int, set] = {v: {base.assignment[v]} for v in variables}

        def absorb(model: Dict[int, bool]) -> None:
            for v in variables:
                seen[v].add(model[v])

        out: Dict[int, Verdict] = {}
        for v in variables:
            if len(seen[v]) == 2:
                out[v] = Verdict.UNKNOWN
                continue
            (b,) = seen[v]
            res = self.query([-v if b else v])     # try to falsify the only seen value
            if res.sat:
                absorb(res.assignment)
                out[v] = Verdict.UNKNOWN
            else:
                out[v] = Verdict.CRIMINAL if b else Verdict.INNOCENT
        return out


# ---------------------------------------------------------------------------
# Model enumeration (used by the uniqueness check)
# ---------------------------------------------------------------------------
@dataclass
class ModelCount:
    count: int                                   # number of models found (<= limit)
    complete: bool                               # True if the enumeration was exhaustive
    models: List[Dict[int, bool]] = field(default_factory=list)  # projected on `project_vars`
    stats: SolverStats = field(default_factory=SolverStats)


def count_models(
    clauses: Iterable[Sequence[int]],
    project_vars: Sequence[int],
    num_vars: Optional[int] = None,
    limit: Optional[int] = 2,
    heuristic: str = "first",
) -> ModelCount:
    """Count models projected on `project_vars` (the primary variables).

    After each model M the blocking clause  OR_{v in project} (v != M[v])  is
    added, so auxiliary variables never produce duplicate primary solutions.
    Stops after `limit` models (limit=2 is enough to decide uniqueness).
    """
    base = [list(c) for c in clauses]
    blocking: List[List[int]] = []
    stats = SolverStats()
    models: List[Dict[int, bool]] = []
    while limit is None or len(models) < limit:
        res = DPLLSolver(base + blocking, num_vars=num_vars, heuristic=heuristic).solve()
        stats.add(res.stats)
        if not res.sat:
            return ModelCount(len(models), True, models, stats)
        proj = {v: res.assignment[v] for v in project_vars}
        models.append(proj)
        blocking.append([-v if val else v for v, val in proj.items()])
    return ModelCount(len(models), False, models, stats)
