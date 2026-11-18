"""Semantic evaluator for Griductive clues.

Evaluates truth values of clues under a complete truth assignment directly without CNF encoding.
"""

from typing import Dict, Union, List, Optional, Any
from .types import Status, ClueType, CompareOp
from .model import Clue, RegionSpec
from .regions import RegionResolver


class SemanticEvaluator:
    """Direct semantic evaluator for Griductive clues."""

    def __init__(self, resolver: RegionResolver):
        self.resolver = resolver

    def _get_bool(self, val: Union[bool, Status, str, int]) -> bool:
        """Convert input status value to canonical boolean: True for Criminal, False for Innocent."""
        if isinstance(val, bool):
            return val
        if isinstance(val, int):
            return val != 0
        if isinstance(val, Status):
            return val == Status.CRIMINAL
        if isinstance(val, str):
            s = val.strip().upper()
            if s in ("CRIMINAL", "TRUE", "1", "C"):
                return True
            if s in ("INNOCENT", "FALSE", "0", "I"):
                return False
        raise ValueError(f"Cannot interpret '{val}' as boolean status.")

    def _resolve_assignment_value(self, identifier: str, assignment: Dict[str, Any]) -> bool:
        """Look up character status by name or cell identifier."""
        cell_id = self.resolver.normalize_person_to_cell(identifier)
        if cell_id in assignment:
            return self._get_bool(assignment[cell_id])
        # Try raw identifier
        if identifier in assignment:
            return self._get_bool(assignment[identifier])
        # Try uppercase
        if identifier.upper() in assignment:
            return self._get_bool(assignment[identifier.upper()])
        # Try name associated with cell
        if cell_id in self.resolver.cell_to_name:
            name = self.resolver.cell_to_name[cell_id]
            if name in assignment:
                return self._get_bool(assignment[name])
        raise KeyError(f"Assignment missing entry for '{identifier}' (resolved cell '{cell_id}').")

    def evaluate(self, clue: Union[Clue, Dict[str, Any]], assignment: Dict[str, Any]) -> bool:
        """Evaluate whether a clue is satisfied under a complete truth assignment.
        
        Args:
            clue: Clue instance or raw dict from puzzle JSON.
            assignment: Mapping from cell IDs or character names to True (Criminal) or False (Innocent).
        
        Returns:
            True if clue is satisfied, False otherwise.
        """
        if isinstance(clue, dict):
            clue = Clue.from_dict(clue)

        clue.validate()

        if clue.clue_type == ClueType.FACT:
            assert clue.person is not None and clue.status is not None
            actual_bool = self._resolve_assignment_value(clue.person, assignment)
            expected_bool = clue.status.to_bool()
            return actual_bool == expected_bool

        elif clue.clue_type == ClueType.SAME:
            assert clue.person is not None and clue.person2 is not None
            val1 = self._resolve_assignment_value(clue.person, assignment)
            val2 = self._resolve_assignment_value(clue.person2, assignment)
            return val1 == val2

        elif clue.clue_type == ClueType.DIFFERENT:
            assert clue.person is not None and clue.person2 is not None
            val1 = self._resolve_assignment_value(clue.person, assignment)
            val2 = self._resolve_assignment_value(clue.person2, assignment)
            return val1 != val2

        elif clue.clue_type in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
            assert clue.region is not None and clue.k is not None
            cells = self.resolver.resolve(clue.region)
            target_bool = clue.target_status.to_bool()
            count = sum(1 for c in cells if self._resolve_assignment_value(c, assignment) == target_bool)

            if clue.clue_type == ClueType.EXACTLY:
                return count == clue.k
            elif clue.clue_type == ClueType.AT_LEAST:
                return count >= clue.k
            elif clue.clue_type == ClueType.AT_MOST:
                return count <= clue.k

        elif clue.clue_type == ClueType.PARITY:
            assert clue.region is not None and clue.parity is not None
            cells = self.resolver.resolve(clue.region)
            target_bool = clue.target_status.to_bool()
            count = sum(1 for c in cells if self._resolve_assignment_value(c, assignment) == target_bool)
            return (count % 2) == clue.parity

        elif clue.clue_type in (ClueType.COUNT_COMPARE, ClueType.COMPARE):
            assert clue.region is not None and clue.region2 is not None and clue.compare_op is not None
            cells1 = self.resolver.resolve(clue.region)
            cells2 = self.resolver.resolve(clue.region2)
            target_bool = clue.target_status.to_bool()
            count1 = sum(1 for c in cells1 if self._resolve_assignment_value(c, assignment) == target_bool)
            count2 = sum(1 for c in cells2 if self._resolve_assignment_value(c, assignment) == target_bool)
            return clue.compare_op.evaluate(count1, count2)

        elif clue.clue_type == ClueType.ALL_SAME:
            assert clue.region is not None
            cells = self.resolver.resolve(clue.region)
            if len(cells) <= 1:
                return True
            first_val = self._resolve_assignment_value(cells[0], assignment)
            return all(self._resolve_assignment_value(c, assignment) == first_val for c in cells[1:])

        raise ValueError(f"Unsupported clue type: {clue.clue_type}")

    def evaluate_all(self, clues: List[Union[Clue, Dict[str, Any]]], assignment: Dict[str, Any]) -> bool:
        """Check if all given clues are satisfied under the complete assignment."""
        return all(self.evaluate(c, assignment) for c in clues)


def evaluate_clue(clue: Union[Clue, Dict[str, Any]], assignment: Dict[str, Any], n: int) -> bool:
    """Convenience helper to evaluate a clue directly given grid size n."""
    resolver = RegionResolver(grid_size=n)
    evaluator = SemanticEvaluator(resolver)
    return evaluator.evaluate(clue, assignment)
