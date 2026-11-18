# Griductive Solver

Hệ thống giải trò chơi suy luận lưới (Grid-deduction game **Griductive**) sử dụng Logic Mệnh đề, mã hóa CNF và thuật toán tìm kiếm DPLL SAT Solver. Đồ án môn **CSC14003 - Nhập môn Trí tuệ Nhân tạo**, Khoa Công nghệ Thông tin, Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM.

---

## 👥 Phân công nhiệm vụ nhóm

| Thành viên | Nhiệm vụ chính | Chi tiết & Module |
|---|---|---|
| **A: Logic core** | Mô hình clue, resolver vùng, evaluator ngữ nghĩa, CNF encoder, extensions | Mục 4.2 (`src/logic/`) |
| **B: SAT + Agent** | Thuật toán DPLL, kiểm tra entailment, uniqueness check, vòng lặp agent, trace | Mục 4.3 + 4.4 (`src/sat/`, `src/agent/`) |
| **C: Engine + GUI** | Game engine, puzzle loader, giao diện đồ họa GUI, highlight clue, Hint/Auto Solve/Load/Restart | Mục 4.1 (`src/engine/`, `src/gui/`) |
| **D: Puzzle + Thực nghiệm** | Thiết kế bộ puzzle mẫu, benchmark generator, thực nghiệm & thống kê số liệu, tổng hợp báo cáo | Mục 4.5 (`puzzles/`, `tools/`) |

---

## 📁 Cấu trúc Thư mục Dự án

```text
Griductive-Solver/
├── README.md                           # Hướng dẫn chạy & thông tin dự án
├── requirements.txt                    # Danh sách thư viện phụ thuộc
├── docs/
│   └── part_a_report.md                # Báo cáo kỹ thuật chi tiết Phần A (Logic Core)
├── puzzles/                            # 24 file puzzle chuẩn (3x3, 4x4, 5x5: easy, medium, hard)
├── tools/                              # Bộ công cụ thực nghiệm của Thành viên D
│   ├── adapter.py                      # Cầu nối (team_evaluate, team_encode) tới logic core
│   ├── cross_check.py                  # Script kiểm tra chéo brute-force độc lập
│   ├── benchmark.py                    # Benchmark đo đạc thời gian & số bước
│   ├── generate_puzzles.py             # Sinh puzzle tự động
│   └── verify_puzzles.py               # Kiểm tra tính hợp lệ & nghiệm duy nhất của puzzles
├── src/
│   ├── __init__.py
│   ├── logic/                          # === PHẦN A: LOGIC CORE ===
│   │   ├── __init__.py
│   │   ├── types.py                    # Enum trạng thái (CRIMINAL/INNOCENT), ClueType, RegionType, CompareOp
│   │   ├── model.py                    # Tọa độ CellCoord, Character, Clue, RegionSpec, Puzzle (tương thích 2 chiều)
│   │   ├── regions.py                  # RegionResolver (Row, Col, Neighbors, Corners, Boundary, Between, v.v.)
│   │   ├── evaluator.py                # SemanticEvaluator (đánh giá ngữ nghĩa trực tiếp không qua CNF)
│   │   ├── encoder.py                  # VarManager (Row-major & Alpha), CNFFormula, CNFEncoder, KnowledgeBase (KB_t)
│   │   └── extensions.py               # Mở rộng: PARITY, COMPARE, ALL_SAME, vùng nâng cao
│   ├── sat/                            # === PHẦN B: DPLL SAT SOLVER ===
│   ├── agent/                          # === PHẦN B: DEDUCTIVE LOGIC AGENT ===
│   ├── engine/                         # === PHẦN C: GAME ENGINE ===
│   └── gui/                            # === PHẦN C: GRAPHICAL USER INTERFACE ===
└── tests/
    ├── __init__.py
    ├── run_tests.py                    # Runner chạy tất cả các test suites
    ├── test_logic_core.py              # Test unit các chức năng của Logic Core
    └── test_cross_check.py             # Test kiểm tra chéo CNF vs Evaluator với brute-force
```

---

## 🚀 Hướng dẫn Cài đặt & Chạy kiểm thử

### 1. Cài đặt môi trường
Dự án yêu cầu Python 3.9+ trở lên. Cài đặt các gói phụ thuộc (dùng cho công cụ thực nghiệm của nhóm):
```bash
pip install -r requirements.txt
```

### 2. Chạy bài kiểm tra chéo độc lập với Thành viên D (`cross_check.py`)
Script kiểm tra tính tương đương logic giữa bộ giải mã CNF (`team_encode`) và bộ đánh giá ngữ nghĩa (`team_evaluate`) của Phần A so với thuật toán brute-force độc lập trên toàn bộ 24 puzzle và clues ngẫu nhiên:
```bash
python tools/cross_check.py
```
**Kết quả thực tế:**
```text
N=3: 141 clues x 512 assignments checked
N=4: 236 clues x 400 assignments checked
N=5: 160 clues x 400 assignments checked

230592 checks, 0 failures
```

### 3. Chạy toàn bộ Unit Tests của Phần A
```bash
python tests/run_tests.py
```
Hoặc dùng `unittest` / `pytest`:
```bash
python -m unittest discover -s tests -p "test_*.py"
```

### 4. Kiểm tra toàn bộ 24 puzzle hợp lệ
```bash
python tools/verify_puzzles.py
```

---

## 💡 Hướng dẫn tích hợp cho Thành viên B & C

### A. Đọc và nạp Puzzle
Lớp `Puzzle` hỗ trợ đọc trực tiếp mọi file JSON trong thư mục `puzzles/`:
```python
from src.logic.model import Puzzle

puzzle = Puzzle.load("puzzles/3x3_easy_01.json")
print("Grid size:", puzzle.size)
print("Initial revealed cells:", puzzle.initial_revealed)
print("Clues count:", len(puzzle.clues))
```

### B. Sử dụng Knowledge Base ($KB_t$) cho Agent (Phần B)
```python
from src.logic.model import Clue, Status
from src.logic.encoder import VarManager, CNFEncoder, KnowledgeBase

# Khởi tạo bộ quản lý biến theo chuẩn Row-major của nhóm:
var_mgr = VarManager.from_grid_size(puzzle.size)
encoder = CNFEncoder(var_mgr=var_mgr)
kb = KnowledgeBase(encoder=encoder)

# Khi một ô được lật mở và hé lộ clue:
kb.add_clue(puzzle.clues["A1"])

# Khi agent đã suy diễn chắc chắn trạng thái của một ô:
kb.add_proved_status("A3", Status.INNOCENT)

# Lấy danh sách mệnh đề CNF (DIMACS integers) để truyền vào DPLL solver:
clauses = kb.get_clauses()
```

### C. Đánh giá ngữ nghĩa trực tiếp (Semantic Evaluator)
```python
from src.logic.evaluator import evaluate_clue

assignment = {"A1": False, "B1": True, "C1": True, "A2": True, ...}
is_valid = evaluate_clue(puzzle.clues["B1"], assignment, n=3)
```
