"""Logic core module for Griductive Solver."""

from .types import Status, ClueType, RegionType, Verdict, CompareOp
from .model import CellCoord, Character, RegionSpec, Clue
from .regions import RegionResolver
from .evaluator import SemanticEvaluator
from .encoder import VarManager, CNFFormula, CNFEncoder, KnowledgeBase
from .extensions import (
    ParityClue,
    CountCompareClue,
    AllSameClue,
    AdvancedRegions,
)

__all__ = [
    "Status",
    "ClueType",
    "RegionType",
    "Verdict",
    "CompareOp",
    "CellCoord",
    "Character",
    "RegionSpec",
    "Clue",
    "RegionResolver",
    "SemanticEvaluator",
    "VarManager",
    "CNFFormula",
    "CNFEncoder",
    "KnowledgeBase",
    "ParityClue",
    "CountCompareClue",
    "AllSameClue",
    "AdvancedRegions",
]
