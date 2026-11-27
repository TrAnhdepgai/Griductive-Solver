from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SERVER = ROOT / "src" / "engine" / "gui_server.py"
BRIDGE = ROOT / "gui" / "static" / "engine-bridge.js"
INDEX = ROOT / "gui" / "index.html"

SERVER_HELPERS = '''def _stats(engine):
    """Size of KB_t and DPLL effort needed to classify the current public state."""
    state = engine.public_state()
    cache = engine.__dict__.setdefault("_gui_stats", {})
    key = tuple(sorted(state.proved.items()))
    if key not in cache:
        cls = classify_state(state)
        s = cls.stats.as_dict()
        cache[key] = {"kb": cls.kb.stats(),
                      "sat": {"calls": s["calls"], "decisions": s["decisions"], "propagations": s["propagations"],
                              "backtracks": s["backtracks"], "conflicts": s["conflicts"],
                              "ms": round(s["runtime_s"] * 1000, 3)},
                      "forced": len(cls.forced), "consistent": cls.consistent}
    return cache[key]


def _total(engine):
    tot = {"calls": 0, "decisions": 0, "propagations": 0, "backtracks": 0}
    for v in engine.__dict__.get("_gui_stats", {}).values():
        for k in tot:
            tot[k] += v["sat"][k]
    return tot


'''

SERVER_EDITS = [
    ("from src.agent.agent import LogicAgent, explain",
     "from src.agent.agent import LogicAgent, classify_state, explain"),
    ("def public_payload(pid, session, engine):", SERVER_HELPERS + "def public_payload(pid, session, engine):"),
    ('"steps": len(state.proved) - len(engine._puzzle["initial_revealed"])}',
     '"steps": len(state.proved) - len(engine._puzzle["initial_revealed"]),\n'
     '            "stats": {**_stats(engine), "total": _total(engine)}}'),
    ('if path == "/api/reset": engine.restart(); engine.submissions=0',
     'if path == "/api/reset": engine.restart(); engine.submissions=0; engine.__dict__.pop("_gui_stats", None)'),
    ('result=engine.submit_verdict(body["cell"],body["verdict"])',
     'checked=_stats(engine); result=engine.submit_verdict(body["cell"],body["verdict"])'),
    ('response={"status":result.status,"message":result.message}',
     'response={"status":result.status,"message":result.message,"checked":checked}'),
    ('response["status"]=ACCEPTED',
     'response["status"]=ACCEPTED; response["checked"]=checked'),
    ('result=engine.submit_verdict(hint.cell,hint.verdict)',
     'checked=_stats(engine); result=engine.submit_verdict(hint.cell,hint.verdict)'),
    ('return self.send_json({"status":result.status,"cell":hint.cell,"verdict":hint.verdict})',
     'return self.send_json({"status":result.status,"cell":hint.cell,"verdict":hint.verdict,"checked":checked})'),
]

BRIDGE_BLOCK = '''// ---- Thống kê KB / CNF / SAT (số liệu thật từ backend) ----
(() => {
  const st = document.createElement("style");
  st.textContent = `
    #stats{display:block}
    #stats .st-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(88px,1fr));gap:8px}
    #stats .st{background:var(--cream);border:3px solid var(--ink);border-radius:14px;padding:4px 6px;text-align:center;cursor:help}
    #stats .st b{display:block;font:400 22px/1.2 OldStyle}
    #stats .st span{display:block;font-size:12px;opacity:.85;line-height:1.2}
    #stats .st-sec{font:14px OldStyle;letter-spacing:1px;margin:12px 0 5px;opacity:.75;text-transform:uppercase}`;
  document.head.appendChild(st);
})();
function fmtChecked(ch) {
  if (!ch) return "";
  return ` · KB ${ch.kb.primary_vars}+${ch.kb.aux_vars} biến, ${ch.kb.clauses} clause · ${ch.sat.calls} SAT, ${ch.sat.decisions} decisions`;
}
function renderStats() {
  const el = $("#stats"); if (!el) return;
  const s = P && P.stats, box = (v, l, tip) => `<div class="st" title="${tip}"><b>${v}</b><span>${l}</span></div>`;
  let h = `<div class="st-row">${box(steps, "bước engine", "Số verdict đã được chấp nhận")}${box(Object.keys(rev).length + "/" + cells.length, "đã lật", "Số thẻ đã lật / tổng số thẻ")}${box(s ? s.forced : "–", "ô ép được", "Số ô chưa lật mà KB hiện tại chứng minh được")}</div>`;
  if (s) {
    h += `<div class="st-sec">Knowledge Base KB<sub>t</sub> (CNF)</div><div class="st-row">`
      + box(s.kb.primary_vars, "biến chính", "Biến C_i: mỗi nhân vật một biến")
      + box(s.kb.aux_vars, "biến phụ", "Biến phụ do bộ mã hóa thêm vào")
      + box(s.kb.clauses, "clause", "Số mệnh đề CNF của KB hiện tại") + `</div>`
      + `<div class="st-sec">DPLL · phân loại trạng thái hiện tại</div><div class="st-row">`
      + box(s.sat.calls, "lần gọi SAT", "Số truy vấn KB ∧ ¬C_i / KB ∧ C_i")
      + box(s.sat.decisions, "decisions", "Số lần DPLL phải rẽ nhánh")
      + box(s.sat.propagations, "propagations", "Số literal suy ra bằng unit propagation")
      + box(s.sat.backtracks, "backtracks", "Số lần quay lui")
      + box(s.sat.ms + " ms", "thời gian", "Thời gian giải SAT cho trạng thái này") + `</div>`
      + `<div class="st-sec">Tổng cả ván</div><div class="st-row">`
      + box(s.total.calls, "lần gọi SAT", "Cộng dồn qua mọi trạng thái đã đi qua")
      + box(s.total.decisions, "decisions", "Cộng dồn")
      + box(s.total.propagations, "propagations", "Cộng dồn")
      + box(s.total.backtracks, "backtracks", "Cộng dồn") + `</div>`;
  }
  el.innerHTML = h;
}
'''

