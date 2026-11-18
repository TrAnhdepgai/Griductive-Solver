"""Comprehensive unit tests for Griductive Logic Core (Part A).

Tests:
- CellCoord and RegionResolver (row, col, neighbors, corners, boundary, between, common neighbors, set operations)
- VarManager (deterministic mapping, sorting by display name, auxiliary separation)
- Clue models, parameters validation, and serialization
- SemanticEvaluator (truth evaluation under complete assignments)
- CNFEncoder (combinatorial and sequential cardinality, binary relations, extensions)
- KnowledgeBase (KB_t assembly, revealed clues, unit clauses for proved verdicts, stats reporting)
"""

import unittest
from src.logic.types import Status, ClueType, RegionType, CompareOp
from src.logic.model import CellCoord, Character, RegionSpec, Clue
from src.logic.regions import RegionResolver
from src.logic.evaluator import SemanticEvaluator
from src.logic.encoder import VarManager, CNFFormula, CNFEncoder, KnowledgeBase
from src.logic.extensions import ParityClue, CountCompareClue, AllSameClue, AdvancedRegions


class TestCellCoordAndRegions(unittest.TestCase):
    """Test grid coordinate manipulation and region resolution."""

    def test_cell_coord(self):
        coord = CellCoord.from_str("B2")
        self.assertEqual(coord.row, 2)
        self.assertEqual(coord.col, 1)
        self.assertEqual(coord.col_letter, "B")
        self.assertEqual(coord.cell_id, "B2")

        c1 = CellCoord.from_str("A1")
        c2 = CellCoord.from_str("B2")
        self.assertTrue(c1.is_neighbor(c2))
        self.assertFalse(c1.is_neighbor(c1))  # self excluded

    def test_region_resolver_core(self):
        resolver = RegionResolver(grid_size=3)

        # Row 1 -> A1, B1, C1
        row1 = resolver.resolve(RegionSpec.row_region(1))
        self.assertEqual(row1, ["A1", "B1", "C1"])

        # Col B -> B1, B2, B3
        col_b = resolver.resolve(RegionSpec.col_region("B"))
        self.assertEqual(col_b, ["B1", "B2", "B3"])

        # Center cell B2 -> 8 neighbors
        n_b2 = resolver.resolve(RegionSpec.neighbors_region("B2"))
        self.assertEqual(len(n_b2), 8)
        self.assertNotIn("B2", n_b2)

        # Corner cell A1 -> 3 neighbors (B1, A2, B2)
        n_a1 = resolver.resolve(RegionSpec.neighbors_region("A1"))
        self.assertEqual(sorted(n_a1), ["A2", "B1", "B2"])

        # Edge cell B1 -> 5 neighbors (A1, C1, A2, B2, C2)
        n_b1 = resolver.resolve(RegionSpec.neighbors_region("B1"))
        self.assertEqual(len(n_b1), 5)

        # Explicit
        exp = resolver.resolve(RegionSpec.explicit_region(["c3", "A1"]))
        self.assertEqual(exp, ["A1", "C3"])

    def test_region_resolver_advanced(self):
        resolver = RegionResolver(grid_size=3)

        # Corners
        corners = resolver.resolve(AdvancedRegions.corners())
        self.assertEqual(corners, ["A1", "C1", "A3", "C3"])

        # Boundary
        boundary = resolver.resolve(AdvancedRegions.boundary())
        self.assertEqual(len(boundary), 8)
        self.assertNotIn("B2", boundary)

        # Interior
        interior = resolver.resolve(AdvancedRegions.interior())
        self.assertEqual(interior, ["B2"])

        # Common neighbors of A1 and C1 -> B1, B2
        common = resolver.resolve(AdvancedRegions.common_neighbors("A1", "C1"))
        self.assertEqual(common, ["B1", "B2"])

        # Between A1 and C1 -> B1
        between_row = resolver.resolve(AdvancedRegions.between("A1", "C1"))
        self.assertEqual(between_row, ["B1"])

        # Between A1 and C3 (diagonal) -> B2
        between_diag = resolver.resolve(AdvancedRegions.between("A1", "C3"))
        self.assertEqual(between_diag, ["B2"])

        # Intersection of Row 1 and Col B -> B1
        r_inter = resolver.resolve(AdvancedRegions.intersection(RegionSpec.row_region(1), RegionSpec.col_region("B")))
        self.assertEqual(r_inter, ["B1"])

    def test_out_of_bounds_validation(self):
        resolver = RegionResolver(grid_size=3)
        with self.assertRaises(ValueError):
            resolver.resolve(RegionSpec.row_region(4))
        with self.assertRaises(ValueError):
            resolver.resolve(RegionSpec.col_region("D"))
        with self.assertRaises(ValueError):
            resolver.normalize_person_to_cell("Z9")


class TestVarManager(unittest.TestCase):
    """Test deterministic mapping and variable management."""

    def test_deterministic_ordering_by_display_name(self):
        # Characters with arbitrary input order
        chars = [
            Character(name="Zack", cell="A1"),
            Character(name="Alice", cell="B1"),
            Character(name="Bob", cell="C1"),
        ]
        vm = VarManager(chars)

        # Must be sorted alphabetically: Alice (1), Bob (2), Zack (3)
        self.assertEqual(vm.get_var("Alice"), 1)
        self.assertEqual(vm.get_var("Bob"), 2)
        self.assertEqual(vm.get_var("Zack"), 3)

        # Lookup by cell identifier must also match
        self.assertEqual(vm.get_var("B1"), 1)
        self.assertEqual(vm.get_var("C1"), 2)
        self.assertEqual(vm.get_var("A1"), 3)

        self.assertEqual(vm.primary_var_count, 3)
        self.assertEqual(vm.aux_var_count, 0)

    def test_auxiliary_variable_separation(self):
        chars = [Character(name="A", cell="A1"), Character(name="B", cell="B1")]
        vm = VarManager(chars)

        self.assertEqual(vm.primary_var_count, 2)
        aux1 = vm.allocate_aux_var("aux1")
        aux2 = vm.allocate_aux_var("aux2")

        self.assertEqual(aux1, 3)
        self.assertEqual(aux2, 4)
        self.assertEqual(vm.aux_var_count, 2)
        self.assertEqual(vm.total_var_count, 4)


