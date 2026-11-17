"""Sample 3x3 puzzles with unique solutions for testing and development.

Each puzzle defines:
- grid_size: Dimension N
- characters: List of character definitions (name, cell, profession, hidden_status, clue)
- initial_revealed: List of cell identifiers face-up at step 0
"""

import json
from pathlib import Path
from typing import Dict, Any, List
from ..logic.types import Status, ClueType, RegionType, CompareOp
from ..logic.model import Character, Clue, RegionSpec


def get_sample_puzzle_1() -> Dict[str, Any]:
    """Puzzle 1: 3x3 grid with clean step-by-step entailment.
    
    Solution:
    A1: CRIMINAL, B1: INNOCENT, C1: CRIMINAL
    A2: INNOCENT, B2: CRIMINAL, C2: INNOCENT
    A3: CRIMINAL, B3: INNOCENT, C3: CRIMINAL
    """
    characters = [
        # Row 1
        {
            "name": "Abel",
            "cell": "A1",
            "profession": "Astronaut",
            "hidden_status": "CRIMINAL",
            "clue": {
                "clue_id": "clue_A1",
                "clue_type": "EXACTLY",
                "k": 2,
                "region": {"region_type": "ROW", "row": 1},
                "target_status": "CRIMINAL",
                "text": "Exactly 2 people in row 1 are Criminals.",
            },
        },
        {
            "name": "Bea",
            "cell": "B1",
            "profession": "Baker",
            "hidden_status": "INNOCENT",
            "clue": {
                "clue_id": "clue_B1",
                "clue_type": "SAME",
                "person": "A1",
                "person2": "C1",
                "text": "Abel and Charlie have the same status.",
            },
        },
        {
            "name": "Charlie",
            "cell": "C1",
            "profession": "Clerk",
            "hidden_status": "CRIMINAL",
            "clue": {
                "clue_id": "clue_C1",
                "clue_type": "SAME",
                "person": "C1",
                "person2": "C3",
                "text": "Charlie and Ian have the same status.",
            },
        },
        # Row 2
        {
            "name": "Diana",
            "cell": "A2",
            "profession": "Doctor",
            "hidden_status": "INNOCENT",
            "clue": {
                "clue_id": "clue_A2",
                "clue_type": "AT_LEAST",
                "k": 2,
                "region": {"region_type": "COL", "col": "A"},
                "target_status": "CRIMINAL",
                "text": "At least 2 people in column A are Criminals.",
            },
        },
        {
            "name": "Evan",
            "cell": "B2",
            "profession": "Engineer",
            "hidden_status": "CRIMINAL",
            "clue": {
                "clue_id": "clue_B2",
                "clue_type": "EXACTLY",
                "k": 4,
                "region": {"region_type": "NEIGHBORS", "cell": "B2"},
                "target_status": "CRIMINAL",
                "text": "Exactly 4 neighbors of Evan are Criminals.",
            },
        },
        {
            "name": "Fiona",
            "cell": "C2",
            "profession": "Farmer",
            "hidden_status": "INNOCENT",
            "clue": {
                "clue_id": "clue_C2",
                "clue_type": "DIFFERENT",
                "person": "B2",
                "person2": "C2",
                "text": "Evan and Fiona have different statuses.",
            },
        },
        # Row 3
        {
            "name": "George",
            "cell": "A3",
            "profession": "Guard",
            "hidden_status": "CRIMINAL",
            "clue": {
                "clue_id": "clue_A3",
                "clue_type": "EXACTLY",
                "k": 2,
                "region": {"region_type": "ROW", "row": 3},
                "target_status": "CRIMINAL",
                "text": "Exactly 2 people in row 3 are Criminals.",
            },
        },
        {
            "name": "Hannah",
            "cell": "B3",
            "profession": "Hunter",
            "hidden_status": "INNOCENT",
            "clue": {
                "clue_id": "clue_B3",
                "clue_type": "EXACTLY",
                "k": 1,
                "region": {"region_type": "COL", "col": "B"},
                "target_status": "CRIMINAL",
                "text": "Exactly 1 person in column B is Criminal.",
            },
        },
        {
            "name": "Ian",
            "cell": "C3",
            "profession": "Inspector",
            "hidden_status": "CRIMINAL",
            "clue": {
                "clue_id": "clue_C3",
                "clue_type": "AT_MOST",
                "k": 2,
                "region": {"region_type": "COL", "col": "C"},
                "target_status": "CRIMINAL",
                "text": "At most 2 people in column C are Criminals.",
            },
        },
    ]

    return {
        "puzzle_id": "sample_3x3_01",
        "grid_size": 3,
        "initial_revealed": ["A1", "B1"],  # Abel (CRIMINAL) and Bea (INNOCENT) start revealed
        "characters": characters,
    }


