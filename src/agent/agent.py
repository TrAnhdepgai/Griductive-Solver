"""Deductive Logic Agent (Part B, section 4.4).

Loop (section 2.2), at step t:
  1. Build KB_t from the PUBLIC state only.
  2. Classify every unresolved character with SAT queries:
        KB_t & ~C_i UNSAT -> CRIMINAL,  KB_t & C_i UNSAT -> INNOCENT, else UNKNOWN;
     KB_t UNSAT -> INCONSISTENT.
  3. Pick the first forced character in row-major order (never guess).
  4. Submit the verdict to the Game Engine, which flips the card and reveals
     its clue; the next KB_{t+1} contains that clue and the new unit clause.
  5. Stop when every character is proved (SOLVED), nothing is forced (STUCK),
     KB_t is unsatisfiable (INCONSISTENT) or the engine rejects a verdict.

Every step is recorded in a :class:`TraceStep`.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from src.logic.types import Verdict
from src.sat import EntailmentChecker, SATQuery, SolverStats

from . import interface as itf
from .interface import GameEngineProtocol, PublicState, SubmitResult
from .knowledge import KnowledgeBaseSnapshot, build_kb, clue_label

# Terminal states of a run
SOLVED = "SOLVED"
STUCK = "STUCK"
INCONSISTENT = "INCONSISTENT"
REJECTED = "REJECTED"
STEP_LIMIT = "STEP_LIMIT"


# ---------------------------------------------------------------------------
# Data records
# ---------------------------------------------------------------------------
@dataclass
class Classification:
    """Result of classifying every unresolved character of one state."""

    verdicts: Dict[str, Verdict]                 # cell -> CRIMINAL / INNOCENT / UNKNOWN / INCONSISTENT
    queries: List[SATQuery]
    kb: KnowledgeBaseSnapshot
    stats: SolverStats
    consistent: bool

    @property
    def forced(self) -> List[str]:
        """Forced cells in row-major order."""
        return [c for c, v in self.verdicts.items() if v in (Verdict.CRIMINAL, Verdict.INNOCENT)]


@dataclass
class TraceStep:
    step: int
    wave: int
    active_clues: List[str]                      # clue ids in KB_t
    kb_stats: Dict[str, int]                     # primary/aux vars, clauses of KB_t
    queries: List[SATQuery]
    classification: Dict[str, str]               # cell -> verdict string
    cell: Optional[str]                          # chosen character (None on terminal steps)
    verdict: Optional[str]
    engine_status: Optional[str]
    revealed_clue: Optional[dict]
    revealed_clue_id: Optional[str]
    sat_stats: Dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["queries"] = [q.as_dict() for q in self.queries]
        return d


@dataclass
class AgentResult:
    status: str
    trace: List[TraceStep]
    waves: int
    sat_stats: SolverStats
    kb_stats: Dict[str, int]                     # final KB (primary/aux vars, clauses)
    max_kb_stats: Dict[str, int]                 # largest KB seen during the run
    proved: Dict[str, str]
    runtime_s: float

    @property
    def steps(self) -> int:
        """Number of accepted verdicts."""
        return sum(1 for t in self.trace if t.engine_status == itf.ACCEPTED)

    @property
    def solved(self) -> bool:
        return self.status == SOLVED

    def as_dict(self) -> dict:
        return {
            "status": self.status, "steps": self.steps, "waves": self.waves,
            "sat_stats": self.sat_stats.as_dict(), "kb_stats": self.kb_stats,
            "max_kb_stats": self.max_kb_stats, "proved": self.proved,
            "runtime_s": self.runtime_s, "trace": [t.as_dict() for t in self.trace],
        }


@dataclass
class Hint:
    cell: Optional[str]                          # None when nothing is forced
    verdict: Optional[str]
    supporting_clues: List[str]                  # owner cells of a minimal clue subset proving it
    supporting_facts: List[str]                  # proved cells whose status is also needed
    message: str


# ---------------------------------------------------------------------------
# Stateless helpers (usable by the GUI without running the whole agent)
# ---------------------------------------------------------------------------
def classify_state(state: PublicState, heuristic: str = "first", strategy: str = "pruned",
                   step: Optional[int] = None) -> Classification:
    """Classify every unresolved character of a public state."""
    kb = build_kb(state)
    name = "KB" if step is None else f"KB_{step}"
    checker = EntailmentChecker(kb.clauses, kb.num_vars, heuristic=heuristic,
                                kb_name=name, fmt_literal=kb.fmt_literal)
    cells = list(state.unresolved())
    by_var = checker.classify_many([kb.var_of[c] for c in cells], strategy=strategy)
    verdicts = {c: by_var[kb.var_of[c]] for c in cells}
    return Classification(verdicts, checker.queries, kb, checker.stats.copy(), checker.is_consistent())


def judge_verdict(state: PublicState, cell: str, verdict: str, heuristic: str = "first") -> str:
    """Engine-side check of a player's call (section 4.1).

    Returns ACCEPTED if `verdict` is entailed by the public KB, CONTRADICTED if
    the opposite verdict is entailed, NOT_PROVABLE if neither is, INCONSISTENT
    if the public KB has no model, INVALID for a bad request.
    """
    verdict = str(verdict).upper()
    if cell not in state.cell_ids or cell in state.proved or verdict not in ("CRIMINAL", "INNOCENT"):
        return itf.INVALID
    kb = build_kb(state)
    checker = EntailmentChecker(kb.clauses, kb.num_vars, heuristic=heuristic)
    if not checker.is_consistent():
        return itf.INCONSISTENT
    var = kb.var_of[cell]
    lit = var if verdict == "CRIMINAL" else -var
    if checker.entails(lit):
        return itf.ACCEPTED
    if checker.entails(-lit):
        return itf.CONTRADICTED
    return itf.NOT_PROVABLE


def explain(state: PublicState, cell: str, verdict: str, heuristic: str = "first") -> Tuple[List[str], List[str]]:
    """A minimal set of revealed clues (and proved statuses) that entails `verdict` for `cell`.

    Deletion-based: drop each clue/status in turn and keep it out if the
    verdict is still entailed. The result is irredundant (every element is needed).
    """
    def entailed(clues_out: Sequence[str], facts_out: Sequence[str]) -> bool:
        st = state.copy()
        for f in facts_out:
            st.proved.pop(f, None)
        kb = build_kb(st, exclude_clues=clues_out)
        var = kb.var_of[cell]
        lit = var if verdict == "CRIMINAL" else -var
        return EntailmentChecker(kb.clauses, kb.num_vars, heuristic=heuristic).entails(lit)

    order = state.cell_ids
    clues = [c for c in order if c in state.revealed_clues]
    facts = [c for c in order if c in state.proved]
    clues_out: List[str] = []
    facts_out: List[str] = []
    for c in clues:
        if entailed(clues_out + [c], facts_out):
            clues_out.append(c)
    for f in facts:
        if entailed(clues_out, facts_out + [f]):
            facts_out.append(f)
    return [c for c in clues if c not in clues_out], [f for f in facts if f not in facts_out]


# ---------------------------------------------------------------------------
# The agent
# ---------------------------------------------------------------------------
class LogicAgent:
    """No-guess deductive agent. It only talks to the engine through the public protocol."""

    def __init__(self, engine: GameEngineProtocol, heuristic: str = "first", strategy: str = "pruned"):
        self.engine = engine
        self.heuristic = heuristic
        self.strategy = strategy
        self.trace: List[TraceStep] = []
        self.sat_stats = SolverStats()
        self.waves = 0
        self._pending_wave: set = set()
        self._max_kb: Dict[str, int] = {"primary_vars": 0, "aux_vars": 0, "clauses": 0}
        self._last_kb: Dict[str, int] = {}

    # ------------------------------------------------------------ queries
    def classify(self) -> Classification:
        """Classify every unresolved character of the current public state."""
        c = classify_state(self.engine.public_state(), self.heuristic, self.strategy,
                           step=len(self.trace))
        self.sat_stats.add(c.stats)
        return c

    def hint(self) -> Hint:
        """Next forced character and the revealed clues that prove it (no hidden data used)."""
        state = self.engine.public_state()
        cls = classify_state(state, self.heuristic, self.strategy)
        if not cls.consistent:
            return Hint(None, None, [], [], "The revealed clues contradict each other.")
        if not cls.forced:
            return Hint(None, None, [], [], "No character can be proved from the revealed clues.")
        cell = cls.forced[0]
        verdict = cls.verdicts[cell].value
        clues, facts = explain(state, cell, verdict, self.heuristic)
        who = state.name_of(cell)
        src = ", ".join(clue_label(c) for c in clues) or "the known statuses"
        return Hint(cell, verdict, clues, facts, f"{who} ({cell}) must be {verdict}: follows from {src}.")

    # ------------------------------------------------------------ loop
    def step(self) -> TraceStep:
        """One deduction step: classify, choose the first forced cell, submit it."""
        t = len(self.trace) + 1
        state = self.engine.public_state()
        cls = classify_state(state, self.heuristic, self.strategy, step=t - 1)
        self.sat_stats.add(cls.stats)
        kb_stats = cls.kb.stats()
        self._last_kb = kb_stats
        for k, v in kb_stats.items():
            self._max_kb[k] = max(self._max_kb[k], v)

        forced = cls.forced
        cell = verdict = None
        result: Optional[SubmitResult] = None
        if cls.consistent and forced:
            if not self._pending_wave:           # same wave definition as tools/reference.py
                self.waves += 1
                self._pending_wave = set(forced)
            cell = forced[0]
            verdict = cls.verdicts[cell].value
            result = self.engine.submit_verdict(cell, verdict)
            if result.accepted:
                self._pending_wave.discard(cell)

        step = TraceStep(
            step=t,
            wave=self.waves,
            active_clues=[clue_label(c) for c in cls.kb.active_clues],
            kb_stats=kb_stats,
            queries=cls.queries,
            classification={c: v.value for c, v in cls.verdicts.items()},
            cell=cell,
            verdict=verdict,
            engine_status=None if result is None else result.status,
            revealed_clue=None if result is None else result.revealed_clue,
            revealed_clue_id=clue_label(cell) if result is not None and result.accepted else None,
            sat_stats=cls.stats.as_dict(),
        )
        self.trace.append(step)
        return step

    def run(self, max_steps: Optional[int] = None) -> AgentResult:
        t0 = time.perf_counter()
        status = STEP_LIMIT
        while max_steps is None or len(self.trace) < max_steps:
            if self.engine.public_state().is_complete():
                status = SOLVED
                break
            st = self.step()
            if st.engine_status == itf.ACCEPTED:
                continue
            if st.cell is None:
                status = INCONSISTENT if any(v == Verdict.INCONSISTENT.value
                                             for v in st.classification.values()) else STUCK
            else:
                status = REJECTED
            break
        state = self.engine.public_state()
        if status == STEP_LIMIT and state.is_complete():
            status = SOLVED
        return AgentResult(
            status=status,
            trace=self.trace,
            waves=self.waves,
            sat_stats=self.sat_stats,
            kb_stats=self._last_kb or build_kb(state).stats(),
            max_kb_stats=dict(self._max_kb),
            proved=dict(state.proved),
            runtime_s=time.perf_counter() - t0,
        )


# ---------------------------------------------------------------------------
# Pretty printing
# ---------------------------------------------------------------------------
def format_trace(result: AgentResult, show_queries: bool = False) -> str:
    lines = []
    for t in result.trace:
        head = f"Step {t.step:>2} (wave {t.wave}) | KB: {t.kb_stats['primary_vars']} prim, " \
               f"{t.kb_stats['aux_vars']} aux, {t.kb_stats['clauses']} clauses | " \
               f"{len(t.queries)} SAT queries"
        lines.append(head)
        lines.append(f"    active clues : {', '.join(t.active_clues) or '-'}")
        forced = {c: v for c, v in t.classification.items() if v != "UNKNOWN"}
        lines.append(f"    forced       : {forced or 'none'}")
        if show_queries:
            for q in t.queries:
                lines.append(f"      {q.label:<28} -> {q.result:<5} (dec={q.decisions}, "
                             f"prop={q.propagations}, bt={q.backtracks})")
        if t.cell:
            lines.append(f"    verdict      : {t.cell} = {t.verdict} -> {t.engine_status}")
            if t.revealed_clue is not None:
                lines.append(f"    revealed     : {t.revealed_clue_id} {t.revealed_clue}")
        else:
            lines.append("    verdict      : none (terminal)")
    s = result.sat_stats
    lines.append(f"Result: {result.status} | steps={result.steps} waves={result.waves} "
                 f"SAT calls={s.calls} decisions={s.decisions} propagations={s.propagations} "
                 f"backtracks={s.backtracks} time={result.runtime_s:.4f}s")
    return "\n".join(lines)
