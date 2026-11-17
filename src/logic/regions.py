"""Region resolver for Griductive puzzles.

Resolves regions (rows, columns, neighbors, explicit lists, corners, boundary, common neighbors, etc.)
into concrete sets of cell IDs on an N x N grid.
"""

from typing import Set, List, Dict, Optional, Union, Tuple
from .types import RegionType
from .model import CellCoord, RegionSpec, Character, Clue


class RegionResolver:
    """Resolves abstract region specifications into sets of concrete cell coordinates."""

    def __init__(self, grid_size: int, characters: Optional[List[Character]] = None):
        """
        Args:
            grid_size: Dimension N of the N x N grid.
            characters: Optional list of characters to map between character names and cells.
        """
        if grid_size <= 0:
            raise ValueError(f"grid_size must be positive, got {grid_size}")
        self.grid_size = grid_size
        self.N = grid_size

        # Mappings between names and cell IDs
        self.name_to_cell: Dict[str, str] = {}
        self.cell_to_name: Dict[str, str] = {}
        if characters:
            for ch in characters:
                c_id = ch.cell.upper()
                self.name_to_cell[ch.name.lower()] = c_id
                self.name_to_cell[c_id.lower()] = c_id
                self.cell_to_name[c_id] = ch.name

    def normalize_person_to_cell(self, identifier: str) -> str:
        """Resolve a person's display name or cell identifier (e.g. 'Mara' or 'A1') to a canonical cell_id."""
        key = identifier.strip().lower()
        if key in self.name_to_cell:
            return self.name_to_cell[key]
        # Try parsing directly as cell coordinate
        coord = CellCoord.from_str(identifier)
        if not coord.is_valid(self.N):
            raise ValueError(f"Cell '{identifier}' is out of bounds for {self.N}x{self.N} grid.")
        return coord.cell_id

    def resolve(self, spec: RegionSpec) -> List[str]:
        """Resolve a RegionSpec into a deterministic, sorted list of canonical cell IDs (e.g. ['A1', 'B1', 'C1'])."""
        cells: Set[str] = set()

        if spec.region_type == RegionType.ROW:
            if spec.row is None:
                raise ValueError("ROW region requires 'row' integer.")
            if not (1 <= spec.row <= self.N):
                raise ValueError(f"Row {spec.row} is out of bounds (1..{self.N}).")
            for col in range(self.N):
                cells.add(CellCoord(row=spec.row, col=col).cell_id)

        elif spec.region_type == RegionType.COL:
            if not spec.col:
                raise ValueError("COL region requires 'col' letter string.")
            col_letter = spec.col.upper().strip()
            col_idx = ord(col_letter) - ord('A')
            if not (0 <= col_idx < self.N):
                max_letter = chr(ord('A') + self.N - 1)
                raise ValueError(f"Column '{col_letter}' is out of bounds ('A'..'{max_letter}').")
            for row in range(1, self.N + 1):
                cells.add(CellCoord(row=row, col=col_idx).cell_id)

        elif spec.region_type == RegionType.NEIGHBORS:
            if not spec.cell:
                raise ValueError("NEIGHBORS region requires center 'cell'.")
            center_cell = self.normalize_person_to_cell(spec.cell)
            coord = CellCoord.from_str(center_cell)
            for r in range(max(1, coord.row - 1), min(self.N, coord.row + 1) + 1):
                for c in range(max(0, coord.col - 1), min(self.N - 1, coord.col + 1) + 1):
                    other = CellCoord(row=r, col=c)
                    if other != coord:
                        cells.add(other.cell_id)

        elif spec.region_type == RegionType.EXPLICIT:
            if spec.cells is None:
                raise ValueError("EXPLICIT region requires 'cells' list.")
            for c_id in spec.cells:
                canonical = self.normalize_person_to_cell(c_id)
                cells.add(canonical)

        elif spec.region_type == RegionType.CORNERS:
            cells = {
                CellCoord(row=1, col=0).cell_id,
                CellCoord(row=1, col=self.N - 1).cell_id,
                CellCoord(row=self.N, col=0).cell_id,
                CellCoord(row=self.N, col=self.N - 1).cell_id,
            }

        elif spec.region_type == RegionType.BOUNDARY:
            for r in range(1, self.N + 1):
                for c in range(self.N):
                    if r == 1 or r == self.N or c == 0 or c == self.N - 1:
                        cells.add(CellCoord(row=r, col=c).cell_id)

        elif spec.region_type == RegionType.INTERIOR:
            for r in range(2, self.N):
                for c in range(1, self.N - 1):
                    cells.add(CellCoord(row=r, col=c).cell_id)

        elif spec.region_type == RegionType.COMMON_NEIGHBORS:
            if not spec.cell1 or not spec.cell2:
                raise ValueError("COMMON_NEIGHBORS requires 'cell1' and 'cell2'.")
            n1 = set(self.resolve(RegionSpec.neighbors_region(spec.cell1)))
            n2 = set(self.resolve(RegionSpec.neighbors_region(spec.cell2)))
            cells = n1.intersection(n2)

        elif spec.region_type == RegionType.BETWEEN:
            if not spec.cell1 or not spec.cell2:
                raise ValueError("BETWEEN requires 'cell1' and 'cell2'.")
            c1 = CellCoord.from_str(self.normalize_person_to_cell(spec.cell1))
            c2 = CellCoord.from_str(self.normalize_person_to_cell(spec.cell2))
            dr = c2.row - c1.row
            dc = c2.col - c1.col
            step_r = (dr > 0) - (dr < 0)
            step_c = (dc > 0) - (dc < 0)

            # Check if straight line (horizontal, vertical, or diagonal)
            if dr == 0 or dc == 0 or abs(dr) == abs(dc):
                curr_r = c1.row + step_r
                curr_c = c1.col + step_c
                while (curr_r, curr_c) != (c2.row, c2.col):
                    mid = CellCoord(row=curr_r, col=curr_c)
                    if mid.is_valid(self.N):
                        cells.add(mid.cell_id)
                    curr_r += step_r
                    curr_c += step_c

        elif spec.region_type == RegionType.INTERSECTION:
            if not spec.sub_regions or len(spec.sub_regions) != 2:
                raise ValueError("INTERSECTION requires exactly two sub_regions.")
            s1 = set(self.resolve(spec.sub_regions[0]))
            s2 = set(self.resolve(spec.sub_regions[1]))
            cells = s1.intersection(s2)

        elif spec.region_type == RegionType.UNION:
            if not spec.sub_regions or len(spec.sub_regions) != 2:
                raise ValueError("UNION requires exactly two sub_regions.")
            s1 = set(self.resolve(spec.sub_regions[0]))
            s2 = set(self.resolve(spec.sub_regions[1]))
            cells = s1.union(s2)

        elif spec.region_type == RegionType.DIFFERENCE:
            if not spec.sub_regions or len(spec.sub_regions) != 2:
                raise ValueError("DIFFERENCE requires exactly two sub_regions.")
            s1 = set(self.resolve(spec.sub_regions[0]))
            s2 = set(self.resolve(spec.sub_regions[1]))
            cells = s1.difference(s2)

        else:
            raise ValueError(f"Unsupported RegionType: {spec.region_type}")

        # Deterministic order: row-major (row 1 to N, col A to ...)
        def sort_key(cid: str) -> Tuple[int, int]:
            coord = CellCoord.from_str(cid)
            return (coord.row, coord.col)

        return sorted(cells, key=sort_key)

    def get_referenced_cells(self, clue: Clue) -> List[str]:
        """Return all cell coordinates referenced or counted by a clue (for GUI highlighting)."""
        clue.validate()
        cells: Set[str] = set()

        if clue.person:
            cells.add(self.normalize_person_to_cell(clue.person))
        if clue.person2:
            cells.add(self.normalize_person_to_cell(clue.person2))
        if clue.region:
            cells.update(self.resolve(clue.region))
        if clue.region2:
            cells.update(self.resolve(clue.region2))

        def sort_key(cid: str) -> Tuple[int, int]:
            coord = CellCoord.from_str(cid)
            return (coord.row, coord.col)

        return sorted(cells, key=sort_key)