BRIDGE_EDITS = [
    ('if (stats) stats.innerHTML = `<span>Bước engine: <b>${steps}</b></span><span>Đã lật: <b>${Object.keys(rev).length}/${cells.length}</b></span>`;',
     'if (stats) renderStats();'),
    ('function acceptEngineState(p, explicitFlip = null) {',
     BRIDGE_BLOCK + 'function acceptEngineState(p, explicitFlip = null) {'),
    ('log(`${c} ${nm(c)}: ${L[v]} (engine SAT)`)',
     'log(`${c} ${nm(c)}: ${L[v]} (engine SAT${fmtChecked(out.checked)})`)'),
    ('log(`${r.cell} ${nm(r.cell)}: ${L[r.verdict]} (agent SAT)`)',
     'log(`${r.cell} ${nm(r.cell)}: ${L[r.verdict]} (agent SAT${fmtChecked(r.checked)})`)'),
    ('toast(msg, "warn"); return;',
     'log(`${c} ${nm(c)}: ${out.status}${fmtChecked(out.checked)}`); toast(msg, "warn"); return;'),
]


def read(path):
    with open(path, encoding="utf-8", newline="") as f:
        return f.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)


def plan(path, edits, marker):
    if not path.exists():
        return None, [f"Không thấy file {path}"]
    s = read(path)
    if marker in s:
        return None, []
    nl = "\r\n" if "\r\n" in s else "\n"
    problems = []
    for anchor, repl in edits:
        n = s.count(anchor)
        if n != 1:
            problems.append(f"{path.name}: tìm thấy {n} lần (cần đúng 1) đoạn: {anchor[:70]!r}")
            continue
        s = s.replace(anchor, repl.replace("\n", nl))
    return s, problems


def main():
    new_server, p1 = plan(SERVER, SERVER_EDITS, "_gui_stats")
    new_bridge, p2 = plan(BRIDGE, BRIDGE_EDITS, "renderStats")
    problems = p1 + p2
    if problems:
        print("KHÔNG sửa file nào, vì có chỗ không khớp:")
        for p in problems:
            print("  -", p)
        return 1
    changed = []
    for path, new in ((SERVER, new_server), (BRIDGE, new_bridge)):
        if new is None:
            print(f"Đã vá từ trước, bỏ qua: {path.relative_to(ROOT)}")
            continue
        shutil.copyfile(path, path.with_suffix(path.suffix + ".bak"))
        write(path, new)
        changed.append(path)
        print(f"Đã vá: {path.relative_to(ROOT)}  (sao lưu: {path.name}.bak)")
    if changed and INDEX.exists():
        html = read(INDEX)
        m = re.search(r"(engine-bridge\.js\?v=)(\d+)", html)
        if m:
            write(INDEX, html.replace(m.group(0), f"{m.group(1)}{int(m.group(2)) + 1}", 1))
            print(f"Đã tăng version: engine-bridge.js?v={int(m.group(2)) + 1}")
    print("\nXong. Tắt server cũ (Ctrl+C), chạy lại `python main.py`, rồi Ctrl+F5.")
    return 0


if __name__ == "__main__":
    sys.exit(main())