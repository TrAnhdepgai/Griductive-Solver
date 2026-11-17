"""Type definitions, enumerations, and constants for Griductive Solver."""

from enum import Enum
from typing import Literal


class Status(str, Enum):
    """Hidden or proved status of a character."""
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"

    def opposite(self) -> "Status":
        """Return the opposite status."""
        return Status.INNOCENT if self == Status.CRIMINAL else Status.CRIMINAL

    def to_bool(self) -> bool:
        """Convention: Criminal = True, Innocent = False (matches C_i boolean variable)."""
        return self == Status.CRIMINAL

    @classmethod
    def from_bool(cls, val: bool) -> "Status":
        """Convert boolean value (C_i) to Status."""
        return cls.CRIMINAL if val else cls.INNOCENT

    def __repr__(self) -> str:
        return self.value


class ClueType(str, Enum):
    """Supported clue templates, including core language and extensions."""
    # Core templates (Section 3.2)
    FACT = "FACT"
    SAME = "SAME"
    DIFFERENT = "DIFFERENT"
    EXACTLY = "EXACTLY"
    AT_LEAST = "AT_LEAST"
    AT_MOST = "AT_MOST"

    # Extensions (Section 3.2 & 4.2)
    PARITY = "PARITY"
    COUNT_COMPARE = "COUNT_COMPARE"
    ALL_SAME = "ALL_SAME"


class RegionType(str, Enum):
    """Types of regions supported for counting and relation clues."""
    # Core regions
    ROW = "ROW"
    COL = "COL"
    NEIGHBORS = "NEIGHBORS"
    EXPLICIT = "EXPLICIT"

    # Extension regions
    CORNERS = "CORNERS"
    BOUNDARY = "BOUNDARY"
    INTERIOR = "INTERIOR"
    COMMON_NEIGHBORS = "COMMON_NEIGHBORS"
    BETWEEN = "BETWEEN"
    INTERSECTION = "INTERSECTION"
    UNION = "UNION"
    DIFFERENCE = "DIFFERENCE"


class Verdict(str, Enum):
    """Result of entailment queries or game move submissions."""
    CRIMINAL = "CRIMINAL"
    INNOCENT = "INNOCENT"
    UNKNOWN = "UNKNOWN"
    INCONSISTENT = "INCONSISTENT"
    NOT_PROVABLE = "NOT_PROVABLE"
    CONTRADICTED = "CONTRADICTED"


class CompareOp(str, Enum):
    """Comparison operators for count comparison extension."""
    EQ = "=="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="

    def evaluate(self, left: int, right: int) -> bool:
        """Evaluate operator on two integer counts."""
        if self == CompareOp.EQ:
            return left == right
        elif self == CompareOp.NE:
            return left != right
        elif self == CompareOp.GT:
            return left > right
        elif self == CompareOp.GE:
            return left >= right
        elif self == CompareOp.LT:
            return left < right
        elif self == CompareOp.LE:
            return left <= right
        raise ValueError(f"Unknown compare operator: {self}")


class ParityType(int, Enum):
    """Parity values for parity extension."""
    EVEN = 0
    ODD = 1