def get_sample_puzzle_2() -> Dict[str, Any]:
    """Puzzle 2: 3x3 grid demonstrating AT_MOST, AT_LEAST, and EXPLICIT regions.
    
    Solution:
    A1: INNOCENT, B1: CRIMINAL, C1: INNOCENT
    A2: CRIMINAL, B2: INNOCENT, C2: CRIMINAL
    A3: INNOCENT, B3: CRIMINAL, C3: INNOCENT
    """
    characters = [
        {"name": "Arthur", "cell": "A1", "profession": "Artist", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "c_A1", "clue_type": "AT_MOST", "k": 1, "region": {"region_type": "ROW", "row": 1}, "target_status": "CRIMINAL", "text": "At most 1 Criminal in row 1."}},
        {"name": "Bella", "cell": "B1", "profession": "Biologist", "hidden_status": "CRIMINAL",
         "clue": {"clue_id": "c_B1", "clue_type": "EXACTLY", "k": 2, "region": {"region_type": "COL", "col": "B"}, "target_status": "CRIMINAL", "text": "Exactly 2 Criminals in column B."}},
        {"name": "Chloe", "cell": "C1", "profession": "Chef", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "c_C1", "clue_type": "SAME", "person": "A1", "person2": "C1", "text": "Arthur and Chloe have the same status."}},
        {"name": "David", "cell": "A2", "profession": "Dentist", "hidden_status": "CRIMINAL",
         "clue": {"clue_id": "c_A2", "clue_type": "DIFFERENT", "person": "A2", "person2": "B2", "text": "David and Emma have different statuses."}},
        {"name": "Emma", "cell": "B2", "profession": "Editor", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "c_B2", "clue_type": "EXACTLY", "k": 4, "region": {"region_type": "NEIGHBORS", "cell": "B2"}, "target_status": "CRIMINAL", "text": "Exactly 4 neighbors of Emma are Criminals."}},
        {"name": "Felix", "cell": "C2", "profession": "Florist", "hidden_status": "CRIMINAL",
         "clue": {"clue_id": "c_C2", "clue_type": "SAME", "person": "A2", "person2": "C2", "text": "David and Felix have the same status."}},
        {"name": "Grace", "cell": "A3", "profession": "Geologist", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "c_A3", "clue_type": "EXPLICIT", "k": 0, "region": {"region_type": "EXPLICIT", "cells": ["A1", "A3", "C1", "C3"]}, "target_status": "CRIMINAL", "text": "No Criminals among Arthur, Grace, Chloe, and Henry."}},
        {"name": "Hugo", "cell": "B3", "profession": "Historian", "hidden_status": "CRIMINAL",
         "clue": {"clue_id": "c_B3", "clue_type": "AT_LEAST", "k": 1, "region": {"region_type": "ROW", "row": 3}, "target_status": "CRIMINAL", "text": "At least 1 Criminal in row 3."}},
        {"name": "Iris", "cell": "C3", "profession": "Illustrator", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "c_C3", "clue_type": "SAME", "person": "A3", "person2": "C3", "text": "Grace and Iris have the same status."}},
    ]
    # Note: Grace's clue uses EXACTLY with 0 on corner cells
    characters[6]["clue"]["clue_type"] = "EXACTLY"

    return {
        "puzzle_id": "sample_3x3_02",
        "grid_size": 3,
        "initial_revealed": ["A1", "B1"],
        "characters": characters,
    }


