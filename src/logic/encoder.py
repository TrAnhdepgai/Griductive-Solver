"""Automatic Logical Representation and CNF Encoder for Griductive.

Converts structured clues and proved verdicts into Conjunctive Normal Form (CNF)
formulas with deterministic variable mapping and cardinality encodings.
"""

from itertools import combinations
from typing import List, Dict, Set, Optional, Tuple, Union
from .types import Status, ClueType, CompareOp
from .model import Clue, Character, CellCoord
from .regions import RegionResolver


class VarManager:
    """Manages deterministic mapping between character identifiers and integer propositional variables.
    
    Primary variables represent:
        C_i = True if character i is Criminal, False if Innocent.
    Primary variables are numbered 1 to M.
    Auxiliary variables (if introduced) are strictly separated and numbered M + 1, M + 2, ...
    """

    def __init__(self, characters: List[Character], grid_size: Optional[int] = None):
        """Initialize deterministic mapping from characters.
        
        Ordering follows project specification:
        Characters are sorted alphabetically by display name (or by cell coordinate as tie-breaker).
        """
        # Determine unique characters and sort deterministically
        # Sort key: primary is display name (case-insensitive), secondary is cell coordinate
        sorted_chars = sorted(
            characters,
            key=lambda c: (c.name.lower(), CellCoord.from_str(c.cell).row, CellCoord.from_str(c.cell).col)
        )

        self.name_to_var: Dict[str, int] = {}
        self.cell_to_var: Dict[str, int] = {}
        self.var_to_cell: Dict[int, str] = {}
        self.var_to_name: Dict[int, str] = {}

        for idx, ch in enumerate(sorted_chars, start=1):
            cell_id = ch.cell.upper()
            self.name_to_var[ch.name.lower()] = idx
            self.cell_to_var[cell_id] = idx
            self.var_to_cell[idx] = cell_id
            self.var_to_name[idx] = ch.name

        self._num_primary: int = len(sorted_chars)
        self._next_aux_var: int = self._num_primary + 1
        self._aux_descriptions: Dict[int, str] = {}

    @classmethod
    def from_grid_size(cls, N: int) -> "VarManager":
        """Create a default VarManager for an N x N grid when character names are coordinates."""
        chars = []
        for r in range(1, N + 1):
            for c in range(N):
                coord = CellCoord(row=r, col=c)
                chars.append(Character(name=coord.cell_id, cell=coord.cell_id))
        return cls(chars, grid_size=N)

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
        """Check whether the formula is satisfied by an integer literal assignment."""
        for clause in self.clauses:
            clause_sat = False
            for lit in clause:
                var = abs(lit)
                if var in assignment:
                    val = assignment[var]
                    lit_val = val if lit > 0 else not val
                    if lit_val:
                        clause_sat = True
                        break
            if not clause_sat:
                return False
        return True

    def to_dimacs(self, total_vars: Optional[int] = None) -> str:
        """Export formula to standard DIMACS CNF format string."""
        max_var = 0
        for clause in self.clauses:
            for lit in clause:
                max_var = max(max_var, abs(lit))
        num_vars = max(max_var, total_vars or 0)
        lines = [f"p cnf {num_vars} {len(self.clauses)}"]
        for clause in self.clauses:
            lines.append(" ".join(str(lit) for lit in clause) + " 0")
        return "\n".join(lines)


