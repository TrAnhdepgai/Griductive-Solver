"""In các bảng số liệu của báo cáo ra terminal (cùng cột, cùng cách ghi số) để chụp màn hình.

Đặt file này ở thư mục gốc của repo rồi chạy:

    python print_report_tables.py summary        # Bảng tab:exp-summary   (mục 06)
    python print_report_tables.py detail         # Bảng tab:exp-detail    (mục 06)
    python print_report_tables.py stress         # Bảng tab:exp-stress    (mục 06)
    python print_report_tables.py naive-pruned   # Bảng tab:naive-pruned  (mục 05)
    python print_report_tables.py trace          # Bảng tab:trace         (mục 05)
    python print_report_tables.py cross          # Bảng tab:cross         (mục 04)
    python print_report_tables.py all            # in tất cả

summary / detail / stress đọc kết quả benchmark có sẵn trong experiments/results/
(chính là số liệu đang dùng trong báo cáo). Muốn đo lại từ đầu thì chạy trước:

    python tools/benchmark.py --backend team --timeout 60 --repeats 3
    python tools/benchmark.py --backend team --heuristic jw --tag team_pruned_jw --timeout 60 --repeats 3
    python tools/benchmark.py --backend team --strategy naive --tag team_naive_first --timeout 60 --repeats 3
    python tools/benchmark.py --backend reference --timeout 60 --repeats 3
    python tools/benchmark.py --backend team --puzzles experiments/stress_puzzles --tag stress_and_edge --timeout 60 --repeats 3
    python tools/benchmark.py --backend team --puzzles experiments/stress_puzzles --only 5x5_hard_903 --tag stress_timeout_test --timeout 0.05

naive-pruned / trace / cross chạy trực tiếp trên code hiện tại.
"""
import csv
import glob
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.stdout.reconfigure(encoding="utf-8")
RESULTS = ROOT / "experiments" / "results"


# ----------------------------------------------------------------- vẽ bảng
def num(x, d=0):
    """Số kiểu báo cáo: 1 090,8 (cách hàng nghìn bằng khoảng trắng, phẩy thập phân)."""
    s = f"{x:,.{d}f}"
    return s.replace(",", " ").replace(".", ",")


def table(title, head, groups, align):
    """groups: danh sách nhóm hàng, giữa các nhóm có đường kẻ.
    align: mỗi cột một ký tự, 'l' căn trái, 'r' căn phải (vd "llrrr")."""
    rows = [r for g in groups for r in g]
    w = [max(len(str(x)) for x in col) for col in zip(head, *rows)]
    line = lambda l, m, r: l + m.join("─" * (x + 2) for x in w) + r
    cell = lambda i, c: f" {str(c):<{w[i]}} " if align[i] == "l" else f" {str(c):>{w[i]}} "
    fmt = lambda cells: "│" + "│".join(cell(i, c) for i, c in enumerate(cells)) + "│"
    print(f"\n{title}\n")
    print(line("┌", "┬", "┐")); print(fmt(head)); print(line("├", "┼", "┤"))
    for gi, g in enumerate(groups):
        for r in g:
            print(fmt(r))
        if gi < len(groups) - 1:
            print(line("├", "┼", "┤"))
    print(line("└", "┴", "┘"))


