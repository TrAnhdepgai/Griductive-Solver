"""Generate publication-quality charts and summary tables from benchmark results (member D).

Reads experiments/results/benchmark_*.json and writes PNG charts to experiments/charts/.
Usage:
  python tools/plot_experiments.py
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "experiments" / "results"
CHARTS = ROOT / "experiments" / "charts"


def load_json(name: str) -> list[dict]:
    return json.loads((RESULTS / f"benchmark_{name}.json").read_text(encoding="utf-8"))


def mean(vals: list[float]) -> float:
    return statistics.mean(vals) if vals else 0.0


def median(vals: list[float]) -> float:
    return statistics.median(vals) if vals else 0.0


def set_style() -> None:
    plt.rcParams.update({
        "figure.dpi": 160,
        "savefig.dpi": 180,
        "font.size": 10,
        "axes.titlesize": 11.5,
        "axes.titleweight": "bold",
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.alpha": 0.28,
        "grid.linestyle": "--",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "legend.framealpha": 0.92,
    })


def fig1_runtime_scaling(team, jw, naive, ref, stress) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8))
    sizes = [3, 4, 5]
    x = np.arange(len(sizes))
    w = 0.19

    series = [
        ("Team DPLL (pruned + first)", team, "#2563EB"),
        ("Team DPLL (pruned + jw)", jw, "#0EA5E9"),
        ("Team DPLL (naive + first)", naive, "#F59E0B"),
        ("Reference (NumPy brute-force)", ref, "#EF4444"),
    ]
    for idx, (label, data, color) in enumerate(series):
        vals = [mean([r["runtime_s"] for r in data if r["size"] == s and r["status"] == "OK"]) for s in sizes]
        bars = ax1.bar(x + (idx - 1.5) * w, vals, w, label=label, color=color, edgecolor="white", linewidth=0.6)
        for b, v in zip(bars, vals):
            ax1.text(b.get_x() + b.get_width() / 2, v * 1.12, f"{v*1000:.1f}ms",
                     ha="center", va="bottom", fontsize=7.5, rotation=45)

    ax1.set_yscale("log")
    ax1.set_ylim(2e-4, 2.0)
    ax1.set_xticks(x)
    counts = [sum(1 for r in team if r["size"] == s) for s in sizes]
    ax1.set_xticklabels([f"{s}×{s} (n={c})" for s, c in zip(sizes, counts)])
    ax1.set_ylabel("Mean Runtime (seconds, log scale)")
    ax1.set_title("Runtime Scaling: DPLL Agent vs. Brute-Force")
    ax1.legend(loc="upper left", fontsize=8.5)

    # Right subplot: runtime distribution per puzzle size + extension stress case
    groups = [
        ("3×3\nstd", [r["runtime_s"] * 1000 for r in team if r["size"] == 3]),
        ("4×4\nstd", [r["runtime_s"] * 1000 for r in team if r["size"] == 4]),
        ("5×5\nstd", [r["runtime_s"] * 1000 for r in team if r["size"] == 5]),
        ("5×5\nPARITY+CMP", [r["runtime_s"] * 1000 for r in stress if r["puzzle"] == "5x5_hard_903"]),
    ]
    labels = [g[0] for g in groups]
    means = [mean(g[1]) for g in groups]
    maxs = [max(g[1]) for g in groups]
    mins = [min(g[1]) for g in groups]
    colors = ["#3B82F6", "#2563EB", "#1D4ED8", "#7C3AED"]
    bars2 = ax2.bar(labels, means, width=0.52, color=colors, edgecolor="white")
    for idx, (b, m, lo, hi) in enumerate(zip(bars2, means, mins, maxs)):
        if hi > lo:
            ax2.errorbar(b.get_x() + b.get_width() / 2, m, yerr=[[m - lo], [hi - m]],
                         fmt="none", ecolor="#1E293B", capsize=4, linewidth=1.2)
        ax2.text(b.get_x() + b.get_width() / 2, hi + 6, f"{m:.1f} ms",
                 ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax2.set_ylim(0, max(maxs) * 1.18)
    ax2.set_ylabel("Runtime (ms)")
    ax2.set_title("Team DPLL (pruned + first): Standard vs. Extension Stress")

    fig.tight_layout()
    fig.savefig(CHARTS / "fig1_runtime_scaling.png")
    plt.close(fig)


def fig2_sat_calls(team, jw, naive) -> None:
    fig, ax = plt.subplots(figsize=(8.6, 4.6))
    sizes = [3, 4, 5]
    x = np.arange(len(sizes))
    w = 0.25

    m_naive = [mean([r["sat_calls"] for r in naive if r["size"] == s]) for s in sizes]
    m_pruned = [mean([r["sat_calls"] for r in team if r["size"] == s]) for s in sizes]
    m_jw = [mean([r["sat_calls"] for r in jw if r["size"] == s]) for s in sizes]

    b1 = ax.bar(x - w, m_naive, w, label="Naive (2 calls / unknown)", color="#F59E0B", edgecolor="white")
    b2 = ax.bar(x, m_pruned, w, label="Pruned + first (witness reuse)", color="#2563EB", edgecolor="white")
    b3 = ax.bar(x + w, m_jw, w, label="Pruned + jw (witness reuse)", color="#0EA5E9", edgecolor="white")

    for bars in (b1, b2, b3):
        for b in bars:
            h = b.get_height()
            ax.text(b.get_x() + b.get_width() / 2, h + 8, f"{h:.1f}", ha="center", va="bottom", fontsize=8.5)

    for i in range(len(sizes)):
        red = (1 - m_pruned[i] / m_naive[i]) * 100
        y_badge = max(m_naive[i] * 0.78, m_pruned[i] + 55)
        ax.annotate(f"-{red:.1f}%", xy=(x[i], m_pruned[i] + 22), xytext=(x[i] + 0.06, y_badge),
                    ha="center", fontsize=9, fontweight="bold", color="#1D4ED8",
                    bbox=dict(boxstyle="round,pad=0.22", fc="#EFF6FF", ec="#93C5FD", lw=0.8))

    ax.set_xticks(x)
    counts = [sum(1 for r in team if r["size"] == s) for s in sizes]
    ax.set_xticklabels([f"{s}×{s} (n={c})" for s, c in zip(sizes, counts)])
    ax.set_ylabel("Mean SAT Solver Calls per Puzzle")
    ax.set_ylim(0, max(m_naive) * 1.18)
    ax.set_title("SAT Calls Reduction: Witness-Pruned vs. Naive Entailment")
    ax.legend(loc="upper left")
    fig.tight_layout()
    fig.savefig(CHARTS / "fig2_sat_calls_pruned_vs_naive.png")
    plt.close(fig)


def fig3_search_effort_and_waves(team, naive) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.8))
    sizes = [3, 4, 5]
    x = np.arange(len(sizes))
    w = 0.2

    dec_p = [mean([r["decisions"] for r in team if r["size"] == s]) for s in sizes]
    prop_p = [mean([r["propagations"] for r in team if r["size"] == s]) for s in sizes]
    dec_n = [mean([r["decisions"] for r in naive if r["size"] == s]) for s in sizes]
    prop_n = [mean([r["propagations"] for r in naive if r["size"] == s]) for s in sizes]

    ax1.bar(x - 1.5 * w, dec_p, w, label="Decisions (pruned)", color="#2563EB")
    ax1.bar(x - 0.5 * w, dec_n, w, label="Decisions (naive)", color="#93C5FD")
    ax1.bar(x + 0.5 * w, prop_p, w, label="Propagations (pruned)", color="#059669")
    ax1.bar(x + 1.5 * w, prop_n, w, label="Propagations (naive)", color="#6EE7B7")
    ax1.set_yscale("log")
    ax1.set_xticks(x)
    ax1.set_xticklabels(["3×3", "4×4", "5×5"])
    ax1.set_ylabel("Count per Puzzle (log scale)")
    ax1.set_title("DPLL Search Effort: Decisions & Unit Propagations")
    ax1.legend(loc="upper left", fontsize=8.5)

    # Right subplot: Waves by size & difficulty (preset 24 puzzles)
    preset = [r for r in team if not r["puzzle"].startswith("daily_")]
    buckets = [
        ("3×3\neasy", 3, "easy"), ("3×3\nmed", 3, "medium"), ("3×3\nhard", 3, "hard"),
        ("4×4\neasy", 4, "easy"), ("4×4\nmed", 4, "medium"), ("4×4\nhard", 4, "hard"),
        ("5×5\nmed", 5, "medium"), ("5×5\nhard", 5, "hard"),
    ]
    blabels, bmeans, bcolors = [], [], []
    palette = {"easy": "#10B981", "medium": "#F59E0B", "hard": "#EF4444"}
    for lbl, sz, diff in buckets:
        vals = [r["waves"] for r in preset if r["size"] == sz and r["difficulty"] == diff]
        blabels.append(lbl)
        bmeans.append(mean(vals))
        bcolors.append(palette[diff])
    bars = ax2.bar(blabels, bmeans, color=bcolors, width=0.58, edgecolor="white")
    for b, v in zip(bars, bmeans):
        ax2.text(b.get_x() + b.get_width() / 2, v + 0.4, f"{v:.1f}", ha="center", va="bottom", fontsize=8.5)
    ax2.set_ylim(0, max(bmeans) * 1.18)
    ax2.set_ylabel("Mean Deduction Waves")
    ax2.set_title("Deduction Waves by Board Size & Difficulty (24 Preset Puzzles)")

    fig.tight_layout()
    fig.savefig(CHARTS / "fig3_search_effort_and_waves.png")
    plt.close(fig)


def fig4_cnf_size_and_stress(team, stress) -> None:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 4.6))

    cats = ["3×3 std\n(mean)", "4×4 std\n(mean)", "5×5 std\n(mean)",
            "3×3 ext\n(901)", "4×4 ext\n(902)", "5×5 ext\n(903)"]
    ext_map = {r["puzzle"]: r for r in stress}

    prim = [
        9, 16, 25,
        ext_map["3x3_hard_901"]["primary_vars"],
        ext_map["4x4_hard_902"]["primary_vars"],
        ext_map["5x5_hard_903"]["primary_vars"],
    ]
    aux = [
        0, 0, 0,
        ext_map["3x3_hard_901"]["aux_vars"],
        ext_map["4x4_hard_902"]["aux_vars"],
        ext_map["5x5_hard_903"]["aux_vars"],
    ]
    clauses = [
        mean([r["clauses"] for r in team if r["size"] == 3]),
        mean([r["clauses"] for r in team if r["size"] == 4]),
        mean([r["clauses"] for r in team if r["size"] == 5]),
        ext_map["3x3_hard_901"]["clauses"],
        ext_map["4x4_hard_902"]["clauses"],
        ext_map["5x5_hard_903"]["clauses"],
    ]

    x = np.arange(len(cats))
    ax1.bar(x, prim, width=0.52, label="Primary vars ($N^2$)", color="#2563EB")
    ax1.bar(x, aux, width=0.52, bottom=prim, label="Auxiliary vars (PARITY/COMPARE)", color="#7C3AED")
    for i, (p, a) in enumerate(zip(prim, aux)):
        ax1.text(i, p + a + 1.2, f"{p}+{a}", ha="center", va="bottom", fontsize=8.5)
    ax1.set_xticks(x)
    ax1.set_xticklabels(cats, fontsize=8.5)
    ax1.set_ylim(0, max(p + a for p, a in zip(prim, aux)) * 1.18)
    ax1.set_ylabel("Variables in Max $KB_t$")
    ax1.set_title("Primary & Auxiliary Variables: Core vs. Extensions")
    ax1.legend(loc="upper left", fontsize=8.5)

    c_colors = ["#3B82F6", "#2563EB", "#1D4ED8", "#A78BFA", "#8B5CF6", "#6D28D9"]
    bars = ax2.bar(x, clauses, width=0.52, color=c_colors)
    for i, v in enumerate(clauses):
        ax2.text(i, v + 22, f"{v:.0f}", ha="center", va="bottom", fontsize=8.5, fontweight="bold")
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats, fontsize=8.5)
    ax2.set_ylim(0, max(clauses) * 1.16)
    ax2.set_ylabel("Clauses in Max $KB_t$")
    ax2.set_title("CNF Clause Growth: Core vs. Extension Stress Cases")

    fig.tight_layout()
    fig.savefig(CHARTS / "fig4_cnf_size_and_stress.png")
    plt.close(fig)


def print_summary(team, jw, naive, ref) -> None:
    print(f"=== SUMMARY BY SIZE (ALL {len(team)} PUZZLES) ===")
    for s in (3, 4, 5):
        t = [r for r in team if r["size"] == s]
        j = [r for r in jw if r["size"] == s]
        n = [r for r in naive if r["size"] == s]
        rf = [r for r in ref if r["size"] == s]
        print(
            f"Size {s}x{s} (count={len(t)}): "
            f"clauses={mean([r['clauses'] for r in t]):.1f} (max {max(r['clauses'] for r in t)}), "
            f"sat_pruned={mean([r['sat_calls'] for r in t]):.1f}, "
            f"sat_naive={mean([r['sat_calls'] for r in n]):.1f} "
            f"(-{(1 - mean([r['sat_calls'] for r in t])/mean([r['sat_calls'] for r in n]))*100:.1f}%), "
            f"dec_p={mean([r['decisions'] for r in t]):.1f}, "
            f"prop_p={mean([r['propagations'] for r in t]):.1f}, "
            f"bt_p={sum(r['backtracks'] for r in t)}, bt_jw={sum(r['backtracks'] for r in j)}, bt_n={sum(r['backtracks'] for r in n)}, "
            f"steps={mean([r['steps'] for r in t]):.1f}, waves={mean([r['waves'] for r in t]):.1f}, "
            f"time_p={mean([r['runtime_s'] for r in t])*1000:.2f}ms (med {median([r['runtime_s'] for r in t])*1000:.2f}ms), "
            f"time_jw={mean([r['runtime_s'] for r in j])*1000:.2f}ms, "
            f"time_n={mean([r['runtime_s'] for r in n])*1000:.2f}ms, "
            f"time_ref={mean([r['runtime_s'] for r in rf])*1000:.2f}ms"
        )


def main() -> int:
    CHARTS.mkdir(parents=True, exist_ok=True)
    set_style()
    team = load_json("team")
    jw = load_json("team_pruned_jw")
    naive = load_json("team_naive_first")
    ref = load_json("reference")
    stress = load_json("stress_and_edge")

    fig1_runtime_scaling(team, jw, naive, ref, stress)
    fig2_sat_calls(team, jw, naive)
    fig3_search_effort_and_waves(team, naive)
    fig4_cnf_size_and_stress(team, stress)
    print_summary(team, jw, naive, ref)
    print(f"\nSaved 4 charts to {CHARTS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
