"""Automatic Logical Representation and CNF Encoder for Griductive.

Converts structured clues and proved verdicts into Conjunctive Normal Form (CNF)
formulas with deterministic variable mapping and cardinality encodings.
"""

from itertools import combinations
from typing import List, Dict, Set, Optional, Tuple, Union, Any
from .types import Status, ClueType, CompareOp, COLS
from .model import Clue, Character, CellCoord, RegionSpec
from .regions import RegionResolver


class VarManager:
    """Manages deterministic mapping between character/cell identifiers and integer propositional variables.
    
    Supports two ordering strategies:
    1. "row_major" (Default for solver, benchmark & team tools):
       cell_index = (row - 1) * N + col
       var = cell_index + 1
       For 3x3: A1=1, B1=2, C1=3, A2=4, B2=5, C2=6, A3=7, B3=8, C3=9.
    2. "alpha" (Alphabetical by display name, per project specification when names are given):
       Sort characters by (name.lower(), row, col).
    
    Auxiliary variables (if introduced) are strictly separated and numbered > num_primary.
    """

    def __init__(
        self,
        characters: Optional[List[Character]] = None,
        grid_size: Optional[int] = None,
        order: str = "auto",
    ):
        """Initialize deterministic mapping."""
        # Determine grid size
        if grid_size is None:
            if characters:
                max_r = max(CellCoord.from_str(c.cell).row for c in characters)
                max_c = max(CellCoord.from_str(c.cell).col + 1 for c in characters)
                grid_size = max(max_r, max_c)
            else:
                grid_size = 3
        self.N = grid_size

        self.name_to_var: Dict[str, int] = {}
        self.cell_to_var: Dict[str, int] = {}
        self.var_to_cell: Dict[int, str] = {}
        self.var_to_name: Dict[int, str] = {}
        self._aux_descriptions: Dict[int, str] = {}

        use_alpha = False
        if order == "alpha":
            use_alpha = True
        elif order == "auto":
            # If characters provided and any character's name is not its cell coordinate, use alpha
            if characters and any(ch.name.upper() != ch.cell.upper() for ch in characters):
                use_alpha = True

        if use_alpha and characters:
            # 1. Alphabetical by display name
            sorted_chars = sorted(
                characters,
                key=lambda c: (c.name.lower(), CellCoord.from_str(c.cell).row, CellCoord.from_str(c.cell).col),
            )
            for idx, ch in enumerate(sorted_chars, start=1):
                cid = ch.cell.upper()
                self.name_to_var[ch.name.lower()] = idx
                self.cell_to_var[cid] = idx
                self.var_to_cell[idx] = cid
                self.var_to_name[idx] = ch.name

            self._num_primary: int = len(sorted_chars)
        else:
            # 2. Standard Row-Major Primary Variable Assignment
            self._num_primary = self.N * self.N
            for r in range(1, self.N + 1):
                for c in range(self.N):
                    cid = f"{COLS[c]}{r}"
                    idx = (r - 1) * self.N + c
                    var = idx + 1
                    self.cell_to_var[cid] = var
                    self.var_to_cell[var] = cid
                    self.var_to_name[var] = cid

            if characters:
                for ch in characters:
                    cid = ch.cell.upper()
                    if cid in self.cell_to_var:
                        var = self.cell_to_var[cid]
                        self.name_to_var[ch.name.lower()] = var
                        self.var_to_name[var] = ch.name

        self._next_aux_var: int = self._num_primary + 1

    @classmethod
    def from_grid_size(cls, N: int) -> "VarManager":
        """Create a default row-major VarManager for an N x N grid."""
        return cls(characters=None, grid_size=N, order="row_major")

    @property
    def primary_var_count(self) -> int:
        """Return the number of primary propositional variables."""
        return self._num_primary

    @property
    def aux_var_count(self) -> int:
        """Return the number of allocated auxiliary variables."""
        return self._next_aux_var - self._num_primary - 1

    @property
    def total_var_count(self) -> int:
        """Return the total number of variables (primary + auxiliary)."""
        return self._next_aux_var - 1

    def allocate_aux_var(self, description: str = "") -> int:
        """Allocate a fresh auxiliary variable strictly distinct from primary variables."""
        var = self._next_aux_var
        self._next_aux_var += 1
        if description:
            self._aux_descriptions[var] = description
        return var

    def get_var(self, identifier: str) -> int:
        """Retrieve variable ID by character name or cell identifier (e.g. 'A1' or 'Mara')."""
        key = identifier.strip()
        cell_key = key.upper()
        if cell_key in self.cell_to_var:
            return self.cell_to_var[cell_key]
        name_key = key.lower()
        if name_key in self.name_to_var:
            return self.name_to_var[name_key]
        raise KeyError(f"Identifier '{identifier}' not found in variable mapping.")

    def get_literal_for_char(self, identifier: str, is_criminal: bool = True) -> int:
        """Return literal: +v if is_criminal=True (C_i), -v if False (~C_i)."""
        v = self.get_var(identifier)
        return v if is_criminal else -v

    def format_literal(self, lit: int) -> str:
        """Return human-readable representation of a literal."""
        var = abs(lit)
        sign = "" if lit > 0 else "~"
        if var <= self._num_primary:
            name = self.var_to_name.get(var, self.var_to_cell.get(var, str(var)))
            cell = self.var_to_cell.get(var, "")
            label = f"{cell}_{name}" if name != cell else cell
            return f"{sign}C[{label}]"
        else:
            desc = self._aux_descriptions.get(var, "")
            return f"{sign}Aux_{var}{(':' + desc) if desc else ''}"

    def format_clause(self, clause: List[int]) -> str:
        """Return human-readable string for a CNF clause."""
        if not clause:
            return "FALSE (empty clause)"
        return "(" + " | ".join(self.format_literal(lit) for lit in clause) + ")"


