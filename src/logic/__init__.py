"""Logic core module for Griductive Solver."""

from .types import Status, ClueType, RegionType, Verdict, CompareOp, ParityType, COLS
from .model import CellCoord, Character, RegionSpec, Clue, Puzzle
from .regions import RegionResolver
from .evaluator import SemanticEvaluator, evaluate_clue
from .encoder import VarManager, CNFFormula, CNFEncoder, KnowledgeBase, encode_clue
from .extensions import (
    ParityClue,
    CountCompareClue,
    AllSameClue,
    AdvancedRegions,
    format_clue_natural_language,
)

__all__ = [
    "Status",
    "ClueType",
    "RegionType",
    "Verdict",
    "CompareOp",
    "ParityType",
    "COLS",
    "CellCoord",
    "Character",
    "RegionSpec",
    "Clue",
    "Puzzle",
    "RegionResolver",
    "SemanticEvaluator",
    "evaluate_clue",
    "VarManager",
    "CNFFormula",
    "CNFEncoder",
    "KnowledgeBase",
    "encode_clue",
    "ParityClue",
    "CountCompareClue",
    "AllSameClue",
    "AdvancedRegions",
    "format_clue_natural_language",
]
