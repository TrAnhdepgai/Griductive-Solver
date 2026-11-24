# Griductive Solver

Hệ thống giải trò chơi suy luận lưới (grid-deduction game **Griductive**) bằng Logic Mệnh đề, mã hóa CNF và thuật toán **DPLL SAT Solver**. Agent chỉ đưa ra những verdict **được suy ra logic chắc chắn** (no-guess), phát hiện trạng thái mơ hồ hoặc mâu thuẫn, và đi kèm một GUI trên trình duyệt để chơi tay hoặc xem agent tự giải.

Đồ án **Project 2** môn **CSC14003 - Nhập môn Trí tuệ Nhân tạo**, Khoa Công nghệ Thông tin, Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM.

---

## 👥 Phân công nhiệm vụ nhóm

| Thành viên | Nhiệm vụ chính | Module |
|---|---|---|
| **A: Logic core** | Mô hình clue, resolver vùng, evaluator ngữ nghĩa, CNF encoder, extensions (mục 4.2) | `src/logic/` |
| **B: SAT + Agent** | DPLL, kiểm tra entailment, uniqueness check, vòng lặp agent, trace (mục 4.3 + 4.4) | `src/sat/`, `src/agent/` |
| **C: Engine + GUI** | Game engine, kết nối GUI với logic, highlight clue, Hint / Auto Solve / Load / Restart (mục 4.1) | `src/engine/`, `gui/` |
| **D: Puzzle + Thực nghiệm** | Bộ puzzle, generator, verify, benchmark, tổng hợp số liệu báo cáo (mục 4.5) | `puzzles/`, `tools/`, `experiments/` |

---

## 🧱 Kiến trúc tổng quan

Đề yêu cầu tách hai vai trò. Hệ thống tuân theo:

```text
 Trình duyệt (gui/)  ──HTTP/JSON──▶  src/engine/gui_server.py
                                          │
                                          ▼
              ┌─────────── Game Engine (LocalGameEngine) ───────────┐
              │ giữ lời giải ẩn + clue chưa lật; chỉ phát ra        │
              │ PublicState (clue đã lật + verdict đã chứng minh)   │
              └───────────────────────┬─────────────────────────────┘
                                      │ chỉ PublicState
                                      ▼
   Logic Agent (src/agent) ─▶ KB_t (CNF, src/logic) ─▶ DPLL (src/sat)
```

- **Game Engine** sở hữu toàn bộ puzzle, lời giải ẩn và clue chưa lật.
- **Logic Agent** chỉ nhận trạng thái công khai, **không** đọc được lời giải ẩn hay clue chưa lật.
- Mọi verdict (người chơi gọi, Hint, Auto Solve) đều được kiểm bằng entailment:
  `KB_t ⊨ C_i ⇔ KB_t ∧ ¬C_i UNSAT`. Kết quả: `ACCEPTED`, `NOT_PROVABLE` (chưa đủ căn cứ) hoặc `CONTRADICTED` (suy ra điều ngược lại).
- Trình duyệt **không** nhận được trạng thái ẩn hay clue chưa lật.

---

## 📁 Cấu trúc thư mục

