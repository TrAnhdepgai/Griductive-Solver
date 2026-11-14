"""Puzzle schema helpers (member D).

Conventions shared by the whole team
------------------------------------
* Cell id  = column letter + row number, e.g. "C2" (column C, row 2).
* Row-major index i = (row-1) * N + col_index   (0-based).
* Propositional variable of cell i (DIMACS style, 1-based) = i + 1.
  So for a 3x3 board A1=1, B1=2, C1=3, A2=4, ... C3=9.
* Bit i of an assignment bitmask = 1  <=>  the cell is a CRIMINAL.
"""
from __future__ import annotations

import json
from pathlib import Path

COLS = "ABCDE"
STATUSES = ("CRIMINAL", "INNOCENT")
CORE_TYPES = ("FACT", "SAME", "DIFFERENT", "EXACTLY", "AT_LEAST", "AT_MOST")
EXT_TYPES = ("PARITY", "COMPARE")          # optional extensions used by the generator
COMPARE_OPS = ("<", "==", ">")


def cell_id(row: int, col: int) -> str:
    """0-based (row, col) -> 'B2'."""
    return f"{COLS[col]}{row + 1}"


def all_cells(n: int) -> list[str]:
    """All cell ids in row-major order."""
    return [cell_id(r, c) for r in range(n) for c in range(n)]


def parse_cell(cid: str, n: int) -> tuple[int, int]:
    """'B2' -> (row, col), 0-based. Raises ValueError for bad ids."""
    if not isinstance(cid, str) or len(cid) < 2 or cid[0] not in COLS[:n] or not cid[1:].isdigit():
        raise ValueError(f"bad cell id {cid!r} for N={n}")
    row, col = int(cid[1:]) - 1, COLS.index(cid[0])
    if not 0 <= row < n:
        raise ValueError(f"bad cell id {cid!r} for N={n}")
    return row, col


def cell_index(cid: str, n: int) -> int:
    row, col = parse_cell(cid, n)
    return row * n + col


def region_cells(region: dict, n: int) -> list[str]:
    """Resolve a region to a list of cell ids.

    {"kind": "row", "row": 2} | {"kind": "column", "col": "B"} |
    {"kind": "neighbors", "of": "B2"} | {"kind": "cells", "cells": ["A1", "C3"]}
    """
    kind = region.get("kind")
    if kind == "row":
        r = region["row"]
        if not isinstance(r, int) or not 1 <= r <= n:
            raise ValueError(f"bad row {r!r}")
        return [cell_id(r - 1, c) for c in range(n)]
    if kind == "column":
        col = region["col"]
        if col not in COLS[:n]:
            raise ValueError(f"bad column {col!r}")
        c = COLS.index(col)
        return [cell_id(r, c) for r in range(n)]
    if kind == "neighbors":
        r, c = parse_cell(region["of"], n)
        return [cell_id(rr, cc)
                for rr in range(r - 1, r + 2) for cc in range(c - 1, c + 2)
                if 0 <= rr < n and 0 <= cc < n and (rr, cc) != (r, c)]
    if kind == "cells":
        lst = region["cells"]
        for x in lst:
            parse_cell(x, n)
        if len(set(lst)) != len(lst) or not lst:
            raise ValueError("explicit region must be a non-empty list of distinct cells")
        return list(lst)
    raise ValueError(f"unknown region kind {kind!r}")


def validate_clue(clue: dict, n: int) -> list[str]:
    """Structural validation of one clue. Returns a list of error strings."""
    errs: list[str] = []
    try:
        t = clue["type"]
        if t == "FACT":
            parse_cell(clue["cell"], n)
            if clue["status"] not in STATUSES:
                errs.append(f"bad status {clue['status']!r}")
        elif t in ("SAME", "DIFFERENT"):
            parse_cell(clue["a"], n)
            parse_cell(clue["b"], n)
            if clue["a"] == clue["b"]:
                errs.append("a and b must differ")
        elif t in ("EXACTLY", "AT_LEAST", "AT_MOST"):
            size = len(region_cells(clue["region"], n))
            k = clue["k"]
            if isinstance(k, bool) or not isinstance(k, int) or not 0 <= k <= size:
                errs.append(f"k={k!r} must satisfy 0 <= k <= {size}")
        elif t == "PARITY":
            region_cells(clue["region"], n)
            if clue["parity"] not in ("EVEN", "ODD"):
                errs.append(f"bad parity {clue['parity']!r}")
        elif t == "COMPARE":
            region_cells(clue["left"], n)
            region_cells(clue["right"], n)
            if clue["op"] not in COMPARE_OPS:
                errs.append(f"bad op {clue['op']!r}")
        else:
            errs.append(f"unknown clue type {t!r}")
    except (KeyError, ValueError, TypeError) as e:
        errs.append(f"{type(e).__name__}: {e}")
    return errs


def validate_puzzle(p: dict) -> list[str]:
    """Structural validation of a whole puzzle (does not check truth/uniqueness)."""
    errs: list[str] = []
    for key in ("id", "size", "cells", "solution", "initial_revealed", "clues"):
        if key not in p:
            errs.append(f"missing key {key!r}")
    if errs:
        return errs
    n = p["size"]
    if n not in (3, 4, 5):
        errs.append(f"size must be 3, 4 or 5 (got {n!r})")
        return errs
    ids = all_cells(n)
    if [c.get("id") for c in p["cells"]] != ids:
        errs.append("cells must list every cell once, in row-major order")
    for c in p["cells"]:
        for k in ("name", "profession"):
            if not c.get(k):
                errs.append(f"cell {c.get('id')} lacks {k}")
    if set(p["solution"]) != set(ids) or any(v not in STATUSES for v in p["solution"].values()):
        errs.append("solution must map every cell to CRIMINAL/INNOCENT")
    if not p["initial_revealed"] or any(c not in ids for c in p["initial_revealed"]):
        errs.append("initial_revealed must be a non-empty list of valid cells")
    if set(p["clues"]) != set(ids):
        errs.append("every cell needs exactly one clue")
    else:
        for cid, clue in p["clues"].items():
            errs += [f"clue {cid}: {e}" for e in validate_clue(clue, n)]
    return errs


def load_puzzle(path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def solution_mask(p: dict) -> int:
    n = p["size"]
    return sum(1 << cell_index(c, n) for c, s in p["solution"].items() if s == "CRIMINAL")