class CNFFormula:
    """Represents a formula in Conjunctive Normal Form (list of clauses)."""

    def __init__(self, clauses: Optional[List[List[int]]] = None):
        self.clauses: List[List[int]] = [list(c) for c in (clauses or [])]

    def add_clause(self, clause: List[int]) -> None:
        """Add a clause to the formula."""
        self.clauses.append(list(clause))

    def extend(self, other: Union["CNFFormula", List[List[int]]]) -> None:
        """Extend with clauses from another formula or clause list."""
        if isinstance(other, CNFFormula):
            self.clauses.extend([list(c) for c in other.clauses])
        else:
            self.clauses.extend([list(c) for c in other])

    @property
    def clause_count(self) -> int:
        return len(self.clauses)

    def is_satisfied_by(self, assignment: Dict[int, bool]) -> bool:
        """Check if formula is satisfied under a given assignment of variable IDs to bool."""
        for clause in self.clauses:
            clause_sat = False
            for lit in clause:
                var = abs(lit)
                if var in assignment:
                    val = assignment[var]
                    if (lit > 0 and val) or (lit < 0 and not val):
                        clause_sat = True
                        break
            if not clause_sat:
                return False
        return True

    def to_dimacs(self, total_vars: int, comments: Optional[List[str]] = None) -> str:
        """Export formula to standard DIMACS CNF format string."""
        lines = []
        if comments:
            for c in comments:
                lines.append(f"c {c}")
        lines.append(f"p cnf {total_vars} {len(self.clauses)}")
        for clause in self.clauses:
            clause_str = " ".join(str(lit) for lit in clause) + " 0"
            lines.append(clause_str)
        return "\n".join(lines) + "\n"

    def __iter__(self):
        return iter(self.clauses)

    def __len__(self):
        return len(self.clauses)

    def __repr__(self) -> str:
        return f"CNFFormula({len(self.clauses)} clauses)"