```text
Griductive-Solver/
├── README.md
├── requirements.txt
├── docs/
│   ├── part_a_report.md            # Báo cáo kỹ thuật Phần A (Logic core)
│   └── part_b_sat_agent.md         # Báo cáo kỹ thuật Phần B (DPLL + Agent)
├── gui/                            # === PHẦN C: giao diện web ===
│   ├── index.html
│   ├── README.md
│   └── static/                     # avatar.js, engine-bridge.js (gọi API), fonts/, icons/
├── puzzles/                        # 31 puzzle: 24 bộ chuẩn + 7 puzzle "daily"
│   ├── {3x3,4x4,5x5}_{easy,medium,hard}_NN.json
│   └── 00_daily_*.json             # 7 puzzle theo thứ trong tuần, độ khó tăng dần T2 → CN
├── experiments/results/            # Kết quả benchmark (benchmark_team.{csv,json,md,tex})
├── tools/                          # === PHẦN D ===
│   ├── README_D.md                 # Schema JSON + quy ước chung (đọc file này trước)
│   ├── adapter.py                  # Cầu nối tới code của nhóm (run_team, team_evaluate, team_encode)
│   ├── generate_puzzles.py         # Sinh bộ puzzle chuẩn (seed cố định)
│   ├── generate_weekly.py          # Sinh 7 puzzle daily
│   ├── verify_puzzles.py           # Kiểm tra hợp lệ + nghiệm duy nhất (brute-force)
│   ├── cross_check.py              # Kiểm tra chéo CNF encoder vs evaluator vs brute-force
│   ├── benchmark.py                # Đo thực nghiệm (timeout, repeats, xuất csv/md/tex)
│   ├── reference.py, clues_ref.py, schema.py   # Bản tham chiếu độc lập và schema
├── src/
│   ├── logic/                      # === PHẦN A ===
│   │   ├── types.py                # Status, ClueType, RegionType, CompareOp
│   │   ├── model.py                # CellCoord, Character, Clue, RegionSpec, Puzzle
│   │   ├── regions.py              # RegionResolver (row, col, neighbors, corners, boundary, between...)
│   │   ├── evaluator.py            # Evaluator ngữ nghĩa trực tiếp, không qua CNF
│   │   ├── encoder.py              # VarManager, CNFEncoder, KnowledgeBase (KB_t)
│   │   └── extensions.py           # PARITY, COMPARE, ALL_SAME, vùng nâng cao
│   ├── sat/                        # === PHẦN B ===
│   │   ├── dpll.py                 # DPLL: unit propagation, conflict, branching, backtrack, thống kê
│   │   └── entailment.py           # EntailmentChecker: CRIMINAL/INNOCENT/UNKNOWN/INCONSISTENT
│   ├── agent/                      # === PHẦN B ===
│   │   ├── interface.py            # PublicState, SubmitResult, GameEngineProtocol
│   │   ├── knowledge.py            # build_kb(state) -> KB_t
│   │   ├── agent.py                # LogicAgent (run/step/hint), judge_verdict, explain, trace
│   │   ├── uniqueness.py           # Kiểm tra nghiệm duy nhất của toàn bộ clue set
│   │   ├── local_engine.py         # LocalGameEngine
│   │   └── __main__.py             # CLI: python -m src.agent ...
│   ├── engine/                     # === PHẦN C ===
│   │   └── gui_server.py           # Server HTTP: phục vụ gui/ và API nối với engine + agent
│   └── puzzles/sample_puzzles.py   # Puzzle 3x3 mẫu cho dev/test
└── tests/                          # 40 unit tests
    ├── run_tests.py
    ├── test_logic_core.py
    ├── test_cross_check.py
    └── test_sat_agent.py
```

---

## 🚀 Cài đặt & chạy

Yêu cầu **Python 3.9+**. Chạy mọi lệnh từ **thư mục gốc của repo**.

```bash
pip install -r requirements.txt
```

> Lõi logic, DPLL, agent và GUI chỉ dùng thư viện chuẩn của Python. `numpy` chỉ cần cho các công cụ của D (`tools/`).

### 1. Chạy GUI (chơi và demo)

```bash
python -m src.engine.gui_server            # mặc định cổng 8001
python -m src.engine.gui_server --port 9000

# hoặc cách sau
python main.py        # chạy server và tự mở trình duyệt
```

Mở <http://127.0.0.1:8001> trong trình duyệt. Cần mở GUI **qua đúng địa chỉ này** (đừng mở thẳng file `index.html`), vì giao diện gọi API của server.

