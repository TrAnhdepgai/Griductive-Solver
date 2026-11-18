"""Part B: deductive logic agent on top of the DPLL solver."""

from .agent import (
    INCONSISTENT,
    REJECTED,
    SOLVED,
    STEP_LIMIT,
    STUCK,
    AgentResult,
    Classification,
    Hint,
    LogicAgent,
    TraceStep,
    classify_state,
    explain,
    format_trace,
    judge_verdict,
)
from .interface import CellInfo, GameEngineProtocol, PublicState, SubmitResult
from .knowledge import KnowledgeBaseSnapshot, build_kb, clue_label
from .local_engine import LocalGameEngine
from .uniqueness import UniquenessReport, check_puzzle_uniqueness, check_uniqueness

__all__ = [
    "LogicAgent", "AgentResult", "TraceStep", "Classification", "Hint",
    "classify_state", "judge_verdict", "explain", "format_trace",
    "SOLVED", "STUCK", "INCONSISTENT", "REJECTED", "STEP_LIMIT",
    "CellInfo", "PublicState", "SubmitResult", "GameEngineProtocol",
    "KnowledgeBaseSnapshot", "build_kb", "clue_label",
    "LocalGameEngine",
    "UniquenessReport", "check_uniqueness", "check_puzzle_uniqueness",
]