def load_csv(name):
    path = RESULTS / f"benchmark_{name}.csv"
    if not path.exists():
        sys.exit(f"Thiếu {path.relative_to(ROOT)}: chạy các lệnh tools/benchmark.py ở đầu file trước.")
    with open(path, encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ----------------------------------------------------------------- mục 06
def summary():
    configs = [("Team (pruned+first)", "team"), ("Team (pruned+jw)", "team_pruned_jw"),
               ("Team (naive+first)", "team_naive_first"), ("Reference (brute-force)", "reference")]
    data = {tag: load_csv(tag) for _, tag in configs}
    groups = []
    for n in ("3", "4", "5"):
        by = {tag: [r for r in rows if r["size"] == n] for tag, rows in data.items()}
        naive_sat = mean(float(r["sat_calls"]) for r in by["team_naive_first"])
        g = []
        for i, (label, tag) in enumerate(configs):
            rs = by[tag]
            first = [f"{n}x{n}", str(len(rs))] if i == 0 else ["", ""]
            t = num(mean(float(r["runtime_s"]) for r in rs) * 1000, 2)
            if tag == "reference":
                g.append(first + [label, "---", "---", "---", "---", "---", "---", t])
                continue
            m = lambda k: mean(float(r[k]) for r in rs)
            sat = m("sat_calls")
            red = "gốc" if tag == "team_naive_first" else f"−{num((1 - sat / naive_sat) * 100, 1)}%"
            g.append(first + [label, num(m("clauses"), 1), num(sat, 1), red, num(m("decisions"), 1),
                              num(m("propagations"), 1), num(sum(int(r["backtracks"]) for r in rs)), t])
        groups.append(g)
    table("Bảng tab:exp-summary — Tổng hợp benchmark trên 31 puzzle (TB: trung bình; Tổng BT: tổng quay lui)",
          ["Lưới", "Số bài", "Cấu hình", "Clauses TB", "SAT calls TB", "Giảm SAT", "Dec. TB",
           "Prop. TB", "Tổng BT", "Time TB (ms)"], groups, "lrlrrrrrrr")


def detail_rows(rows):
    out = []
    for r in rows:
        out.append([r["puzzle"], r["status"], r["primary_vars"], r["aux_vars"], num(int(r["clauses"])),
                    r["sat_calls"], num(int(r["decisions"])), num(int(r["propagations"])), r["backtracks"],
                    r["steps"], r["waves"], f"{float(r['runtime_s']):.4f}"])
    return out


def detail():
    rows = load_csv("team")
    level = {"easy": 0, "medium": 1, "hard": 2}
    order = lambda r: (level.get(r["puzzle"].split("_")[1], 9), r["puzzle"])   # easy, medium, hard như báo cáo
    daily = sorted((r for r in rows if r["puzzle"].startswith("daily")), key=lambda r: r["puzzle"])
    groups = [detail_rows(daily)]
    for n in ("3", "4", "5"):
        groups.append(detail_rows(sorted((r for r in rows if r["size"] == n and not r["puzzle"].startswith("daily")),
                                         key=order)))
    table("Bảng tab:exp-detail — Kết quả chi tiết 31 puzzle (pruned + first, trung vị 3 lần chạy, timeout 60s)",
          ["Puzzle", "Status", "Prim.", "Aux.", "Clauses", "SAT calls", "Dec.", "Prop.", "BT", "Steps",
           "Waves", "Time (s)"], groups, "llrrrrrrrrrr")


def stress():
    desc = {"3x3_hard_901": "3x3 + PARITY,CMP", "4x4_hard_902": "4x4 + PARITY,CMP",
            "5x5_hard_903": "5x5 + PARITY,CMP", "edge_inconsistent_3x3": "KB_0 mâu thuẫn",
            "edge_stuck_4x4": "Thiếu ràng buộc"}
    rows = []
    for r in load_csv("stress_and_edge"):
        ok = r["status"] == "OK"
        status = "OK" if ok else "FAIL"
        steps = r["steps"] or "0"
        waves = r["waves"] or "0"
        rows.append([r["puzzle"], desc.get(r["puzzle"], ""), "60s", status, r["primary_vars"], r["aux_vars"],
                     num(int(r["clauses"])), r["sat_calls"], num(int(r["decisions"])),
                     num(int(r["propagations"])), r["backtracks"], steps, waves, f"{float(r['runtime_s']):.4f}"])
    for r in load_csv("stress_timeout_test"):
        rows.append([f"{r['puzzle']} (strict)", "Ngưỡng chặt 50 ms", "0.05s", r["status"]] + ["---"] * 10)
    table("Bảng tab:exp-stress — Stress case (PARITY+COMPARE), FAIL và TIMEOUT",
          ["Case", "Mô tả", "Limit", "Status", "Prim.", "Aux.", "Cl.", "SAT", "Dec.", "Prop.", "BT", "St.",
           "Wv.", "Time (s)"], [rows], "llllrrrrrrrrrr")


# ----------------------------------------------------------------- mục 05
def naive_pruned():
    from src.agent import LocalGameEngine, LogicAgent
    files = sorted(glob.glob(str(ROOT / "puzzles" / "*.json")))
    agg, count = defaultdict(lambda: [0, 0, 0, 0, 0.0]), defaultdict(int)
    for strat in ("naive", "pruned"):
        for f in files:
            p = json.load(open(f, encoding="utf-8"))
            r = LogicAgent(LocalGameEngine(p), heuristic="first", strategy=strat).run()
            s, a = r.sat_stats, agg[(p["size"], strat)]
            a[0] += s.calls; a[1] += s.decisions; a[2] += s.propagations; a[3] += s.backtracks
            a[4] += s.runtime_s * 1000
            count[p["size"]] += strat == "naive"
    groups = []
    for n in sorted(count):
        g = []
        for strat in ("naive", "pruned"):
            c, d, pr, b, ms = agg[(n, strat)]
            g.append([f"{n}x{n} ({count[n]} ván)" if strat == "naive" else "", strat,
                      num(c), num(d), num(pr), num(b), num(ms)])
        groups.append(g)
    table(f"Bảng tab:naive-pruned — Tổng số liệu SAT của agent trên {len(files)} puzzle (heuristic first)",
          ["Lưới", "Chiến lược", "Gọi SAT", "Quyết định", "Lan truyền", "Quay lui", "Thời gian (ms)"],
          groups, "llrrrrr")


def clue_text(c):
    if c["type"] == "FACT":
        return f"FACT({c['cell']}, {'Inno' if c['status'] == 'INNOCENT' else 'Crim'})"
    reg = c.get("region", {})
    kind = reg.get("kind")
    if kind == "cells":
        where = "{" + ",".join(reg["cells"]) + "}"
    elif kind == "neighbors":
        where = f"lân cận {reg['of']}"
    elif kind == "row":
        where = f"hàng {reg['row']}"
    elif kind == "column":
        where = f"cột {reg['col']}"
    else:
        where = json.dumps(reg, ensure_ascii=False)
    return f"{c['type']}({c.get('k', '')},{where})"


def trace(puzzle="puzzles/3x3_easy_01.json"):
    from src.agent import LocalGameEngine, LogicAgent
    p = json.load(open(ROOT / puzzle, encoding="utf-8"))
    res = LogicAgent(LocalGameEngine(p), heuristic="first", strategy="pruned").run()
    rows = []
    for t in res.trace:
        if not t.cell:
            continue
        forced = ", ".join(c for c, v in t.classification.items() if v != "UNKNOWN")
        short = "Crim" if t.verdict == "CRIMINAL" else "Inno"
        new = f"{t.revealed_clue_id}: {clue_text(t.revealed_clue)}" if t.revealed_clue else "—"
        rows.append([t.step, t.wave, t.kb_stats["clauses"], len(t.queries), forced, f"{t.cell} = {short}", new])
    s = res.sat_stats
    table(f"Bảng tab:trace — Trace của {Path(puzzle).stem} (pruned + first)",
          ["Bước", "Wave", "Mệnh đề", "Truy vấn", "Ô bị ép", "Kết luận", "Clue mới lộ"], [rows], "rrrrlll")
    print(f"Kết quả: {res.status}, {res.steps} bước, {res.waves} wave, {s.calls} lần gọi SAT, "
          f"{s.decisions} quyết định, {s.propagations} lan truyền, {s.backtracks} quay lui")


# ----------------------------------------------------------------- mục 04
def cross():
    out = subprocess.run([sys.executable, str(ROOT / "tools" / "cross_check.py")], cwd=ROOT,
                         capture_output=True, text=True, encoding="utf-8").stdout
    rows, total = [], 0
    for n, clues, masks in re.findall(r"N=(\d+): (\d+) clues x (\d+) assignments", out):
        pairs = int(clues) * int(masks)
        total += pairs
        how = "vét cạn" if int(masks) == 2 ** (int(n) ** 2) else "lấy mẫu"
        rows.append([n, clues, f"{masks} ({how})", num(pairs)])
    m = re.search(r"(\d+) checks, (\d+) failures", out)
    foot = [["", "", "Tổng số cặp; số trường hợp sai lệch", f"{num(int(m.group(1)))}; {m.group(2)}"]]
    table("Bảng tab:cross — Đối chiếu evaluator và encoder",
          ["N", "Số clue", "Số phép gán mỗi clue", "Số cặp clue–phép gán"], [rows, foot], "lrrr")


TABLES = {"summary": summary, "detail": detail, "stress": stress, "naive-pruned": naive_pruned,
          "trace": trace, "cross": cross}

if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which == "all":
        for fn in TABLES.values():
            fn()
    elif which in TABLES:
        TABLES[which]()
    else:
        sys.exit(f"Chọn một trong: {', '.join(TABLES)}, all")