Chức năng chính:
- **Chơi tay:** chọn ô, gọi *Tội phạm / Vô tội*. Verdict đúng thì lật thẻ và lộ clue; sai thì báo `NOT_PROVABLE` hoặc `CONTRADICTED`, không lộ clue.
- **Chọn một clue đã lật** để highlight các ô mà clue nhắc tới.
- **Hint** (chỉ ra một ô ép được và clue liên quan), **Từng bước**, **Tự giải** (agent chạy từng bước), **Chơi lại**, **Tải puzzle**.
- **Lịch theo ngày:** mỗi thứ trong tuần là một puzzle (7 file `00_daily_*`), độ khó tăng từ Thứ Hai đến Chủ Nhật. Có đồng hồ, cài đặt và thông báo tạm dừng khi chuyển tab.

API của server (chi tiết trong `src/engine/gui_server.py`): `GET /api/puzzles`, `GET /api/state`, `POST /api/start`, `/api/call`, `/api/hint`, `/api/step`, `/api/reset`.

### 2. Chạy agent trên dòng lệnh (xem trace suy diễn)

```bash
python -m src.agent puzzles/3x3_easy_01.json --queries     # trace chi tiết + từng SAT query
python -m src.agent "puzzles/*.json" --summary             # bảng tóm tắt mọi puzzle
python -m src.agent puzzles/4x4_hard_01.json --strategy naive --heuristic jw --json out.json
```

Tùy chọn: `--heuristic {first,jw}`, `--strategy {pruned,naive}`, `--queries`, `--summary`, `--json FILE`.

### 3. Chạy kiểm thử

```bash
python tests/run_tests.py                                   # 40 tests
python -m unittest discover -s tests -p "test_*.py"         # hoặc dùng unittest
```

### 4. Kiểm tra puzzle và kiểm tra chéo (Thành viên D)

```bash
python tools/verify_puzzles.py     # kiểm tra mọi puzzle hợp lệ + đúng 1 nghiệm (kết quả: 31/31 valid)
python tools/cross_check.py        # CNF encoder và evaluator của A so với brute-force độc lập
```

Kết quả `cross_check.py` gần nhất:

```text
N=3: 159 clues x 512 assignments checked
N=4: 268 clues x 400 assignments checked
N=5: 235 clues x 400 assignments checked

282608 checks, 0 failures
```

### 5. Chạy thực nghiệm (benchmark)

```bash
python tools/benchmark.py --backend team --timeout 60 --repeats 3
```

Mỗi puzzle chạy trong một tiến trình riêng có timeout, **fail hoặc timeout được ghi lại chứ không bị bỏ**. Kết quả nằm trong `experiments/results/benchmark_team.{csv,json,md,tex}` với các chỉ số: biến chính/phụ, số clause, số SAT call, decisions/propagations/backtracks, số bước, số wave, thời gian.

Sinh lại puzzle (seed cố định, cho kết quả lặp lại được):

```bash
python tools/generate_puzzles.py --preset      # bộ puzzle chuẩn
python tools/generate_weekly.py                # 7 puzzle daily (thêm --check để chỉ kiểm tra)
```

---

## 🧩 Định dạng puzzle

Mỗi file trong `puzzles/` có dạng (mô tả đầy đủ ở `tools/README_D.md`):

```json
{
  "id": "3x3_easy_01", "size": 3, "difficulty": "easy",
  "cells": [{"id": "A1", "row": 1, "col": "A", "name": "Abel", "profession": "Clerk"}],
  "solution": {"A1": "CRIMINAL"},
  "initial_revealed": ["B2"],
  "clues": {"A1": {"type": "EXACTLY", "region": {"kind": "row", "row": 1}, "k": 2}}
}
```

