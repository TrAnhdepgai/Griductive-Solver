"""Contract between the Game Engine (member C) and the Logic Agent (member B).

The agent only ever sees a :class:`PublicState`: grid size, the public card
data (id, name, profession), the statuses proved so far and the clues that are
face-up. Hidden statuses and unrevealed clues never cross this boundary.

Any engine (the GUI engine of member C, or :class:`LocalGameEngine` used for
tests/benchmarks) only has to implement :class:`GameEngineProtocol`.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from typing import Dict, Optional, Protocol, Tuple, runtime_checkable

COLS = "ABCDE"

# Results returned by GameEngineProtocol.submit_verdict
ACCEPTED = "ACCEPTED"
NOT_PROVABLE = "NOT_PROVABLE"
CONTRADICTED = "CONTRADICTED"
INCONSISTENT = "INCONSISTENT"     # public KB has no model (broken puzzle)
WRONG = "WRONG"                   # proved verdict disagrees with the hidden label (broken puzzle)
INVALID = "INVALID"               # unknown cell / already resolved / bad verdict string


@dataclass(frozen=True)
class CellInfo:
    """Public card data. Names/professions carry no logic unless a clue uses them."""

    id: str           # "B2"
    row: int          # 1-based
    col: str          # "B"
    name: str = ""
    profession: str = ""


@dataclass
class PublicState:
    """Everything the agent is allowed to know at step t."""

    size: int
    cells: Tuple[CellInfo, ...]                         # row-major order
    proved: Dict[str, str] = field(default_factory=dict)          # cell -> "CRIMINAL"/"INNOCENT"
    revealed_clues: Dict[str, dict] = field(default_factory=dict)  # owner cell -> structured clue

    @property
    def cell_ids(self) -> Tuple[str, ...]:
        return tuple(c.id for c in self.cells)

    def unresolved(self) -> Tuple[str, ...]:
        """Cells without a proved status, in row-major order."""
        return tuple(c for c in self.cell_ids if c not in self.proved)

    def is_complete(self) -> bool:
        return len(self.proved) == len(self.cells)

    def name_of(self, cell: str) -> str:
        for c in self.cells:
            if c.id == cell:
                return c.name or cell
        return cell

    def copy(self) -> "PublicState":
        return PublicState(self.size, self.cells, dict(self.proved), copy.deepcopy(self.revealed_clues))


@dataclass
class SubmitResult:
    """Answer of the engine to a CRIMINAL/INNOCENT call."""

    status: str                         # ACCEPTED / NOT_PROVABLE / CONTRADICTED / ...
    cell: str
    verdict: str
    revealed_clue: Optional[dict] = None  # the newly face-up clue when ACCEPTED
    message: str = ""

    @property
    def accepted(self) -> bool:
        return self.status == ACCEPTED


@runtime_checkable
class GameEngineProtocol(Protocol):
    """What the Logic Agent needs from a Game Engine."""

    def public_state(self) -> PublicState:
        """Snapshot of the public knowledge (must not contain hidden data)."""
        ...

    def submit_verdict(self, cell: str, verdict: str) -> SubmitResult:
        """Call `cell` CRIMINAL/INNOCENT. On ACCEPTED the card is flipped and its clue revealed."""
        ...


def cells_for_size(n: int) -> Tuple[CellInfo, ...]:
    """Anonymous row-major cells for an n x n board (useful in tests)."""
    return tuple(CellInfo(f"{COLS[c]}{r}", r, COLS[c]) for r in range(1, n + 1) for c in range(n))
