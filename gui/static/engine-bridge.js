// Browser adapter: all game state and deductions come from the team's Python engine.
// Mặc định gọi API cùng origin với trang (đúng với mọi cổng khi chạy --port).
// Chỉ khi mở thẳng file (file://) mới dùng cổng mặc định 8001; có thể ghi đè bằng ?api=http://127.0.0.1:PORT
const API_BASE = new URLSearchParams(location.search).get("api")
  || (location.protocol === "file:" ? "http://127.0.0.1:8001" : "");
const api = async (path, body) => {
  let r;
  try { r = await fetch(API_BASE + path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {}); }
  catch (_) { throw Error("Chưa kết nối engine. Hãy chạy: python -m src.engine.gui_server"); }
  const type = r.headers.get("content-type") || "";
  if (!type.includes("application/json")) throw Error("API trả về trang HTML. Hãy chạy GUI qua python -m src.engine.gui_server rồi mở đúng địa chỉ in ra trên terminal.");
  const data = await r.json(); if (!r.ok) throw Error(data.error || "Lỗi kết nối engine"); return data;
};
let enginePuzzleIds = [], gameSession = null;
let hintColorGroups = { first: new Set(), second: new Set(), people: new Set() }, hintScopes = [];
const plainClueText = clueText;
function colorizeHintText(node, k) {
  const text = plainClueText(k), colors = Array(text.length).fill(null), rank = { "hint-range-one": 1, "hint-range-two": 2, "hint-character-text": 3 };
  const mark = (term, cls) => { if (!term) return; let from = 0, lower = text.toLocaleLowerCase(), needle = term.toLocaleLowerCase(); while ((from = lower.indexOf(needle, from)) >= 0) { for (let i = from; i < from + needle.length; i++)if (!colors[i] || rank[cls] > rank[colors[i]]) colors[i] = cls; from += needle.length; } };
  if (k.left && k.right) { mark(rt(k.left), "hint-range-one"); mark(rt(k.right), "hint-range-two"); }
  else if (k.region) mark(rt(k.region), "hint-range-one");
  const people = [k.region && k.region.cell, k.cell, k.a, k.b].filter(c => c && P.characters[c]);
  people.forEach(c => mark(nm(c), "hint-character-text"));
  let start = 0;
  while (start < text.length) {
    const cls = colors[start]; let end = start + 1; while (end < text.length && colors[end] === cls) end++; const part = text.slice(start, end);
    if (cls) { const span = document.createElement("span"); span.className = cls; span.textContent = part; node.append(span); } else node.append(document.createTextNode(part)); start = end;
  }
}
const legacyDraw = draw;
draw = function (flipped) {
  legacyDraw();
  document.querySelectorAll("#board .cell").forEach(card => {
    const c = card.dataset.c;
    if (!rev[c] || !P.clues[c]) return;
    card.classList.add("has-clue");
    const note = document.createElement("span"); note.className = "inline-clue"; colorizeHintText(note, P.clues[c]);
    card.querySelector(".face").append(note);
    card.setAttribute("aria-label", `${c} ${nm(c)}, ${L[rev[c]]}. ${note.textContent}`);
  });
  const stats = $("#stats");
  if (stats) renderStats();
  if (flipped) requestAnimationFrame(() => {
    const face = document.querySelector(`#board .cell[data-c="${flipped}"] .face`);
    if (face) {
      face.getAnimations().forEach(animation => animation.cancel()); face.animate(
        [{ transform: "rotateY(180deg) scale(.9)" }, { transform: "none" }],
        { duration: 600, easing: "cubic-bezier(.3, 1.3, .5, 1)" }
      );
    }
  });
};
// ---- 4x4 / 5x5: keep clues readable on small cards ----
// 1) shrink the clue text until it fits its card (marks it .clipped if even the minimum is too big)
// 2) selecting a revealed card shows its full clue in a popup next to it
function fitClues() {
  document.querySelectorAll("#board .inline-clue").forEach(note => {
    note.style.fontSize = ""; note.classList.remove("clipped");
    let fs = parseFloat(getComputedStyle(note).fontSize);
    while (fs > 8 && note.scrollHeight > note.clientHeight + 1) { fs -= .5; note.style.fontSize = fs + "px"; }
    if (note.clientHeight > 0 && note.scrollHeight > note.clientHeight + 1) note.classList.add("clipped");
  });
}
function closeCluePop() { const e = document.getElementById("cluePop"); if (e) e.remove(); }
function showCluePop() {
  closeCluePop();
  if (!sel || !rev[sel] || !P.clues[sel]) return;
  const card = document.querySelector(`#board .cell[data-c="${sel}"]`);
  const clipped = card && card.querySelector(".inline-clue.clipped");
  const hidden = card && getComputedStyle(card.querySelector(".inline-clue") || card).display === "none";
  if (!card || !(N >= 4 || clipped || hidden)) return;
  const box = document.getElementById("board").closest(".board-box"), br = box.getBoundingClientRect(), cr = card.getBoundingClientRect();
  const pop = document.createElement("div"); pop.id = "cluePop"; pop.className = "clue-pop"; pop.setAttribute("role", "status");
  const title = document.createElement("b"); title.textContent = `${nm(sel)} (${sel})`;
  const text = document.createElement("p"); text.textContent = plainClueText(P.clues[sel]);
  pop.append(title, text); box.append(pop);
  const pw = pop.offsetWidth, ph = pop.offsetHeight;
  let left = cr.left - br.left + cr.width / 2 - pw / 2; left = Math.max(8, Math.min(left, br.width - pw - 8));
  let top = cr.bottom - br.top + 8; if (top + ph > br.height - 8) top = cr.top - br.top - ph - 8;
  pop.style.left = left + "px"; pop.style.top = Math.max(8, top) + "px";
}
const drawWithClues = draw;
function makeHintColorGroups(clueIds) {
  hintColorGroups = { first: new Set(), second: new Set(), people: new Set() }; hintScopes = [];
  if (hintCell) hintColorGroups.people.add(hintCell);
  const addScope = r => { if (!r) return; const group = hintScopes.length === 0 ? hintColorGroups.first : hintColorGroups.second; region(r).forEach(c => group.add(c)); hintScopes.push(r); if (r.kind === "NEIGHBORS") hintColorGroups.people.add(r.cell); };
  (clueIds || []).forEach(id => {
    const k = P.clues[id]; if (!k) return;
    if (k.left && k.right) { addScope(k.left); addScope(k.right); } else if (k.region) addScope(k.region);
    [k.cell, k.a, k.b].filter(c => c && P.characters[c]).forEach(c => hintColorGroups.people.add(c));
  });
}
function showHintSummary(h) {
  const host = $("#toast"); host.textContent = ""; const pill = document.createElement("span"); pill.className = "pill warn hint-message";
  pill.append("Gợi ý cho "); const who = document.createElement("strong"); who.className = "hint-character-text"; who.textContent = `${nm(h.cell)} (${h.cell})`; pill.append(who, ` là ${L[h.verdict].toLowerCase()}.`);
  hintScopes.slice(0, 2).forEach((r, i) => {
    const scope = document.createElement("strong"); scope.className = i === 0 ? "hint-range-one" : "hint-range-two"; const label = i === 0 ? "Vùng 1" : "Vùng 2";
    if (r.kind === "NEIGHBORS") { scope.append(` ${label}: hàng xóm của `); const name = document.createElement("span"); name.className = "hint-character-text"; name.textContent = nm(r.cell); scope.append(name, "."); }
    else scope.textContent = ` ${label}: ${rt(r)}.`;
    pill.append(scope);
  }); host.append(pill);
}
draw = function (flipped) {
  drawWithClues(flipped); document.body.dataset.n = N;
  const board = document.getElementById("board"), selectedClue = Boolean(sel && rev[sel] && P.clues[sel]), active = Boolean(hl.length && (hintCell || selectedClue)); board.classList.toggle("hint-active", active);
  board.querySelectorAll(".cell").forEach(card => {
    card.classList.remove("hint-marked", "hint-person", "hint-target", "focus-card", "dimmed"); card.style.removeProperty("--border-left"); card.style.removeProperty("--border-right");
    const c = card.dataset.c, roles = [];
    if (hintColorGroups.people.has(c)) { roles.push("#78B987"); card.classList.add("hint-person"); }
    if (hintColorGroups.first.has(c)) roles.push("#FF4D94");
    if (hintColorGroups.second.has(c)) roles.push("#26B5D2");
    if (active && roles.length) { card.classList.add("hint-marked"); card.style.setProperty("--border-left", roles[0]); card.style.setProperty("--border-right", roles[1] || roles[0]); }
    else if (active && c === sel && selectedClue) card.classList.add("focus-card");
    else if (active) card.classList.add("dimmed");
    if (active && c === hintCell) card.classList.add("hint-target");
  });
  fitClues(); showCluePop();
};
let clueFitFrame = 0;
window.addEventListener("resize", () => { cancelAnimationFrame(clueFitFrame); clueFitFrame = requestAnimationFrame(() => { fitClues(); showCluePop(); }); });
// composedPath(): the clicked card is already re-rendered (detached) when the event reaches document
document.addEventListener("click", e => { if (!e.composedPath().some(n => n.id === "board")) closeCluePop(); });
document.addEventListener("keydown", e => { if (e.key === "Escape") closeCluePop(); });
$("#clue").closest(".card").hidden = true;
$(".side").append($("#toast"));
// ---- Thống kê KB / CNF / SAT (số liệu thật từ backend) ----
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
      + box(s.kb.clauses, "clause", "Số mệnh đề CNF của KB hiện tại (clue đã lật + verdict đã chứng minh)") + `</div>`
      + `<div class="st-sec">DPLL · phân loại trạng thái hiện tại</div><div class="st-row">`
      + box(s.sat.calls, "lần gọi SAT", "Số truy vấn KB ∧ ¬C_i / KB ∧ C_i để xếp loại các ô chưa lật")
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
// Cell notes ("lời khai hết giá trị", nghi vô tội / có tội) belong to ONE puzzle. Cells are named the
// same in every puzzle (A1, B2...), so they are stored per puzzle id and swapped in when a new game starts.
const NOTES_KEY = "griductive.notes.v1";
let notesByPuzzle = {};
try { notesByPuzzle = JSON.parse(localStorage.getItem(NOTES_KEY) || "{}") || {}; } catch (_) { notesByPuzzle = {}; }
const notesKey = p => (p && p.id) || "custom";
function persistNotes() {
  const k = notesKey(P);
  if (Object.keys(notes).length) notesByPuzzle[k] = { ...notes }; else delete notesByPuzzle[k];
  try { localStorage.setItem(NOTES_KEY, JSON.stringify(notesByPuzzle)); } catch (_) { }
}
const saveBase = save;
save = function () { saveBase(); persistNotes(); };
function acceptEngineState(p, explicitFlip = null) {
  const newSession = gameSession !== p.session;
  if (!curDate) { curDate = today(); viewMon = monday(curDate); }
  const sameSession = gameSession && gameSession === p.session;
  const newlyFlipped = sameSession ? Object.keys(p.revealed || {}).find(c => !rev[c]) : null;
  const flipped = explicitFlip || newlyFlipped;
  P = p; gameSession = p.session; N = p.size; cells = Object.keys(p.characters); rev = { ...p.revealed };
  if (newSession) { elapsed = 0; last = performance.now(); renderClock(); notes = { ...(notesByPuzzle[notesKey(p)] || {}) }; }
  P.initial_revealed = Object.keys(rev); solved = Object.keys(rev).length === cells.length;
  steps = p.steps || 0; sat = 0; sel = null; hl = flipped && P.clues[flipped] ? clueCells(P.clues[flipped]) : []; hintCell = null; hintScopes = []; hintColorGroups = { first: new Set(), second: new Set(), people: new Set() };
  if (flipped && P.clues[flipped]) $("#clue").innerHTML = `<b>Manh mối mới của ${nm(flipped)}:</b> ${clueText(P.clues[flipped])}`;
  draw(flipped || undefined); infoLine();
}
async function startEnginePuzzle(index = 0) {
  const meta = enginePuzzleIds[index % enginePuzzleIds.length]; if (!meta) return;
  curDate = curDate || today(); viewMon = monday(curDate);
  const p = await api("/api/start", { id: meta.id }); acceptEngineState(p);
  renderWeek();
  $("#dayinfo").textContent = `${meta.id} · ${p.size}×${p.size}`;
}
load = function (p) { acceptEngineState(p); };
// Puzzle list is sorted by file name, so "thu" comes before "wed": pick the daily puzzle by its weekday suffix, not by position.
const DAY_CODES = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"];
function dailyIndex(i) { const j = enginePuzzleIds.findIndex(m => /daily/.test(m.file) && m.file.replace(/\.json$/, "").endsWith("_" + DAY_CODES[i])); return j >= 0 ? j : i; }
// ---- Daily mode: every calendar date has its own puzzle, playable for the last 6 months ----
// The server generates a date's puzzle the first time it is opened (src/engine/daily.py).
let dailyInfo = null, loadingDay = false;
const parseIso = s => { const [y, m, d] = s.split("-").map(Number); return new Date(y, m - 1, d); };
const earliestDay = () => dailyInfo ? parseIso(dailyInfo.earliest) : null;
async function startDailyPuzzle(d) {
  const k = iso(d); if (!(dailyInfo.ready || []).includes(k)) toast(`Đang tạo puzzle cho ngày ${pad(d.getDate())}/${pad(d.getMonth() + 1)}/${d.getFullYear()}…`, "warn");
  const p = await api("/api/start", { date: k }); (dailyInfo.ready = dailyInfo.ready || []).push(k);
  acceptEngineState(p); renderWeek(); infoLine(); $("#toast").textContent = "";
}
selectDate = async function (d) {
  if (busy || loadingDay) return;
  const day = new Date(d); day.setHours(0, 0, 0, 0);
  if (!dailyInfo) { curDate = day; viewMon = monday(curDate); return startEnginePuzzle(dailyIndex((day.getDay() + 6) % 7)); }  // old server: weekday files
  if (day > today() || day < earliestDay()) return toast("Chỉ chơi được các ngày trong 6 tháng gần nhất", "warn");
  curDate = day; viewMon = monday(curDate); loadingDay = true; renderWeek();
  try { await startDailyPuzzle(day); } catch (e) { toast(e.message, "bad"); } finally { loadingDay = false; }
};
// Calendar (week strip + month picker): lock days older than the server's window.
minDay = earliestDay;
pick = async function (c) {
  if (busy || paused) return; sel = c; hintCell = null; hl = []; hintScopes = []; hintColorGroups = { first: new Set(), second: new Set(), people: new Set() };
  if (rev[c]) { $("#clue").innerHTML = `<b>${nm(c)} (${c}):</b> ${clueText(P.clues[c])}`; hl = clueCells(P.clues[c]); if (P.clues[c]) makeHintColorGroups([c]); $("#call").innerHTML = ""; }
  else { $("#clue").textContent = "Thẻ này đang úp. Hãy gọi tên nếu bạn chắc chắn."; $("#call").innerHTML = `<button class="btn pink" data-v="CRIMINAL">${IC("ghost")}Tội phạm</button><button class="btn cyan" data-v="INNOCENT">${IC("love")}Vô tội</button>`; $("#call").querySelectorAll("button").forEach(b => b.onclick = () => call(c, b.dataset.v)); } draw();
};
let submittingVerdict = false;
call = async function (c, v) {
  if (submittingVerdict) return; submittingVerdict = true; $("#call").querySelectorAll("button").forEach(b => b.disabled = true); try {
    const out = await api("/api/call", { id: P.id, session: gameSession, cell: c, verdict: v }); if (out.status !== "ACCEPTED") {
      if (out.state) acceptEngineState(out.state);
      if (out.status === "INVALID") {
        const state = out.state || await api(`/api/state?id=${encodeURIComponent(P.id)}&session=${encodeURIComponent(gameSession)}`);
        if (state.revealed && state.revealed[c]) { const existing = state.revealed[c]; acceptEngineState(state); hl = clueCells(P.clues[c]); $("#clue").innerHTML = `<b>${nm(c)} (${c}):</b> ${clueText(P.clues[c])}`; draw(); toast(`Engine đã ghi nhận ${c} là ${L[existing]}; bàn vừa tải lại trạng thái đó. Nước vừa chọn không được tính.`, "warn"); return; }
      }
      const forced = Object.entries(out.forced || {}).map(([cell, status]) => `${cell}: ${L[status]}`).join(", ");
      const msg = out.status === "CONTRADICTED" ? "Engine đã chứng minh trạng thái ngược lại" : out.status === "NOT_PROVABLE" ? `Chưa đủ căn cứ cho ${c}.${forced ? ` Engine đang suy ra: ${forced}.` : " Hãy bấm Gợi ý để xem kết luận có thể chứng minh."}` : `${out.status}: ${out.message || "Nước đi không hợp lệ."}`;
      log(`${c} ${nm(c)}: ${out.status}${fmtChecked(out.checked)}`); toast(msg, "warn"); return;
    }
    const p = await api(`/api/state?id=${encodeURIComponent(P.id)}&session=${encodeURIComponent(gameSession)}`); acceptEngineState(p, c); log(`${c} ${nm(c)}: ${L[v]} (engine SAT${fmtChecked(out.checked)})`); toast(solved ? doneMsg() : `Đúng rồi, ${nm(c)} là ${L[v].toLowerCase()}`, "ok");
  } catch (e) { toast(e.message, "bad"); } finally { submittingVerdict = false; $("#call").querySelectorAll("button").forEach(b => b.disabled = false); }
};
$("#bHint").onclick = async () => { if (busy || paused || solved) return; try { const h = await api("/api/hint", { id: P.id, session: gameSession }); if (h.status !== "HINT") return toast(h.message, "warn"); hintCell = h.cell; assisted = true; makeHintColorGroups(h.clues || []); hl = (h.clues || []).flatMap(c => P.clues[c] ? clueCells(P.clues[c]) : []); draw(); showHintSummary(h); } catch (e) { toast(e.message, "bad"); } };
async function stepOnce() { try { const r = await api("/api/step", { id: P.id, session: gameSession }); if (r.status !== "ACCEPTED") { toast(r.status === "STUCK" ? r.message : r.status, "warn"); return false; } const p = await api(`/api/state?id=${encodeURIComponent(P.id)}&session=${encodeURIComponent(gameSession)}`); acceptEngineState(p, r.cell); log(`${r.cell} ${nm(r.cell)}: ${L[r.verdict]} (agent SAT${fmtChecked(r.checked)})`); return !solved; } catch (e) { toast(e.message, "bad"); return false; } }
$("#bStep").onclick = () => { if (!busy && !paused && !solved) { assisted = true; stepOnce(); } };
$("#bAuto").onclick = async () => { if (busy) { busy = false; return; } if (solved || paused) return; assisted = true; lock(true); while (busy && await stepOnce()) await sleep(1400 / +$("#speed").value); lock(false); };
$("#bRestart").onclick = async () => { if (busy) return; try { const p = await api("/api/reset", { id: P.id, session: gameSession }); elapsed = 0; last = performance.now(); renderClock(); notes = {}; persistNotes(); acceptEngineState(p); } catch (e) { toast(e.message, "bad"); } };
// ---- Kích hoạt nút Load: hỗ trợ cả Upload file JSON từ máy & chọn nhanh từ danh sách puzzles/ ----
const fileInput = $("#file");
const loadBtn = $("#bLoad");

