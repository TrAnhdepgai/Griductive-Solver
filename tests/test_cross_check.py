"""Brute-force Cross-Verification Test: Semantic Evaluator vs CNF Encoder.

Formal verification:
For every clue template (FACT, SAME, DIFFERENT, EXACTLY, AT_LEAST, AT_MOST, PARITY,
COUNT_COMPARE, ALL_SAME), iterates through ALL 2^N possible truth assignments and
mathematically asserts:

    evaluator.evaluate(clue, assignment) == cnf_formula.is_satisfiable_under(primary_assignment)

This proves 100% semantic equivalence between the direct evaluator and the CNF encoder.
"""

import unittest
from itertools import product
from typing import Dict, List, Set
from src.logic.types import Status, ClueType, CompareOp
from src.logic.model import Character, RegionSpec, Clue
from src.logic.regions import RegionResolver
from src.logic.evaluator import SemanticEvaluator
from src.logic.encoder import VarManager, CNFEncoder, CNFFormula
from src.logic.extensions import ParityClue, CountCompareClue, AllSameClue


class TestCrossCheckBruteForce(unittest.TestCase):
    """Exhaustive brute-force cross validation across all possible models."""

    def _check_formula_satisfiable_with_fixed_primaries(
        self,
        formula: CNFFormula,
        primary_assignment: Dict[int, bool],
        aux_vars: List[int],
    ) -> bool:
        """Check whether there exists an assignment to auxiliary variables satisfying the formula."""
        if not aux_vars:
            return formula.is_satisfied_by(primary_assignment)

        # Brute-force auxiliary variables if present
        for aux_vals in product([False, True], repeat=len(aux_vars)):
            full_assignment = dict(primary_assignment)
            for var, val in zip(aux_vars, aux_vals):
                full_assignment[var] = val
            if formula.is_satisfied_by(full_assignment):
                return True
        return False

    def _verify_clue_equivalence(
        self,
        clue: Clue,
        characters: List[Character],
        grid_size: int,
    ) -> None:
        """Verify that clue evaluator matches CNF satisfiability for ALL 2^N assignments."""
        resolver = RegionResolver(grid_size=grid_size, characters=characters)
        var_mgr = VarManager(characters=characters, grid_size=grid_size)
        evaluator = SemanticEvaluator(resolver=resolver)
        encoder = CNFEncoder(var_mgr=var_mgr, resolver=resolver)

        # Record aux vars before and after encoding
        initial_aux_count = var_mgr.aux_var_count
        formula = encoder.encode_clue(clue)
        new_aux_vars = list(range(
            var_mgr.primary_var_count + 1 + initial_aux_count,
            var_mgr.total_var_count + 1,
        ))

        cell_ids = [c.cell.upper() for c in characters]
        num_chars = len(cell_ids)

        # Iterate over all 2^num_chars possible assignments
        for bits in product([False, True], repeat=num_chars):
            # Assignment dict for SemanticEvaluator
            eval_assignment = {cell_ids[i]: bits[i] for i in range(num_chars)}

            # Assignment dict with integer variable keys for CNFFormula
            primary_int_assignment = {var_mgr.get_var(cell_ids[i]): bits[i] for i in range(num_chars)}

            # 1. Semantic truth value
            expected_truth = evaluator.evaluate(clue, eval_assignment)

            # 2. CNF truth value (projected on primary variables)
            cnf_truth = self._check_formula_satisfiable_with_fixed_primaries(
                formula=formula,
                primary_assignment=primary_int_assignment,
                aux_vars=new_aux_vars,
            )

            self.assertEqual(
                expected_truth,
                cnf_truth,
                f"Mismatch for clue {clue.clue_type.value} on assignment {eval_assignment}: "
                f"Evaluator={expected_truth}, CNF={cnf_truth}",
            )

    # -------------------------------------------------------------------------
    # Core Clue Templates
    # -------------------------------------------------------------------------

    def test_fact_equivalence(self):
        chars = [Character(name="Alice", cell="A1")]
        for status in [Status.CRIMINAL, Status.INNOCENT]:
            clue = Clue.fact("fact_test", "A1", status)
            self._verify_clue_equivalence(clue, chars, grid_size=1)

    def test_same_equivalence(self):
        chars = [Character(name="Alice", cell="A1"), Character(name="Bob", cell="B1")]
        clue = Clue.same("same_test", "A1", "B1")
        self._verify_clue_equivalence(clue, chars, grid_size=2)

    def test_different_equivalence(self):
        chars = [Character(name="Alice", cell="A1"), Character(name="Bob", cell="B1")]
        clue = Clue.different("diff_test", "A1", "B1")
        self._verify_clue_equivalence(clue, chars, grid_size=2)

    def test_exactly_equivalence_all_k(self):
        # 3 variables: row 1 (A1, B1, C1)
        chars = [
            Character(name="A", cell="A1"),
            Character(name="B", cell="B1"),
            Character(name="C", cell="C1"),
        ]
        reg = RegionSpec.row_region(1)
        for k in range(0, 4):  # k = 0, 1, 2, 3
            # Target = CRIMINAL
            clue_crim = Clue.exactly(f"ex_crim_{k}", k, reg, target_status=Status.CRIMINAL)
            self._verify_clue_equivalence(clue_crim, chars, grid_size=3)

            # Target = INNOCENT
            clue_inno = Clue.exactly(f"ex_inno_{k}", k, reg, target_status=Status.INNOCENT)
            self._verify_clue_equivalence(clue_inno, chars, grid_size=3)

    def test_at_least_equivalence_all_k(self):
        chars = [
            Character(name="A", cell="A1"),
            Character(name="B", cell="B1"),
            Character(name="C", cell="C1"),
            Character(name="D", cell="A2"),
        ]
        reg = RegionSpec.explicit_region(["A1", "B1", "C1", "A2"])
        for k in range(0, 5):
            clue = Clue.at_least(f"al_{k}", k, reg)
            self._verify_clue_equivalence(clue, chars, grid_size=2)

    def test_at_most_equivalence_all_k(self):
        chars = [
            Character(name="A", cell="A1"),
            Character(name="B", cell="B1"),
            Character(name="C", cell="C1"),
            Character(name="D", cell="A2"),
        ]
        reg = RegionSpec.explicit_region(["A1", "B1", "C1", "A2"])
        for k in range(0, 5):
            clue = Clue.at_most(f"am_{k}", k, reg)
            self._verify_clue_equivalence(clue, chars, grid_size=2)

    # -------------------------------------------------------------------------
    # Extensions Equivalence
    # -------------------------------------------------------------------------

    def test_parity_equivalence(self):
        chars = [
            Character(name="A", cell="A1"),
            Character(name="B", cell="B1"),
            Character(name="C", cell="C1"),
        ]
        reg = RegionSpec.row_region(1)
        # Even (parity = 0)
        clue_even = ParityClue.even("p_even", reg)
        self._verify_clue_equivalence(clue_even, chars, grid_size=3)

        # Odd (parity = 1)
        clue_odd = ParityClue.odd("p_odd", reg)
        self._verify_clue_equivalence(clue_odd, chars, grid_size=3)

    def test_count_compare_equivalence(self):
        chars = [
            Character(name="A", cell="A1"),
            Character(name="B", cell="B1"),
            Character(name="C", cell="A2"),
            Character(name="D", cell="B2"),
        ]
        r1 = RegionSpec.explicit_region(["A1", "B1"])
        r2 = RegionSpec.explicit_region(["A2", "B2"])

        for op in [CompareOp.GT, CompareOp.EQ, CompareOp.LE]:
            clue = Clue.count_compare(f"cmp_{op.name}", r1, op, r2)
            self._verify_clue_equivalence(clue, chars, grid_size=2)

    def test_all_same_equivalence(self):
        chars = [
            Character(name="A", cell="A1"),
            Character(name="B", cell="B1"),
            Character(name="C", cell="C1"),
        ]
        reg = RegionSpec.row_region(1)
        clue = AllSameClue.create("all_same_test", reg)
        self._verify_clue_equivalence(clue, chars, grid_size=3)


if __name__ == "__main__":
    unittest.main()