class CNFEncoder:
    """Encodes structured clues and game verdicts into CNF."""

    def __init__(self, var_mgr: VarManager, resolver: RegionResolver):
        self.var_mgr = var_mgr
        self.resolver = resolver

    # -------------------------------------------------------------------------
    # Cardinality Encoding Primitives (Combinatorial / Binomial)
    # -------------------------------------------------------------------------

    @staticmethod
    def encode_at_least_k(literals: List[int], k: int) -> List[List[int]]:
        """Encode sum(literals) >= k using direct combinatorial encoding.
        
        To have at least k true literals out of n, no subset of size (n - k + 1)
        can be all false. Therefore, every subset of size (n - k + 1) must contain
        at least one true literal.
        """
        n = len(literals)
        if k <= 0:
            return []  # Trivially satisfied
        if k > n:
            return [[]]  # Impossible -> empty clause is UNSAT

        clause_size = n - k + 1
        clauses = []
        for subset in combinations(literals, clause_size):
            clauses.append(list(subset))
        return clauses

    @staticmethod
    def encode_at_most_k(literals: List[int], k: int) -> List[List[int]]:
        """Encode sum(literals) <= k using direct combinatorial encoding.
        
        To have at most k true literals out of n, no subset of size (k + 1)
        can be all true. Therefore, for every subset of size (k + 1), at least
        one literal must be false (negated).
        """
        n = len(literals)
        if k >= n:
            return []  # Trivially satisfied
        if k < 0:
            return [[]]  # Impossible -> empty clause is UNSAT

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
            # All literals must be false
            return [[-lit] for lit in literals]
        if k == n:
            # All literals must be true
            return [[lit] for lit in literals]

        clauses = []
        clauses.extend(cls.encode_at_least_k(literals, k))
        clauses.extend(cls.encode_at_most_k(literals, k))
        return clauses

    # -------------------------------------------------------------------------
    # Sequential Counter Cardinality Encoding (Alternative with Aux Vars)
    # -------------------------------------------------------------------------

    def encode_at_most_k_sequential(self, literals: List[int], k: int) -> Tuple[List[List[int]], List[int]]:
        """Encode sum(literals) <= k using Sinz's sequential counter encoding.
        
        Introduces (n-1)*k auxiliary variables s_{i, j} representing prefix sums >= j.
        Returns: (clauses, auxiliary_variables_allocated).
        """
        n = len(literals)
        if k >= n:
            return [], []
        if k < 0:
            return [[]], []
        if k == 0:
            return [[-lit] for lit in literals], []

        aux_vars: List[int] = []
        # s[i][j] for i in 0..n-2 (items 0..n-2), j in 0..k-1 (representing sum >= j+1)
        s: Dict[Tuple[int, int], int] = {}
        for i in range(n - 1):
            for j in range(k):
                var = self.var_mgr.allocate_aux_var(f"seq_counter_{i}_{j+1}")
                s[(i, j)] = var
                aux_vars.append(var)

        clauses: List[List[int]] = []

        # 1. Base item 0
        clauses.append([-literals[0], s[(0, 0)]])
        for j in range(1, k):
            clauses.append([-s[(0, j)]])

        # 2. Intermediate items 1..n-2
        for i in range(1, n - 1):
            # literals[i] -> s[i][0]
            clauses.append([-literals[i], s[(i, 0)]])
            # s[i-1][0] -> s[i][0]
            clauses.append([-s[(i - 1, 0)], s[(i, 0)]])

            for j in range(1, k):
                # literals[i] and s[i-1][j-1] -> s[i][j]
                clauses.append([-literals[i], -s[(i - 1, j - 1)], s[(i, j)]])
                # s[i-1][j] -> s[i][j]
                clauses.append([-s[(i - 1, j)], s[(i, j)]])

            # overflow prevention: cannot have literals[i] and s[i-1][k-1]
            clauses.append([-literals[i], -s[(i - 1, k - 1)]])

        # 3. Final item n-1
        clauses.append([-literals[n - 1], -s[(n - 2, k - 1)]])

        return clauses, aux_vars

    # -------------------------------------------------------------------------
    # Core Clue Template Encoding
    # -------------------------------------------------------------------------

    def _resolve_clue_literals(self, region_spec, target_status: Status) -> List[int]:
        """Resolve region into list of literals corresponding to target status."""
        cells = self.resolver.resolve(region_spec)
        literals = []
        is_criminal = (target_status == Status.CRIMINAL)
        for cell_id in cells:
            v = self.var_mgr.get_var(cell_id)
            lit = v if is_criminal else -v
            literals.append(lit)
        return literals

    def encode_clue(self, clue: Clue) -> CNFFormula:
        """Convert any structured clue into its corresponding CNF formula.
        
        Validates clue parameters before encoding.
        """
        clue.validate()
        formula = CNFFormula()

        # 1. FACT: Person has a given status (Ci or ~Ci)
        if clue.clue_type == ClueType.FACT:
            assert clue.person is not None and clue.status is not None
            lit = self.var_mgr.get_literal_for_char(clue.person, clue.status == Status.CRIMINAL)
            formula.add_clause([lit])
            return formula

        # 2. SAME: Two named people have the same status (Ci <-> Cj)
        elif clue.clue_type == ClueType.SAME:
            assert clue.person is not None and clue.person2 is not None
            v1 = self.var_mgr.get_var(clue.person)
            v2 = self.var_mgr.get_var(clue.person2)
            # (~v1 | v2) & (v1 | ~v2)
            formula.add_clause([-v1, v2])
            formula.add_clause([v1, -v2])
            return formula

        # 3. DIFFERENT: Two named people have different statuses (Ci XOR Cj)
        elif clue.clue_type == ClueType.DIFFERENT:
            assert clue.person is not None and clue.person2 is not None
            v1 = self.var_mgr.get_var(clue.person)
            v2 = self.var_mgr.get_var(clue.person2)
            # (v1 | v2) & (~v1 | ~v2)
            formula.add_clause([v1, v2])
            formula.add_clause([-v1, -v2])
            return formula

        # 4. EXACTLY: Exactly k people in region have target status
        elif clue.clue_type == ClueType.EXACTLY:
            assert clue.region is not None and clue.k is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self.encode_exactly_k(lits, clue.k)
            formula.extend(clauses)
            return formula

        # 5. AT_LEAST: At least k people in region have target status
        elif clue.clue_type == ClueType.AT_LEAST:
            assert clue.region is not None and clue.k is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self.encode_at_least_k(lits, clue.k)
            formula.extend(clauses)
            return formula

        # 6. AT_MOST: At most k people in region have target status
        elif clue.clue_type == ClueType.AT_MOST:
            assert clue.region is not None and clue.k is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self.encode_at_most_k(lits, clue.k)
            formula.extend(clauses)
            return formula

        # ---------------------------------------------------------------------
        # Extensions
        # ---------------------------------------------------------------------

        # Extension: PARITY
        elif clue.clue_type == ClueType.PARITY:
            assert clue.region is not None and clue.parity is not None
            lits = self._resolve_clue_literals(clue.region, clue.target_status)
            clauses = self._encode_parity(lits, clue.parity)
            formula.extend(clauses)
            return formula

        # Extension: COUNT_COMPARE
        elif clue.clue_type == ClueType.COUNT_COMPARE:
            assert clue.region is not None and clue.region2 is not None and clue.compare_op is not None
            lits1 = self._resolve_clue_literals(clue.region, clue.target_status)
            lits2 = self._resolve_clue_literals(clue.region2, clue.target_status)
            clauses = self._encode_count_compare(lits1, clue.compare_op, lits2)
            formula.extend(clauses)
            return formula

        # Extension: ALL_SAME
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

        raise ValueError(f"Unknown or unhandled clue type: {clue.clue_type}")

    def _encode_parity(self, literals: List[int], parity: int) -> List[List[int]]:
        """Encode XOR(literals) == parity using auxiliary variables for linear size."""
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

        # For n >= 3: chain xor: aux_1 = l1 ^ l2; aux_2 = aux_1 ^ l3 ...
        clauses: List[List[int]] = []
        curr = literals[0]
        for i in range(1, n - 1):
            next_lit = literals[i]
            aux = self.var_mgr.allocate_aux_var(f"parity_chain_{i}")
            # aux <-> curr ^ next_lit
            # CNF for a = (b ^ c):
            clauses.append([-curr, -next_lit, -aux])
            clauses.append([curr, next_lit, -aux])
            clauses.append([curr, -next_lit, aux])
            clauses.append([-curr, next_lit, aux])
            curr = aux

        # Final step with last literal literals[n-1] and required parity
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

        # Create indicator variable p[k] for (sum(lits1) == k)
        p: Dict[int, int] = {}
        for k in range(n1 + 1):
            var = self.var_mgr.allocate_aux_var(f"count1_eq_{k}")
            p[k] = var
            # p[k] -> (sum == k)
            exact_clauses = self.encode_exactly_k(lits1, k)
            for c in exact_clauses:
                clauses.append([-var] + c)

        # sum(lits1) must take at least one value
        clauses.append(list(p.values()))

        # Create indicator variable q[m] for (sum(lits2) == m)
        q: Dict[int, int] = {}
        for m in range(n2 + 1):
            var = self.var_mgr.allocate_aux_var(f"count2_eq_{m}")
            q[m] = var
            exact_clauses = self.encode_exactly_k(lits2, m)
            for c in exact_clauses:
                clauses.append([-var] + c)

        clauses.append(list(q.values()))

        # For every pair (k, m) that violates the operator: cannot have p[k] and q[m] both true
        for k in range(n1 + 1):
            for m in range(n2 + 1):
                if not op.evaluate(k, m):
                    clauses.append([-p[k], -q[m]])

        return clauses


