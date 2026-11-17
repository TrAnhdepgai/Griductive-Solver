"""Data models for Griductive: Cell coordinates, Character, RegionSpec, Clue, and Puzzle."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict, Any, Union
from .types import Status, ClueType, RegionType, CompareOp, ParityType, COLS


@dataclass(frozen=True, order=True)
class CellCoord:
    """Coordinate representing a grid cell (e.g. C2 -> col='C', row=2).
    
    Rows are 1-indexed (1 to N, top to bottom).
    Columns are 0-indexed integers internally (0 to N-1), represented as uppercase letters A, B, C...
    """
    row: int
    col: int

    @property
    def col_letter(self) -> str:
        """Return the column as an uppercase letter ('A', 'B', 'C', ...)."""
        return COLS[self.col] if 0 <= self.col < len(COLS) else chr(ord('A') + self.col)

    @property
    def cell_id(self) -> str:
        """Return canonical string identifier, e.g., 'C2'."""
        return f"{self.col_letter}{self.row}"

    @classmethod
    def from_str(cls, s: str) -> "CellCoord":
        """Parse cell coordinate string like 'C2', 'a1', 'B12'."""
        s = s.strip().upper()
        if not s or not s[0].isalpha() or not s[1:].isdigit():
            raise ValueError(f"Invalid cell coordinate format: '{s}'. Expected format like 'C2'.")
        col = ord(s[0]) - ord('A')
        row = int(s[1:])
        return cls(row=row, col=col)

    def is_valid(self, N: int) -> bool:
        """Check if coordinate lies within an N x N grid."""
        return 1 <= self.row <= N and 0 <= self.col < N

    def is_neighbor(self, other: "CellCoord") -> bool:
        """Check 8-connectivity (Chebyshev distance == 1, self excluded)."""
        if self == other:
            return False
        return max(abs(self.row - other.row), abs(self.col - other.col)) == 1

    def __str__(self) -> str:
        return self.cell_id

    def __repr__(self) -> str:
        return f"CellCoord({self.cell_id})"


@dataclass
class RegionSpec:
    """Specification of a clue region."""
    region_type: RegionType
    row: Optional[int] = None
    col: Optional[str] = None
    cell: Optional[str] = None
    cells: Optional[List[str]] = None
    cell1: Optional[str] = None
    cell2: Optional[str] = None
    sub_regions: Optional[List["RegionSpec"]] = None

    @classmethod
    def row_region(cls, row_num: int) -> "RegionSpec":
        return cls(region_type=RegionType.ROW, row=row_num)

    @classmethod
    def col_region(cls, col_letter: str) -> "RegionSpec":
        return cls(region_type=RegionType.COL, col=col_letter.upper())

    @classmethod
    def neighbors_region(cls, cell_id: str) -> "RegionSpec":
        return cls(region_type=RegionType.NEIGHBORS, cell=cell_id.upper())

    @classmethod
    def explicit_region(cls, cells: List[str]) -> "RegionSpec":
        return cls(region_type=RegionType.EXPLICIT, cells=[c.upper() for c in cells])

    @classmethod
    def corners(cls) -> "RegionSpec":
        return cls(region_type=RegionType.CORNERS)

    @classmethod
    def boundary(cls) -> "RegionSpec":
        return cls(region_type=RegionType.BOUNDARY)

    @classmethod
    def interior(cls) -> "RegionSpec":
        return cls(region_type=RegionType.INTERIOR)

    @classmethod
    def common_neighbors(cls, c1: str, c2: str) -> "RegionSpec":
        return cls(region_type=RegionType.COMMON_NEIGHBORS, cell1=c1.upper(), cell2=c2.upper())

    @classmethod
    def between(cls, c1: str, c2: str) -> "RegionSpec":
        return cls(region_type=RegionType.BETWEEN, cell1=c1.upper(), cell2=c2.upper())

    @classmethod
    def intersection(cls, r1: "RegionSpec", r2: "RegionSpec") -> "RegionSpec":
        return cls(region_type=RegionType.INTERSECTION, sub_regions=[r1, r2])

    @classmethod
    def union(cls, r1: "RegionSpec", r2: "RegionSpec") -> "RegionSpec":
        return cls(region_type=RegionType.UNION, sub_regions=[r1, r2])

    @classmethod
    def difference(cls, r1: "RegionSpec", r2: "RegionSpec") -> "RegionSpec":
        return cls(region_type=RegionType.DIFFERENCE, sub_regions=[r1, r2])

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict representation (supporting both kind and region_type)."""
        d: Dict[str, Any] = {"region_type": self.region_type.value}
        if self.row is not None:
            d["row"] = self.row
        if self.col is not None:
            d["col"] = self.col
        if self.cell is not None:
            d["cell"] = self.cell
        if self.cells is not None:
            d["cells"] = self.cells
        if self.cell1 is not None:
            d["cell1"] = self.cell1
        if self.cell2 is not None:
            d["cell2"] = self.cell2
        if self.sub_regions is not None:
            d["sub_regions"] = [r.to_dict() for r in self.sub_regions]
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RegionSpec":
        """Parse RegionSpec supporting both member D schema ('kind') and logic-core schema ('region_type')."""
        if "kind" in data:
            kind = data["kind"].lower()
            if kind == "row":
                return cls(region_type=RegionType.ROW, row=data["row"])
            elif kind == "column":
                return cls(region_type=RegionType.COL, col=data["col"].upper())
            elif kind == "neighbors":
                cell_of = data.get("of") or data.get("cell")
                return cls(region_type=RegionType.NEIGHBORS, cell=cell_of.upper())
            elif kind == "cells":
                return cls(region_type=RegionType.EXPLICIT, cells=[c.upper() for c in data["cells"]])
            elif kind in ("corners", "boundary", "interior"):
                return cls(region_type=RegionType(kind.upper()))
            elif kind == "common_neighbors":
                return cls(region_type=RegionType.COMMON_NEIGHBORS, cell1=data["cell1"].upper(), cell2=data["cell2"].upper())
            elif kind == "between":
                return cls(region_type=RegionType.BETWEEN, cell1=data["cell1"].upper(), cell2=data["cell2"].upper())
            elif kind in ("intersection", "union", "difference"):
                sub_regs = [cls.from_dict(r) for r in data.get("sub_regions", [])]
                return cls(region_type=RegionType(kind.upper()), sub_regions=sub_regs)
            raise ValueError(f"Unknown region kind: {kind}")

        # Logic-core format
        sub_regions = None
        if "sub_regions" in data and data["sub_regions"]:
            sub_regions = [cls.from_dict(r) for r in data["sub_regions"]]
        r_type = RegionType(data["region_type"].upper())
        return cls(
            region_type=r_type,
            row=data.get("row"),
            col=data.get("col").upper() if data.get("col") else None,
            cell=data.get("cell").upper() if data.get("cell") else None,
            cells=[c.upper() for c in data["cells"]] if data.get("cells") else None,
            cell1=data.get("cell1").upper() if data.get("cell1") else None,
            cell2=data.get("cell2").upper() if data.get("cell2") else None,
            sub_regions=sub_regions,
        )