class CNFEncoder:
    """Encodes Griductive clues into Conjunctive Normal Form (CNF)."""

    def __init__(self, var_mgr: VarManager, resolver: Optional[RegionResolver] = None):
        self.var_mgr = var_mgr
        self.resolver = resolver or RegionResolver(grid_size=var_mgr.N)

    # -------------------------------------------------------------------------
    # Cardinality Encodings (Combinatorial Binomial)
    # -------------------------------------------------------------------------

    @staticmethod
    def encode_at_least_k(literals: List[int], k: int) -> List[List[int]]:
        """Encode sum(literals) >= k using direct combinatorial encoding."""
        n = len(literals)
        if k <= 0:
            return []  # Trivially satisfied
        if k > n:
            return [[]]  # Impossible -> UNSAT

        clause_size = n - k + 1
        clauses = []
        for subset in combinations(literals, clause_size):
            clauses.append(list(subset))
        return clauses

    @staticmethod
    def encode_at_most_k(literals: List[int], k: int) -> List[List[int]]:
        """Encode sum(literals) <= k using direct combinatorial encoding."""
        n = len(literals)
        if k >= n:
            return []  # Trivially satisfied
        if k < 0:
            return [[]]  # Impossible -> UNSAT

        clause_size = k + 1
        clauses = []
        for subset in combinations(literals, clause_size):
            clauses.append([-lit for lit in subset])
        return clauses

    @classmethod
    def encode_exactly_k(cls, literals: List[int], k: int) -> List[List[int]]:
        """Encode sum(literals) == k as (sum >= k) AND (sum <= k)."""
        n = len(literals)
        if k < 0 or k > n:
            return [[]]  # Impossible -> UNSAT
        if k == 0:
            return [[-lit] for lit in literals]
        if k == n:
            return [[lit] for lit in literals]

        clauses = []
        clauses.extend(cls.encode_at_least_k(literals, k))
        clauses.extend(cls.encode_at_most_k(literals, k))
        return clauses

    def _resolve_clue_literals(self, region_spec: RegionSpec, target_status: Status) -> List[int]:
        """Resolve region into list of literals corresponding to target status."""
        cells = self.resolver.resolve(region_spec)
        literals = []
        is_criminal = (target_status == Status.CRIMINAL)
        for cell_id in cells:
            v = self.var_mgr.get_var(cell_id)
            lit = v if is_criminal else -v
            literals.append(lit)
        return literals

    def encode_clue(self, clue: Union[Clue, Dict[str, Any]]) -> CNFFormula:
        """Convert any structured clue into its corresponding CNF formula."""
        if isinstance(clue, dict):
            clue = Clue.from_dict(clue)

        clue.validate()
        formula = CNFFormula()

        # 1. FACT: Person has a given status
        if clue.clue_type == ClueType.FACT:
            assert clue.person is not None and clue.status is not None
            lit = self.var_mgr.get_literal_for_char(clue.person, clue.status == Status.CRIMINAL)
            formula.add_clause([lit])
            return formula

        # 2. SAME: Two people have the same status (v1 <-> v2)
        elif clue.clue_type == ClueType.SAME:
            assert clue.person is not None and clue.person2 is not None
            v1 = self.var_mgr.get_var(clue.person)
            v2 = self.var_mgr.get_var(clue.person2)
            formula.add_clause([-v1, v2])
            formula.add_clause([v1, -v2])
            return formula

        # 3. DIFFERENT: Two people have different statuses (v1 XOR v2)
        elif clue.clue_type == ClueType.DIFFERENT:
            assert clue.person is not None and clue.person2 is not None
            v1 = self.var_mgr.get_var(clue.person)
            v2 = self.var_mgr.get_var(clue.person2)
            formula.add_clause([v1, v2])
            formula.add_clause([-v1, -v2])
            return formula

        # 4. EXACTLY: Exactly k people in region
        elif clue.clue_type == ClueType.EXACTLY:
            assert clue.region is not None and clue.k is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self.encode_exactly_k(lits, clue.k)
            formula.extend(clauses)
            return formula

        # 5. AT_LEAST: At least k people in region
        elif clue.clue_type == ClueType.AT_LEAST:
            assert clue.region is not None and clue.k is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self.encode_at_least_k(lits, clue.k)
            formula.extend(clauses)
            return formula

        # 6. AT_MOST: At most k people in region
        elif clue.clue_type == ClueType.AT_MOST:
            assert clue.region is not None and clue.k is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self.encode_at_most_k(lits, clue.k)
            formula.extend(clauses)
            return formula

        # 7. PARITY: Even / Odd count of criminals in region
        elif clue.clue_type == ClueType.PARITY:
            assert clue.region is not None and clue.parity is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self._encode_parity(lits, clue.parity)
            formula.extend(clauses)
            return formula

        # 8. COMPARE / COUNT_COMPARE: Compare counts between two regions
        elif clue.clue_type in (ClueType.COMPARE, ClueType.COUNT_COMPARE):
            assert clue.region is not None and clue.region2 is not None and clue.compare_op is not None
            lits1 = self._resolve_clue_literals(clue.region, clue.target_status)
            lits2 = self._resolve_clue_literals(clue.region2, clue.target_status)
            clauses = self._encode_count_compare(lits1, clue.compare_op, lits2)
            formula.extend(clauses)
            return formula

        # 9. ALL_SAME: All people in region have the same status
        elif clue.clue_type == ClueType.ALL_SAME:
            assert clue.region is not None
            cells = self.resolver.resolve(clue.region)
            if len(cells) > 1:
                vars_in_region = [self.var_mgr.get_var(c) for c in cells]
                for i in range(len(vars_in_region) - 1):
                    v1 = vars_in_region[i]
                    v2 = vars_in_region[i + 1]
                    formula.add_clause([-v1, v2])
                    formula.add_clause([v1, -v2])
            return formula

        raise ValueError(f"Unknown clue type: {clue.clue_type}")

    def _encode_parity(self, literals: List[int], parity: int) -> List[List[int]]:
        """Encode XOR(literals) == parity using auxiliary variables."""
        n = len(literals)
        if n == 0:
            return [] if parity == 0 else [[]]
        if n == 1:
            return [[literals[0]]] if parity == 1 else [[-literals[0]]]
        if n == 2:
            l1, l2 = literals[0], literals[1]
            if parity == 1:
                return [[l1, l2], [-l1, -l2]]
            else:
                return [[-l1, l2], [l1, -l2]]

        # Chained XOR for n >= 3
        clauses: List[List[int]] = []
        curr = literals[0]
        for i in range(1, n - 1):
            next_lit = literals[i]
            aux = self.var_mgr.allocate_aux_var(f"parity_chain_{i}")
            clauses.append([-curr, -next_lit, -aux])
            clauses.append([curr, next_lit, -aux])
            clauses.append([curr, -next_lit, aux])
            clauses.append([-curr, next_lit, aux])
            curr = aux

        last_lit = literals[n - 1]
        if parity == 1:
            clauses.append([curr, last_lit])
            clauses.append([-curr, -last_lit])
        else:
            clauses.append([-curr, last_lit])
            clauses.append([curr, -last_lit])

        return clauses

    def _encode_count_compare(self, lits1: List[int], op: CompareOp, lits2: List[int]) -> List[List[int]]:
        """Encode comparison op(sum(lits1), sum(lits2)) using indicator auxiliary variables."""
        n1 = len(lits1)
        n2 = len(lits2)
        clauses: List[List[int]] = []

        p: Dict[int, int] = {}
        for k in range(n1 + 1):
            var = self.var_mgr.allocate_aux_var(f"count1_eq_{k}")
            p[k] = var
            exact_clauses = self.encode_exactly_k(lits1, k)
            for c in exact_clauses:
                clauses.append([-var] + c)

        clauses.append(list(p.values()))

        q: Dict[int, int] = {}
        for m in range(n2 + 1):
            var = self.var_mgr.allocate_aux_var(f"count2_eq_{m}")
            q[m] = var
            exact_clauses = self.encode_exactly_k(lits2, m)
            for c in exact_clauses:
                clauses.append([-var] + c)

        clauses.append(list(q.values()))

        for k in range(n1 + 1):
            for m in range(n2 + 1):
                if not op.evaluate(k, m):
                    clauses.append([-p[k], -q[m]])

        return clauses