class KnowledgeBase:
    """Represents the current deduction state KB_t at deduction step t.
    
    KB_t = CNF(revealed clues) ^ (unit clauses for proved verdicts).
    
    CRITICAL CONSTRAINT: Hidden statuses and unrevealed clues must NOT be included in KB_t.
    """

    def __init__(self, var_mgr: VarManager, encoder: CNFEncoder):
        self.var_mgr = var_mgr
        self.encoder = encoder
        self.formula = CNFFormula()
        self.revealed_clues: List[Clue] = []
        self.proved_verdicts: Dict[str, Status] = {}

    @classmethod
    def create(cls, characters: List[Character], grid_size: Optional[int] = None) -> "KnowledgeBase":
        """Factory method to initialize KnowledgeBase for a set of characters."""
        N = grid_size or max(len(characters), 1)
        # If characters have cells, infer grid dimension
        if characters:
            max_r = max(CellCoord.from_str(c.cell).row for c in characters)
            max_c = max(CellCoord.from_str(c.cell).col + 1 for c in characters)
            N = max(max_r, max_c, N)
        resolver = RegionResolver(grid_size=N, characters=characters)
        var_mgr = VarManager(characters=characters, grid_size=N)
        encoder = CNFEncoder(var_mgr=var_mgr, resolver=resolver)
        return cls(var_mgr=var_mgr, encoder=encoder)

    def add_revealed_clue(self, clue: Clue) -> CNFFormula:
        """Add a newly revealed clue to KB_t."""
        clue_formula = self.encoder.encode_clue(clue)
        self.formula.extend(clue_formula)
        self.revealed_clues.append(clue)
        return clue_formula

    def add_proved_verdict(self, identifier: str, status: Status) -> int:
        """Add a proved verdict as a unit clause to KB_t.
        
        Returns the added unit literal (+v for Criminal, -v for Innocent).
        """
        lit = self.var_mgr.get_literal_for_char(identifier, is_criminal=(status == Status.CRIMINAL))
        self.formula.add_clause([lit])
        canonical_cell = self.encoder.resolver.normalize_person_to_cell(identifier)
        self.proved_verdicts[canonical_cell] = status
        return lit

    def get_clauses(self) -> List[List[int]]:
        """Return a copy of the current CNF clauses."""
        return [list(c) for c in self.formula.clauses]

    @property
    def primary_var_count(self) -> int:
        """Number of primary propositional variables."""
        return self.var_mgr.primary_var_count

    @property
    def aux_var_count(self) -> int:
        """Number of auxiliary variables introduced."""
        return self.var_mgr.aux_var_count

    @property
    def total_var_count(self) -> int:
        """Total variables (primary + auxiliary)."""
        return self.var_mgr.total_var_count

    @property
    def clause_count(self) -> int:
        """Total number of clauses in KB_t."""
        return self.formula.clause_count

    def report_stats(self) -> Dict[str, int]:
        """Report variable and clause counts as required by Section 4.2."""
        return {
            "primary_variables": self.primary_var_count,
            "auxiliary_variables": self.aux_var_count,
            "total_variables": self.total_var_count,
            "clause_count": self.clause_count,
            "revealed_clues_count": len(self.revealed_clues),
            "proved_verdicts_count": len(self.proved_verdicts),
        }

    def to_dimacs(self) -> str:
        """Export current KB_t to DIMACS CNF format string."""
        return self.formula.to_dimacs(total_vars=self.total_var_count)
