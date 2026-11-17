"""Extensions for Griductive Logic Core.

Implements required extensions beyond the 6 core templates:
1. PARITY constraints (Even / Odd criminals in region)
2. COUNT_COMPARE constraints (Comparison of counts between two regions)
3. ALL_SAME constraints (All characters in a region share identical status)
4. Advanced Region expressions (corners, boundary, interior, common neighbors, between, intersection)
5. Natural language clue formatter for GUI / display
"""

from typing import List, Optional
from .types import Status, ClueType, RegionType, CompareOp, ParityType
from .model import Clue, RegionSpec


class ParityClue:
    """Helper to construct parity constraint clues."""

    @staticmethod
    def even(clue_id: str, region: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> Clue:
        """Constraint: Count of target_status in region is EVEN."""
        nl_text = text or f"An EVEN number of {target_status.value.lower()}s in region"
        return Clue.parity_clue(clue_id=clue_id, parity=0, region=region, target_status=target_status, text=nl_text)

    @staticmethod
    def odd(clue_id: str, region: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> Clue:
        """Constraint: Count of target_status in region is ODD."""
        nl_text = text or f"An ODD number of {target_status.value.lower()}s in region"
        return Clue.parity_clue(clue_id=clue_id, parity=1, region=region, target_status=target_status, text=nl_text)


class CountCompareClue:
    """Helper to construct count comparison clues between two regions."""

    @staticmethod
    def more_than(clue_id: str, region1: RegionSpec, region2: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> Clue:
        """Constraint: Count in region1 > Count in region2."""
        nl_text = text or f"More {target_status.value.lower()}s in region 1 than region 2"
        return Clue.count_compare(clue_id, region1, CompareOp.GT, region2, target_status, nl_text)

    @staticmethod
    def equal(clue_id: str, region1: RegionSpec, region2: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> Clue:
        """Constraint: Count in region1 == Count in region2."""
        nl_text = text or f"Equal number of {target_status.value.lower()}s in region 1 and region 2"
        return Clue.count_compare(clue_id, region1, CompareOp.EQ, region2, target_status, nl_text)

    @staticmethod
    def at_least_as_many(clue_id: str, region1: RegionSpec, region2: RegionSpec, target_status: Status = Status.CRIMINAL, text: str = "") -> Clue:
        """Constraint: Count in region1 >= Count in region2."""
        nl_text = text or f"At least as many {target_status.value.lower()}s in region 1 as in region 2"
        return Clue.count_compare(clue_id, region1, CompareOp.GE, region2, target_status, nl_text)


class AllSameClue:
    """Helper to construct all-same status clues."""

    @staticmethod
    def create(clue_id: str, region: RegionSpec, text: str = "") -> Clue:
        """Constraint: All characters in region share the exact same status."""
        nl_text = text or "All characters in this region share the same status"
        return Clue.all_same(clue_id=clue_id, region=region, text=nl_text)


class AdvancedRegions:
    """Convenience factory for advanced region expressions."""

    @staticmethod
    def corners() -> RegionSpec:
        return RegionSpec.corners()

    @staticmethod
    def boundary() -> RegionSpec:
        return RegionSpec.boundary()

    @staticmethod
    def interior() -> RegionSpec:
        return RegionSpec.interior()

    @staticmethod
    def common_neighbors(cell1: str, cell2: str) -> RegionSpec:
        return RegionSpec.common_neighbors(cell1, cell2)

    @staticmethod
    def between(cell1: str, cell2: str) -> RegionSpec:
        return RegionSpec.between(cell1, cell2)

    @staticmethod
    def intersection(r1: RegionSpec, r2: RegionSpec) -> RegionSpec:
        return RegionSpec.intersection(r1, r2)

    @staticmethod
    def union(r1: RegionSpec, r2: RegionSpec) -> RegionSpec:
        return RegionSpec.union(r1, r2)

    @staticmethod
    def difference(r1: RegionSpec, r2: RegionSpec) -> RegionSpec:
        return RegionSpec.difference(r1, r2)


def format_clue_natural_language(clue: Clue) -> str:
    """Generate a clean English description of any structured clue."""
    if clue.text:
        return clue.text

    if clue.clue_type == ClueType.FACT:
        return f"{clue.person} is {clue.status.value}."

    if clue.clue_type == ClueType.SAME:
        return f"{clue.person} and {clue.person2} have the same status."

    if clue.clue_type == ClueType.DIFFERENT:
        return f"{clue.person} and {clue.person2} have different statuses."

    role = clue.target_status.value.lower() + "s"
    reg_desc = _format_region_desc(clue.region)

    if clue.clue_type == ClueType.EXACTLY:
        if clue.k == 0:
            return f"No {role} in {reg_desc}."
        return f"Exactly {clue.k} {role} in {reg_desc}."

    if clue.clue_type == ClueType.AT_LEAST:
        return f"At least {clue.k} {role} in {reg_desc}."

    if clue.clue_type == ClueType.AT_MOST:
        return f"At most {clue.k} {role} in {reg_desc}."

    if clue.clue_type == ClueType.PARITY:
        par_word = "even" if clue.parity == 0 else "odd"
        return f"An {par_word} number of {role} in {reg_desc}."

    if clue.clue_type == ClueType.COUNT_COMPARE:
        reg2_desc = _format_region_desc(clue.region2)
        op_word = {
            CompareOp.GT: "more than",
            CompareOp.GE: "at least as many as in",
            CompareOp.LT: "fewer than",
            CompareOp.LE: "at most as many as in",
            CompareOp.EQ: "the same number as in",
            CompareOp.NE: "a different number than in",
        }.get(clue.compare_op, clue.compare_op.value)
        return f"Number of {role} in {reg_desc} is {op_word} {reg2_desc}."

    if clue.clue_type == ClueType.ALL_SAME:
        return f"All characters in {reg_desc} have the same status."

    return f"Clue {clue.clue_id} ({clue.clue_type.value})"


def _format_region_desc(region: Optional[RegionSpec]) -> str:
    """Format RegionSpec for display."""
    if not region:
        return "the region"
    if region.region_type == RegionType.ROW:
        return f"row {region.row}"
    if region.region_type == RegionType.COL:
        return f"column {region.col}"
    if region.region_type == RegionType.NEIGHBORS:
        return f"the neighbors of {region.cell}"
    if region.region_type == RegionType.EXPLICIT:
        return f"cells {', '.join(region.cells or [])}"
    if region.region_type == RegionType.CORNERS:
        return "the corner cells"
    if region.region_type == RegionType.BOUNDARY:
        return "the boundary cells"
    if region.region_type == RegionType.INTERIOR:
        return "the interior cells"
    if region.region_type == RegionType.COMMON_NEIGHBORS:
        return f"the common neighbors of {region.cell1} and {region.cell2}"
    if region.region_type == RegionType.BETWEEN:
        return f"the cells between {region.cell1} and {region.cell2}"
    return region.region_type.value.lower()