class KnowledgeBase:
    """Cumulative Knowledge Base ($KB_t$) at step t."""

    def __init__(self, encoder: CNFEncoder):
        self.encoder = encoder
        self.var_mgr = encoder.var_mgr
        self.formula = CNFFormula()
        self.active_clues: List[Clue] = []
        self.revealed_cells: Set[str] = set()
        self.proved_verdicts: Dict[str, Status] = {}

    @classmethod
    def create(cls, characters: List[Character], grid_size: Optional[int] = None) -> "KnowledgeBase":
        """Factory method to construct KnowledgeBase from character list."""
        var_mgr = VarManager(characters, grid_size=grid_size)
        resolver = RegionResolver(grid_size=var_mgr.N, characters=characters)
        encoder = CNFEncoder(var_mgr=var_mgr, resolver=resolver)
        return cls(encoder=encoder)

    def add_clue(self, clue: Union[Clue, Dict[str, Any]]) -> None:
        """Encode and add a revealed clue to the knowledge base."""
        if isinstance(clue, dict):
            clue = Clue.from_dict(clue)
        self.active_clues.append(clue)
        f = self.encoder.encode_clue(clue)
        self.formula.extend(f)

    def add_revealed_clue(self, clue: Union[Clue, Dict[str, Any]]) -> None:
        """Alias for add_clue."""
        self.add_clue(clue)

    def add_proved_status(self, identifier: str, status: Status) -> None:
        """Add a proved status as a unit clause to KB."""
        self.proved_verdicts[identifier.upper()] = status
        lit = self.var_mgr.get_literal_for_char(identifier, is_criminal=(status == Status.CRIMINAL))
        self.formula.add_clause([lit])

    def add_proved_verdict(self, identifier: str, status: Status) -> None:
        """Alias for add_proved_status."""
        self.add_proved_status(identifier, status)

    def report_stats(self) -> Dict[str, int]:
        """Report current variable and clause statistics."""
        return {
            "primary_variables": self.var_mgr.primary_var_count,
            "auxiliary_variables": self.var_mgr.aux_var_count,
            "total_variables": self.var_mgr.total_var_count,
            "clause_count": self.formula.clause_count,
        }

    def get_clauses(self) -> List[List[int]]:
        """Return the current list of CNF clauses."""
        return list(self.formula.clauses)

    @property
    def clause_count(self) -> int:
        return self.formula.clause_count

    @property
    def total_vars(self) -> int:
        return self.var_mgr.total_var_count

    def to_dimacs(self, comments: Optional[List[str]] = None) -> str:
        """Export KB to DIMACS string."""
        return self.formula.to_dimacs(self.var_mgr.total_var_count, comments)


def encode_clue(clue: Union[Clue, Dict[str, Any]], n: int) -> List[List[int]]:
    """Convenience helper to encode one clue into CNF clauses with DIMACS ints (row-major)."""
    var_mgr = VarManager.from_grid_size(n)
    encoder = CNFEncoder(var_mgr=var_mgr)
    formula = encoder.encode_clue(clue)
    return formula.clauses
