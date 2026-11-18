"""Build KB_t from the public state using member A's CNF encoder.

    KB_t = CNF(revealed clues)  /\\  unit clauses for proved verdicts

Primary variables follow the team convention (row-major, A1 = 1, B1 = 2, ...);
auxiliary variables created by the encoder are numbered after them.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from src.logic.encoder import CNFEncoder, VarManager
from src.logic.model import Clue

from .interface import PublicState


def clue_label(owner: str) -> str:
    """Identifier of a clue in traces: the clue printed on card `owner`."""
    return f"clue@{owner}"


@dataclass
class KnowledgeBaseSnapshot:
    """Encoded KB_t plus bookkeeping for traces and statistics."""

    size: int
    clauses: List[List[int]]
    num_vars: int
    primary_vars: int
    aux_vars: int
    var_of: Dict[str, int]                       # cell -> primary variable
    cell_of: Dict[int, str]                      # primary variable -> cell
    active_clues: List[str]                      # owner cells of the encoded clues (row-major)
    clue_clauses: Dict[str, List[List[int]]] = field(default_factory=dict)
    unit_clauses: Dict[str, List[int]] = field(default_factory=dict)   # cell -> [lit]

    @property
    def clause_count(self) -> int:
        return len(self.clauses)

    def stats(self) -> Dict[str, int]:
        return {"primary_vars": self.primary_vars, "aux_vars": self.aux_vars,
                "clauses": self.clause_count}

    def fmt_literal(self, lit: int) -> str:
        cell = self.cell_of.get(abs(lit), f"aux{abs(lit)}")
        return f"{'~' if lit < 0 else ''}C[{cell}]"


def build_kb(
    state: PublicState,
    exclude_clues: Iterable[str] = (),
    extra_clues: Optional[Dict[str, dict]] = None,
) -> KnowledgeBaseSnapshot:
    """Encode the public state into CNF.

    exclude_clues -- owner cells whose clue is left out (used by Hint to find
                     a minimal set of supporting clues).
    extra_clues   -- additional clues (used by the uniqueness check, which
                     works on the complete clue set rather than a game state).
    """
    n = state.size
    vm = VarManager.from_grid_size(n)
    encoder = CNFEncoder(vm)
    excluded = set(exclude_clues)

    var_of = {c: vm.get_var(c) for c in state.cell_ids}
    cell_of = {v: c for c, v in var_of.items()}

    clauses: List[List[int]] = []
    clue_clauses: Dict[str, List[List[int]]] = {}
    all_clues = dict(state.revealed_clues)
    all_clues.update(extra_clues or {})
    order = {c: i for i, c in enumerate(state.cell_ids)}
    active = sorted((c for c in all_clues if c not in excluded), key=lambda c: order.get(c, 1 << 30))
    for owner in active:
        clue = Clue.from_dict(all_clues[owner], clue_id=clue_label(owner))
        cnf = [list(cl) for cl in encoder.encode_clue(clue).clauses]
        clue_clauses[owner] = cnf
        clauses.extend(cnf)

    units: Dict[str, List[int]] = {}
    for cell in state.cell_ids:
        if cell in state.proved:
            lit = var_of[cell] if state.proved[cell] == "CRIMINAL" else -var_of[cell]
            units[cell] = [lit]
            clauses.append([lit])

    return KnowledgeBaseSnapshot(
        size=n,
        clauses=clauses,
        num_vars=vm.total_var_count,
        primary_vars=vm.primary_var_count,
        aux_vars=vm.aux_var_count,
        var_of=var_of,
        cell_of=cell_of,
        active_clues=active,
        clue_clauses=clue_clauses,
        unit_clauses=units,
    )
