"""Reference semantic evaluator for every clue template (member D).

Deliberately independent from the team's encoder/evaluator so it can be used
for brute-force cross-checking. `models` may be a Python int (one assignment
bitmask) or a numpy uint32 array (many assignments at once).
"""
from __future__ import annotations

import numpy as np

from schema import cell_index, parse_cell, region_cells

_idx = np.arange(1 << 16, dtype=np.uint32)
_PC16 = sum(((_idx >> b) & 1) for b in range(16)).astype(np.uint8)


def region_mask(region: dict, n: int) -> int:
    m = 0
    for c in region_cells(region, n):
        m |= 1 << cell_index(c, n)
    return m


def _count(models, mask: int):
    if isinstance(models, np.ndarray):
        x = models & np.uint32(mask)
        return _PC16[x & np.uint32(0xFFFF)] + _PC16[x >> np.uint32(16)]
    return bin(models & mask).count("1")


def _bit(models, i: int):
    if isinstance(models, np.ndarray):
        return ((models >> np.uint32(i)) & np.uint32(1)).astype(bool)
    return bool((models >> i) & 1)


def evaluate(clue: dict, models, n: int):
    """True where the clue holds. Returns bool or bool-array matching `models`."""
    t = clue["type"]
    if t == "FACT":
        return _bit(models, cell_index(clue["cell"], n)) == (clue["status"] == "CRIMINAL")
    if t == "SAME":
        return _bit(models, cell_index(clue["a"], n)) == _bit(models, cell_index(clue["b"], n))
    if t == "DIFFERENT":
        return _bit(models, cell_index(clue["a"], n)) != _bit(models, cell_index(clue["b"], n))
    if t in ("EXACTLY", "AT_LEAST", "AT_MOST"):
        cnt = _count(models, region_mask(clue["region"], n))
        k = clue["k"]
        return cnt == k if t == "EXACTLY" else (cnt >= k if t == "AT_LEAST" else cnt <= k)
    if t == "PARITY":
        cnt = _count(models, region_mask(clue["region"], n))
        return (cnt % 2) == (0 if clue["parity"] == "EVEN" else 1)
    if t == "COMPARE":
        a = _count(models, region_mask(clue["left"], n))
        b = _count(models, region_mask(clue["right"], n))
        return {"<": a < b, "==": a == b, ">": a > b}[clue["op"]]
    raise ValueError(f"unknown clue type {t!r}")


def assignment_to_mask(assignment: dict, n: int) -> int:
    """{'A1': True/'CRIMINAL', ...} -> bitmask (criminal = 1)."""
    m = 0
    for c, v in assignment.items():
        if v is True or v == "CRIMINAL":
            m |= 1 << cell_index(c, n)
    return m


# ---------------------------------------------------------------- text ----
def _region_text(region: dict, names: dict) -> str:
    nm = lambda c: names.get(c, c)  # noqa: E731
    k = region["kind"]
    if k == "row":
        return f"row {region['row']}"
    if k == "column":
        return f"column {region['col']}"
    if k == "neighbors":
        return f"the neighbors of {nm(region['of'])}"
    cs = [nm(c) for c in region["cells"]]
    return ", ".join(cs[:-1]) + (" and " if len(cs) > 1 else "") + cs[-1]


def clue_to_text(clue: dict, names: dict | None = None) -> str:
    """Human-readable English rendering (for the GUI / report)."""
    names = names or {}
    nm = lambda c: names.get(c, c)  # noqa: E731
    t = clue["type"]
    if t == "FACT":
        return f"{nm(clue['cell'])} is {'a criminal' if clue['status'] == 'CRIMINAL' else 'an innocent'}"
    if t == "SAME":
        return f"{nm(clue['a'])} and {nm(clue['b'])} have the same status"
    if t == "DIFFERENT":
        return f"{nm(clue['a'])} and {nm(clue['b'])} have different statuses"
    if t in ("EXACTLY", "AT_LEAST", "AT_MOST"):
        word = {"EXACTLY": "Exactly", "AT_LEAST": "At least", "AT_MOST": "At most"}[t]
        return f"{word} {clue['k']} criminal(s) among {_region_text(clue['region'], names)}"
    if t == "PARITY":
        return f"{'An even' if clue['parity'] == 'EVEN' else 'An odd'} number of criminals among {_region_text(clue['region'], names)}"
    if t == "COMPARE":
        rel = {"<": "fewer criminals than", "==": "as many criminals as", ">": "more criminals than"}[clue["op"]]
        return f"{_region_text(clue['left'], names).capitalize()} has {rel} {_region_text(clue['right'], names)}"
    return str(clue)