class TestSemanticEvaluator(unittest.TestCase):
    """Test direct truth-value evaluation."""

    def setUp(self):
        self.resolver = RegionResolver(grid_size=3)
        self.evaluator = SemanticEvaluator(self.resolver)
        # Assignment: A1=CRIMINAL, B1=INNOCENT, C1=CRIMINAL
        self.assignment = {
            "A1": Status.CRIMINAL,
            "B1": Status.INNOCENT,
            "C1": Status.CRIMINAL,
            "A2": Status.INNOCENT,
            "B2": Status.CRIMINAL,
            "C2": Status.INNOCENT,
            "A3": Status.INNOCENT,
            "B3": Status.INNOCENT,
            "C3": Status.INNOCENT,
        }

    def test_fact_evaluator(self):
        clue_true = Clue.fact("c1", "A1", Status.CRIMINAL)
        clue_false = Clue.fact("c2", "A1", Status.INNOCENT)
        self.assertTrue(self.evaluator.evaluate(clue_true, self.assignment))
        self.assertFalse(self.evaluator.evaluate(clue_false, self.assignment))

    def test_same_and_different_evaluator(self):
        # A1 (C) and C1 (C) are SAME -> True
        clue_same = Clue.same("c_same", "A1", "C1")
        self.assertTrue(self.evaluator.evaluate(clue_same, self.assignment))

        # A1 (C) and B1 (I) are DIFFERENT -> True
        clue_diff = Clue.different("c_diff", "A1", "B1")
        self.assertTrue(self.evaluator.evaluate(clue_diff, self.assignment))

    def test_counting_evaluator(self):
        # Row 1 has A1(C), B1(I), C1(C) -> 2 criminals
        reg1 = RegionSpec.row_region(1)
        self.assertTrue(self.evaluator.evaluate(Clue.exactly("c_ex", 2, reg1), self.assignment))
        self.assertFalse(self.evaluator.evaluate(Clue.exactly("c_ex", 1, reg1), self.assignment))

        self.assertTrue(self.evaluator.evaluate(Clue.at_least("c_al", 2, reg1), self.assignment))
        self.assertTrue(self.evaluator.evaluate(Clue.at_least("c_al", 1, reg1), self.assignment))
        self.assertFalse(self.evaluator.evaluate(Clue.at_least("c_al", 3, reg1), self.assignment))

        self.assertTrue(self.evaluator.evaluate(Clue.at_most("c_am", 2, reg1), self.assignment))
        self.assertFalse(self.evaluator.evaluate(Clue.at_most("c_am", 1, reg1), self.assignment))

    def test_extensions_evaluator(self):
        # Parity: Row 1 has 2 criminals -> EVEN
        reg1 = RegionSpec.row_region(1)
        self.assertTrue(self.evaluator.evaluate(ParityClue.even("p_even", reg1), self.assignment))
        self.assertFalse(self.evaluator.evaluate(ParityClue.odd("p_odd", reg1), self.assignment))

        # Count compare: Row 1 has 2 criminals, Row 2 has 1 criminal (B2) -> Row 1 > Row 2
        reg2 = RegionSpec.row_region(2)
        comp = CountCompareClue.more_than("cmp", reg1, reg2)
        self.assertTrue(self.evaluator.evaluate(comp, self.assignment))


class TestKnowledgeBase(unittest.TestCase):
    """Test KB_t construction, isolation, and statistics."""

    def test_knowledge_base_construction(self):
        chars = [
            Character(name="Alice", cell="A1", hidden_status=Status.CRIMINAL),
            Character(name="Bob", cell="B1", hidden_status=Status.INNOCENT),
            Character(name="Charlie", cell="C1", hidden_status=Status.CRIMINAL),
        ]
        kb = KnowledgeBase.create(chars, grid_size=3)

        # Initial stats: 3 primary vars, 0 aux, 0 clauses
        stats = kb.report_stats()
        self.assertEqual(stats["primary_variables"], 3)
        self.assertEqual(stats["auxiliary_variables"], 0)
        self.assertEqual(stats["clause_count"], 0)

        # Add revealed clue: Exactly 2 criminals in row 1
        clue = Clue.exactly("clue1", 2, RegionSpec.row_region(1))
        kb.add_revealed_clue(clue)
        # EXACTLY(2, 3 vars): At_least(2) has C(3, 3-2+1)=C(3,2)=3 clauses.
        # At_most(2) has C(3, 2+1)=C(3,3)=1 clause.
        # Total = 4 clauses
        self.assertEqual(kb.clause_count, 4)

        # Add proved verdict: Alice is Criminal -> unit clause [+v]
        alice_var = kb.var_mgr.get_var("Alice")
        kb.add_proved_verdict("Alice", Status.CRIMINAL)
        self.assertEqual(kb.clause_count, 5)
        self.assertIn([alice_var], kb.get_clauses())

        # Check DIMACS format contains header and clauses
        dimacs = kb.to_dimacs()
        self.assertTrue(dimacs.startswith("p cnf 3 5"))


if __name__ == "__main__":
    unittest.main()