def get_sample_puzzle_3() -> Dict[str, Any]:
    """Puzzle 3: 3x3 grid incorporating extension clues (PARITY & COUNT_COMPARE).
    
    Solution:
    A1: CRIMINAL, B1: CRIMINAL, C1: INNOCENT
    A2: INNOCENT, B2: INNOCENT, C2: INNOCENT
    A3: INNOCENT, B3: INNOCENT, C3: CRIMINAL
    """
    characters = [
        {"name": "Anna", "cell": "A1", "profession": "Astronomer", "hidden_status": "CRIMINAL",
         "clue": {"clue_id": "ext_A1", "clue_type": "EXACTLY", "k": 2, "region": {"region_type": "ROW", "row": 1}, "target_status": "CRIMINAL", "text": "Exactly 2 Criminals in row 1."}},
        {"name": "Ben", "cell": "B1", "profession": "Botanist", "hidden_status": "CRIMINAL",
         "clue": {"clue_id": "ext_B1", "clue_type": "PARITY", "parity": 1, "region": {"region_type": "COL", "col": "B"}, "target_status": "CRIMINAL", "text": "An ODD number of Criminals in column B."}},
        {"name": "Cara", "cell": "C1", "profession": "Chemist", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "ext_C1", "clue_type": "COUNT_COMPARE", "region": {"region_type": "COL", "col": "A"}, "compare_op": "==", "region2": {"region_type": "COL", "col": "C"}, "target_status": "CRIMINAL", "text": "Equal number of Criminals in column A and column C."}},
        {"name": "Dan", "cell": "A2", "profession": "Diver", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "ext_A2", "clue_type": "DIFFERENT", "person": "A1", "person2": "A2", "text": "Anna and Dan have different statuses."}},
        {"name": "Eva", "cell": "B2", "profession": "Economist", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "ext_B2", "clue_type": "PARITY", "parity": 0, "region": {"region_type": "CORNERS"}, "target_status": "CRIMINAL", "text": "An EVEN number of Criminals in the corners."}},
        {"name": "Finn", "cell": "C2", "profession": "Filmmaker", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "ext_C2", "clue_type": "AT_MOST", "k": 1, "region": {"region_type": "ROW", "row": 2}, "target_status": "CRIMINAL", "text": "At most 1 Criminal in row 2."}},
        {"name": "Gia", "cell": "A3", "profession": "Gardener", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "ext_A3", "clue_type": "SAME", "person": "A2", "person2": "A3", "text": "Dan and Gia have the same status."}},
        {"name": "Hank", "cell": "B3", "profession": "Hypnotist", "hidden_status": "INNOCENT",
         "clue": {"clue_id": "ext_B3", "clue_type": "ALL_SAME", "region": {"region_type": "EXPLICIT", "cells": ["A3", "B3"]}, "text": "Gia and Hank have the same status."}},
        {"name": "Iris", "cell": "C3", "profession": "Inventor", "hidden_status": "CRIMINAL",
         "clue": {"clue_id": "ext_C3", "clue_type": "FACT", "person": "C3", "status": "CRIMINAL", "text": "Iris is a Criminal."}},
    ]

    return {
        "puzzle_id": "sample_3x3_03",
        "grid_size": 3,
        "initial_revealed": ["A1", "A2"],
        "characters": characters,
    }


def get_sample_puzzles() -> List[Dict[str, Any]]:
    """Return all sample 3x3 puzzles."""
    return [get_sample_puzzle_1(), get_sample_puzzle_2(), get_sample_puzzle_3()]


def export_sample_puzzles_to_json(target_dir: Path) -> List[Path]:
    """Export sample puzzles as JSON files into the specified directory."""
    target_dir.mkdir(parents=True, exist_ok=True)
    exported = []
    for puzzle in get_sample_puzzles():
        path = target_dir / f"{puzzle['puzzle_id']}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(puzzle, f, indent=2)
        exported.append(path)
    return exported