- Ô gọi theo **cột chữ + hàng số** (`C2` = cột C, hàng 2). Biến SAT của ô thứ `i` (row-major, từ 0) là `i + 1`; biến phụ đánh số lớn hơn `N*N`.
- 6 clue lõi: `FACT`, `SAME`, `DIFFERENT`, `EXACTLY`, `AT_LEAST`, `AT_MOST`. Extension: `PARITY`, `COMPARE` (và vùng nâng cao trong `src/logic/extensions.py`).
- Vùng: `row`, `column`, `neighbors`, `cells`.
- `solution` chỉ dành cho Game Engine; Logic Agent không bao giờ nhìn thấy.

---

## 💡 Hướng dẫn dùng các module trong code

### Nạp puzzle và dựng Knowledge Base

```python
from src.logic.model import Puzzle
from src.agent.local_engine import LocalGameEngine
from src.agent.knowledge import build_kb

puzzle = Puzzle.load("puzzles/3x3_easy_01.json")
engine = LocalGameEngine.load("puzzles/3x3_easy_01.json")
kb = build_kb(engine.public_state())      # KB_t = CNF(clue đã lộ) ∧ unit clause verdict đã chứng minh
clauses = kb.get_clauses()                # danh sách mệnh đề DIMACS
```

### Dùng agent

```python
from src.agent import LogicAgent, judge_verdict

judge_verdict(engine.public_state(), "B2", "CRIMINAL")   # ACCEPTED / NOT_PROVABLE / CONTRADICTED
hint = LogicAgent(engine).hint()                         # hint.cell, hint.verdict, hint.supporting_clues
result = LogicAgent(engine).run()                        # Auto Solve; result.trace là deduction trace
```

### Đánh giá ngữ nghĩa trực tiếp (không qua CNF)

```python
from src.logic.evaluator import evaluate_clue

assignment = {"A1": False, "B1": True, "C1": True, "A2": True, ...}
evaluate_clue(puzzle.clues["B1"], assignment, n=3)
```

Chi tiết kỹ thuật: [`docs/part_a_report.md`](docs/part_a_report.md) (Logic core) và [`docs/part_b_sat_agent.md`](docs/part_b_sat_agent.md) (DPLL, entailment, uniqueness, vòng lặp agent).

---

## 🎯 Bộ 6 test case chính thức (Official Benchmark Set)

Theo giải đáp của giảng viên (tối thiểu 6 test case, mỗi kích thước 2 test case có **nghiệm duy nhất**, dùng cho Load, Demo Agent và báo cáo):

| Kích thước | Test case 1 | Test case 2 |
| :---: | :--- | :--- |
| **3×3** | `puzzles/3x3_easy_01.json` | `puzzles/3x3_medium_01.json` |
| **4×4** | `puzzles/4x4_easy_01.json` | `puzzles/4x4_medium_01.json` |
| **5×5** | `puzzles/5x5_medium_01.json` | `puzzles/5x5_hard_01.json` |

Ngoài 6 test case trên, thư mục `puzzles/` còn các puzzle mở rộng (đủ độ khó Easy đến Hard) và 7 puzzle daily. Cả 31 puzzle đều đã được kiểm chứng có đúng một nghiệm và agent giải được toàn bộ.

---

## 📚 Tài liệu tham khảo

1. **Trò chơi gốc:** Griductive trên Knotwise (<https://knotwise.games/games/griductive>) và tựa game suy luận **Clues By Sam** (<https://cluesbysam.com/>), nguồn tham khảo luật chơi, ý tưởng thẻ nhân vật và clue.
2. **Tài liệu môn học:** Đề và hướng dẫn đồ án *CSC14003 - Nhập môn Trí tuệ Nhân tạo*, Khoa Công nghệ Thông tin, ĐH Khoa học Tự nhiên, ĐHQG-HCM.
3. **Mã hóa cardinality constraints:** Sinz, C. (2005). *Towards an Optimal CNF Encoding of Boolean Cardinality Constraints*. CP 2005.
4. **Giao diện:** font (Kermel, Nokio, iCielBC Old Style) và bộ icon Streamline Stickies do thành viên C sử dụng, ghi rõ nguồn và giấy phép trong báo cáo.