if (fileInput) {
  fileInput.disabled = false;
  fileInput.accept = ".json,application/json";
  fileInput.onchange = async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    try {
      const text = await f.text();
      const puzzleObj = JSON.parse(text);
      const p = await api("/api/upload", { puzzle: puzzleObj });
      acceptEngineState(p);
      $("#dayinfo").textContent = `${p.id} · ${p.size}×${p.size} (${puzzleObj.difficulty || "custom"})`;
      toast(`Đã tải thành công: ${f.name}`, "ok");
    } catch (err) {
      toast("Không thể tải file puzzle: " + err.message, "bad");
    } finally {
      fileInput.value = ""; // Reset để có thể chọn lại cùng 1 file nếu muốn
    }
  };
}

if (loadBtn) {
  loadBtn.disabled = false;
  loadBtn.onclick = () => {
    // Mở hộp thoại chọn file JSON từ máy tính
    if (fileInput) fileInput.click();
  };
}

// Tạo thêm dropdown chọn nhanh các màn chơi mẫu có sẵn trong thư mục puzzles/ (3x3, 4x4, 5x5)
function renderPresetSelector(items) {
  if (!items || !items.length || document.getElementById("presetWrap")) return;
  const presets = items.filter(item => !/^daily_/i.test(item.id) && !/daily/i.test(item.file || ""));
  const list = presets.length ? presets : items;

  const wrap = document.createElement("div");
  wrap.id = "presetWrap";
  wrap.style.cssText = "position:relative;display:inline-block;";

  const trigger = document.createElement("button");
  trigger.type = "button";
  trigger.className = "btn";
  trigger.textContent = "📂 Chọn màn mẫu ▾";
  trigger.title = "Chọn nhanh puzzle mẫu từ thư mục puzzles/";

  const menu = document.createElement("div");
  menu.style.cssText = `
    display:none;position:absolute;top:calc(100% + 6px);left:0;z-index:999;
    min-width:100%;max-height:280px;overflow-y:auto;
    background:var(--cream,#fff);color:var(--ink,#222);
    border:3px solid var(--ink,#222);border-radius:14px;
    box-shadow:0 6px 0 var(--ink,#222);padding:4px;
  `;

  list.forEach(item => {
    const row = document.createElement("div");
    row.textContent = `${item.id} (${item.size}×${item.size} - ${item.difficulty || "?"})`;
    row.style.cssText = "padding:6px 12px;border-radius:9px;cursor:pointer;white-space:nowrap;font-size:14px;";
    row.onmouseenter = () => { row.style.background = "rgba(0,0,0,0.08)"; };
    row.onmouseleave = () => { row.style.background = "transparent"; };
    row.onclick = async () => {
      menu.style.display = "none";
      if (busy) return;
      trigger.textContent = `📂 ${item.id} ▾`;
      try {
        const p = await api("/api/start", { id: item.id });
        acceptEngineState(p);
        $("#dayinfo").textContent = `${p.id} · ${p.size}×${p.size}`;
        toast(`Đã nạp màn: ${p.id}`, "ok");
      } catch (err) {
        toast(err.message, "bad");
      }
    };
    menu.append(row);
  });

  trigger.onclick = (e) => {
    e.stopPropagation();
    menu.style.display = menu.style.display === "none" ? "block" : "none";
  };
  document.addEventListener("click", () => { menu.style.display = "none"; });

  wrap.append(trigger, menu);
  if (loadBtn && loadBtn.parentElement) {
    loadBtn.parentElement.insertBefore(wrap, loadBtn);
  }
}

api("/api/puzzles").then(async items => {
  enginePuzzleIds = items;
  renderPresetSelector(items);
  try { dailyInfo = await api("/api/daily"); } catch (_) { dailyInfo = null; }
  return selectDate(today());
}).catch(e => toast(e.message, "bad"));