@dataclass
class Clue:
    """Structured representation of a clue."""
    clue_id: str
    clue_type: ClueType
    person: Optional[str] = None
    person2: Optional[str] = None
    status: Optional[Status] = None
    region: Optional[RegionSpec] = None
    k: Optional[int] = None
    target_status: Status = Status.CRIMINAL
    parity: Optional[int] = None
    compare_op: Optional[CompareOp] = None
    region2: Optional[RegionSpec] = None
    text: str = ""

    def validate(self) -> None:
        """Validate that all required parameters are present and consistent."""
        if not self.clue_id:
            # Default ID if omitted
            self.clue_id = f"clue_{self.clue_type.value}"

        if self.clue_type == ClueType.FACT:
            if not self.person:
                raise ValueError(f"FACT clue requires 'person' or 'cell'.")
            if self.status is None:
                raise ValueError(f"FACT clue requires 'status'.")

        elif self.clue_type in (ClueType.SAME, ClueType.DIFFERENT):
            if not self.person or not self.person2:
                raise ValueError(f"{self.clue_type.value} clue requires two cells (a, b).")

        elif self.clue_type in (ClueType.EXACTLY, ClueType.AT_LEAST, ClueType.AT_MOST):
            if self.region is None:
                raise ValueError(f"{self.clue_type.value} clue requires 'region'.")
            if self.k is None:
                raise ValueError(f"{self.clue_type.value} clue requires integer 'k'.")
            if self.k < 0:
                raise ValueError(f"{self.clue_type.value} clue requires k >= 0.")

        elif self.clue_type == ClueType.PARITY:
            if self.region is None:
                raise ValueError(f"PARITY clue requires 'region'.")
            if self.parity is None or self.parity not in (0, 1):
                raise ValueError(f"PARITY clue requires parity in (0, 1).")

        elif self.clue_type in (ClueType.COUNT_COMPARE, ClueType.COMPARE):
            if self.region is None or self.region2 is None:
                raise ValueError(f"COMPARE clue requires two regions ('left'/'region' and 'right'/'region2').")
            if self.compare_op is None:
                raise ValueError(f"COMPARE clue requires 'compare_op' or 'op'.")

    # Factory methods
    @classmethod
    def fact(cls, clue_id: str, person: str, status: Status, text: str = "") -> "Clue":
        c = cls(clue_id=clue_id, clue_type=ClueType.FACT, person=person, status=status, text=text)
        c.validate()
        return c

    @classmethod
    def same(cls, clue_id: str, p1: str, p2: str, text: str = "") -> "Clue":
        c = cls(clue_id=clue_id, clue_type=ClueType.SAME, person=p1, person2=p2, text=text)
        c.validate()
        return c

    @classmethod
    def different(cls, clue_id: str, p1: str, p2: str, text: str = "") -> "Clue":
        c = cls(clue_id=clue_id, clue_type=ClueType.DIFFERENT, person=p1, person2=p2, text=text)
        c.validate()
        return c

    @classmethod
    def exactly(cls, clue_id: str, k: int, region: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> "Clue":
        c = cls(clue_id=clue_id, clue_type=ClueType.EXACTLY, k=k, region=region, target_status=target_status, text=text)
        c.validate()
        return c

    @classmethod
    def at_least(cls, clue_id: str, k: int, region: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> "Clue":
        c = cls(clue_id=clue_id, clue_type=ClueType.AT_LEAST, k=k, region=region, target_status=target_status, text=text)
        c.validate()
        return c

    @classmethod
    def at_most(cls, clue_id: str, k: int, region: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> "Clue":
        c = cls(clue_id=clue_id, clue_type=ClueType.AT_MOST, k=k, region=region, target_status=target_status, text=text)
        c.validate()
        return c

    @classmethod
    def parity_clue(cls, clue_id: str, parity: Union[int, str], region: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> "Clue":
        par_val = ParityType.from_val(parity).to_int()
        c = cls(clue_id=clue_id, clue_type=ClueType.PARITY, parity=par_val, region=region, target_status=target_status, text=text)
        c.validate()
        return c

    @classmethod
    def count_compare(cls, clue_id: str, region1: RegionSpec, op: Union[CompareOp, str], region2: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> "Clue":
        compare_op = CompareOp.from_str(op) if isinstance(op, str) else op
        c = cls(clue_id=clue_id, clue_type=ClueType.COMPARE, region=region1, compare_op=compare_op, region2=region2, target_status=target_status, text=text)
        c.validate()
        return c

    @classmethod
    def all_same(cls, clue_id: str, region: RegionSpec, text: str = "") -> "Clue":
        c = cls(clue_id=clue_id, clue_type=ClueType.ALL_SAME, region=region, text=text)
        c.validate()
        return c

    def to_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "clue_id": self.clue_id,
            "clue_type": self.clue_type.value,
        }
        if self.person is not None:
            d["person"] = self.person
        if self.person2 is not None:
            d["person2"] = self.person2
        if self.status is not None:
            d["status"] = self.status.value
        if self.region is not None:
            d["region"] = self.region.to_dict()
        if self.k is not None:
            d["k"] = self.k
        if self.target_status != Status.CRIMINAL:
            d["target_status"] = self.target_status.value
        if self.parity is not None:
            d["parity"] = self.parity
        if self.compare_op is not None:
            d["compare_op"] = self.compare_op.value
        if self.region2 is not None:
            d["region2"] = self.region2.to_dict()
        if self.text:
            d["text"] = self.text
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any], clue_id: Optional[str] = None) -> "Clue":
        """Parse Clue supporting both member D schema and logic-core schema."""
        raw_type = (data.get("clue_type") or data.get("type", "")).upper()
        if raw_type == "COUNT_COMPARE":
            raw_type = "COMPARE"
        clue_type = ClueType(raw_type)

        cid = clue_id or data.get("clue_id") or f"clue_{clue_type.value}"

        # Resolve region(s)
        region = None
        if "region" in data and data["region"]:
            region = RegionSpec.from_dict(data["region"])
        elif "left" in data and data["left"]:
            region = RegionSpec.from_dict(data["left"])

        region2 = None
        if "region2" in data and data["region2"]:
            region2 = RegionSpec.from_dict(data["region2"])
        elif "right" in data and data["right"]:
            region2 = RegionSpec.from_dict(data["right"])

        # Resolve persons
        person = data.get("person") or data.get("cell") or data.get("a")
        person2 = data.get("person2") or data.get("b")

        # Status
        status = None
        if "status" in data and data["status"]:
            status = Status(data["status"].upper())

        target_status = Status(data.get("target_status", Status.CRIMINAL.value).upper())

        # Parity
        parity = None
        if "parity" in data and data["parity"] is not None:
            parity = ParityType.from_val(data["parity"]).to_int()

        # CompareOp
        compare_op = None
        op_raw = data.get("compare_op") or data.get("op")
        if op_raw is not None:
            compare_op = CompareOp.from_str(str(op_raw)) if isinstance(op_raw, str) else op_raw

        c = cls(
            clue_id=cid,
            clue_type=clue_type,
            person=person,
            person2=person2,
            status=status,
            region=region,
            k=data.get("k"),
            target_status=target_status,
            parity=parity,
            compare_op=compare_op,
            region2=region2,
            text=data.get("text", ""),
        )
        c.validate()
        return c


@dataclass
class Character:
    """Character in the puzzle.
    
    Contains display name, cell location, profession, and clue.
    Note: hidden_status must only be used by Game Engine, never by Logic Agent.
    """
    name: str
    cell: str
    profession: str = ""
    hidden_status: Optional[Status] = None
    clue: Optional[Clue] = None
    is_revealed: bool = False
    proved_status: Optional[Status] = None

    @property
    def cell_coord(self) -> CellCoord:
        return CellCoord.from_str(self.cell)

    def to_dict(self, include_hidden: bool = True) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "name": self.name,
            "cell": self.cell.upper(),
            "profession": self.profession,
            "is_revealed": self.is_revealed,
        }
        if self.proved_status is not None:
            d["proved_status"] = self.proved_status.value
        if self.clue is not None:
            d["clue"] = self.clue.to_dict()
        if include_hidden and self.hidden_status is not None:
            d["hidden_status"] = self.hidden_status.value
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Character":
        clue = Clue.from_dict(data["clue"]) if "clue" in data and data["clue"] else None
        hidden_status = Status(data["hidden_status"].upper()) if "hidden_status" in data and data["hidden_status"] else None
        proved_status = Status(data["proved_status"].upper()) if "proved_status" in data and data["proved_status"] else None
        return cls(
            name=data["name"],
            cell=data["cell"].upper(),
            profession=data.get("profession", ""),
            hidden_status=hidden_status,
            clue=clue,
            is_revealed=data.get("is_revealed", False),
            proved_status=proved_status,
        )


@dataclass
class Puzzle:
    """Unified Puzzle container supporting both team format and experiment formats."""
    id: str
    size: int
    cells: List[Dict[str, Any]]
    solution: Dict[str, Status]
    initial_revealed: List[str]
    clues: Dict[str, Clue]
    difficulty: str = "medium"
    characters: List[Character] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Puzzle":
        """Load from either Member D schema or legacy schema."""
        pid = data.get("id", "puzzle")
        size = data.get("size") or data.get("grid_size", 3)
        initial_revealed = [c.upper() for c in data.get("initial_revealed", [])]
        difficulty = data.get("difficulty", "medium")
        meta = data.get("meta", {})

        clues: Dict[str, Clue] = {}
        solution: Dict[str, Status] = {}
        cells: List[Dict[str, Any]] = []
        characters: List[Character] = []

        # If schema has 'clues' dictionary (Member D's schema)
        if "clues" in data:
            for cid, cdict in data["clues"].items():
                clues[cid.upper()] = Clue.from_dict(cdict, clue_id=f"clue_{cid.upper()}")

        if "solution" in data:
            for cid, sval in data["solution"].items():
                solution[cid.upper()] = Status(sval.upper())

        if "cells" in data:
            cells = data["cells"]
            for c in cells:
                cid = c["id"].upper()
                ch = Character(
                    name=c.get("name", cid),
                    cell=cid,
                    profession=c.get("profession", ""),
                    hidden_status=solution.get(cid),
                    clue=clues.get(cid),
                    is_revealed=(cid in initial_revealed),
                )
                characters.append(ch)

        elif "characters" in data:
            # Legacy format with characters list
            for ch_dict in data["characters"]:
                ch = Character.from_dict(ch_dict)
                characters.append(ch)
                cid = ch.cell.upper()
                cells.append({
                    "id": cid,
                    "row": ch.cell_coord.row,
                    "col": ch.cell_coord.col_letter,
                    "name": ch.name,
                    "profession": ch.profession,
                })
                if ch.hidden_status:
                    solution[cid] = ch.hidden_status
                if ch.clue:
                    clues[cid] = ch.clue

        return cls(
            id=pid,
            size=size,
            cells=cells,
            solution=solution,
            initial_revealed=initial_revealed,
            clues=clues,
            difficulty=difficulty,
            characters=characters,
            meta=meta,
        )

    @classmethod
    def load(cls, path: Union[str, Path]) -> "Puzzle":
        """Load puzzle from a JSON file path."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to Member D standard JSON schema."""
        return {
            "id": self.id,
            "size": self.size,
            "difficulty": self.difficulty,
            "cells": self.cells,
            "solution": {c: s.value for c, s in self.solution.items()},
            "initial_revealed": self.initial_revealed,
            "clues": {c: clue.to_dict() for c, clue in self.clues.items()},
            "meta": self.meta,
        }
