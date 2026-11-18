"""Minimal headless Game Engine implementing :class:`GameEngineProtocol`.

Used by the agent tests, the CLI and the benchmark adapter. Member C's GUI
engine can replace it as long as it offers the same two methods
(`public_state`, `submit_verdict`).

It owns the hidden data (solution + unrevealed clues) and only hands out a
:class:`PublicState`. A verdict is accepted only if it is entailed by the
public KB (judged with the SAT solver) AND matches the hidden label.
"""
from __future__ import annotations

import copy
import json
from typing import Optional

from . import interface as itf
from .interface import CellInfo, PublicState, SubmitResult


class LocalGameEngine:
    def __init__(self, puzzle: dict, check_provability: bool = True):
        self._puzzle = copy.deepcopy(puzzle)
        self.check_provability = check_provability
        self.size: int = puzzle["size"]
        self.puzzle_id: str = puzzle.get("id", "")
        self._cells = tuple(
            CellInfo(c["id"], int(c["row"]), c["col"], c.get("name", ""), c.get("profession", ""))
            for c in puzzle["cells"]
        )
        self.submissions = 0
        self.restart()

    @classmethod
    def load(cls, path: str, **kw) -> "LocalGameEngine":
        with open(path, encoding="utf-8") as f:
            return cls(json.load(f), **kw)

    def restart(self) -> None:
        sol, clues = self._puzzle["solution"], self._puzzle["clues"]
        self._proved = {c: sol[c] for c in self._puzzle["initial_revealed"]}
        self._revealed = {c: copy.deepcopy(clues[c]) for c in self._puzzle["initial_revealed"]}

    # ------------------------------------------------------------- protocol
    def public_state(self) -> PublicState:
        return PublicState(self.size, self._cells, dict(self._proved), copy.deepcopy(self._revealed))

    def submit_verdict(self, cell: str, verdict: str) -> SubmitResult:
        from .agent import judge_verdict   # local import: avoid a cycle at module load

        self.submissions += 1
        verdict = str(verdict).upper()
        if self.check_provability:
            status = judge_verdict(self.public_state(), cell, verdict)
        else:
            ok = cell in self._puzzle["solution"] and cell not in self._proved \
                and verdict in ("CRIMINAL", "INNOCENT")
            status = itf.ACCEPTED if ok else itf.INVALID
        if status != itf.ACCEPTED:
            return SubmitResult(status, cell, verdict, message=f"{cell}: {status}")
        if self._puzzle["solution"][cell] != verdict:
            return SubmitResult(itf.WRONG, cell, verdict,
                                message="proved verdict disagrees with the hidden label (invalid puzzle)")
        self._proved[cell] = verdict
        self._revealed[cell] = copy.deepcopy(self._puzzle["clues"][cell])
        return SubmitResult(itf.ACCEPTED, cell, verdict, copy.deepcopy(self._revealed[cell]))

    # ------------------------------------------------------------- helpers
    def is_solved(self) -> bool:
        """All characters proved and equal to the hidden solution."""
        sol = self._puzzle["solution"]
        return len(self._proved) == len(sol) and all(self._proved[c] == sol[c] for c in sol)

    @property
    def full_puzzle(self) -> dict:
        """Engine-only access (e.g. for the uniqueness check). Never give this to the agent."""
        return copy.deepcopy(self._puzzle)
