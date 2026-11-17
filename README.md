# Griductive Solver

Hệ thống giải trò chơi suy luận lưới (Grid-deduction game **Griductive**) sử dụng Logic Mệnh đề, mã hóa CNF và thuật toán tìm kiếm DPLL SAT Solver. Đồ án môn **CSC14003 - Nhập môn Trí tuệ Nhân tạo**, Khoa Công nghệ Thông tin, Trường Đại học Khoa học Tự nhiên, ĐHQG-HCM.

---

## 👥 Phân công nhiệm vụ nhóm

| Thành viên | Nhiệm vụ chính | Chi tiết & Module |
|---|---|---|
| **A: Logic core** | Mô hình clue, resolver vùng, evaluator ngữ nghĩa, CNF encoder, extensions | Mục 4.2 (`src/logic/`) |
| **B: SAT + Agent** | Thuật toán DPLL, kiểm tra entailment, uniqueness check, vòng lặp agent, trace | Mục 4.3 + 4.4 (`src/sat/`, `src/agent/`) |
| **C: Engine + GUI** | Game engine, puzzle loader, giao diện đồ họa GUI, highlight clue, Hint/Auto Solve/Load/Restart | Mục 4.1 (`src/engine/`, `src/gui/`) |
| **D: Puzzle + Thực nghiệm** | Thiết kế bộ puzzle mẫu, benchmark generator, thực nghiệm & thống kê số liệu, tổng hợp báo cáo | Mục 4.5 (`src/puzzles/`, `benchmarks/`) |

---

## 📁 Cấu trúc Thư mục Dự án

```text
Griductive-Solver/
├── README.md                           # Hướng dẫn chạy & thông tin dự án
├── requirements.txt                    # Danh sách thư viện phụ thuộc
├── docs/
│   └── part_a_report.md                # Báo cáo kỹ thuật chi tiết Phần A (Logic Core)
├── src/
│   ├── __init__.py
│   ├── logic/                          # === PHẦN A: LOGIC CORE ===
│   │   ├── __init__.py
│   │   ├── types.py                    # Enum trạng thái (CRIMINAL/INNOCENT), ClueType, RegionType, Verdict
│   │   ├── model.py                    # Tọa độ CellCoord, Character, Clue, RegionSpec
│   │   ├── regions.py                  # RegionResolver (Row, Col, Neighbors, Corners, Boundary, Between, v.v.)
│   │   ├── evaluator.py                # SemanticEvaluator (đánh giá ngữ nghĩa trực tiếp không qua CNF)
│   │   ├── encoder.py                  # VarManager, CNFFormula, CNFEncoder, KnowledgeBase (KB_t)
│   │   └── extensions.py               # Mở rộng: PARITY, COUNT_COMPARE, ALL_SAME, vùng nâng cao
│   ├── sat/                            # === PHẦN B: DPLL SAT SOLVER ===
│   ├── agent/                          # === PHẦN B: DEDUCTIVE LOGIC AGENT ===
│   ├── engine/                         # === PHẦN C: GAME ENGINE ===
│   ├── gui/                            # === PHẦN C: GRAPHICAL USER INTERFACE ===
│   └── puzzles/                        # === PHẦN D: BỘ PUZZLE MẪU ===
│       ├── __init__.py
│       ├── sample_puzzles.py           # Loader & định nghĩa puzzle mẫu 3x3
│       └── data/
│           ├── sample_3x3_01.json      # Puzzle 3x3 mẫu số 1 (nghiệm duy nhất)
│           ├── sample_3x3_02.json      # Puzzle 3x3 mẫu số 2 (nghiệm duy nhất)
│           └── sample_3x3_03.json      # Puzzle 3x3 mẫu số 3 (nghiệm duy nhất, có extension)
└── tests/
    ├── __init__.py
    ├── run_tests.py                    # Runner chạy tất cả các test suites
    ├── test_logic_core.py              # Test unit các chức năng của Logic Core
    └── test_cross_check.py             # Test chéo brute-force giữa CNF Encoder và Semantic Evaluator
```

---

## 🚀 Hướng dẫn Cài đặt & Chạy Test

### 1. Cài đặt môi trường
Dự án sử dụng **Python 3.10+**. Phần logic core thuần túy sử dụng thư viện chuẩn của Python (`dataclasses`, `enum`, `itertools`, `unittest`).

```bash
# Cài đặt thư viện phụ trợ (nếu cần)
pip install -r requirements.txt
```

### 2. Chạy bộ kiểm thử tự động (Unit Test & Cross Check)
Để chạy toàn bộ các bài kiểm thử của Phần A:

```bash
# Chạy qua test runner tích hợp sẵn
python tests/run_tests.py

# Hoặc chạy thông qua module unittest của Python
python -m unittest discover -s tests -p "test_*.py"

# Hoặc chạy thông qua pytest (nếu đã cài pytest)
pytest tests/
```

---

## 🧩 Chi tiết Phần A: Logic Core & CNF Encoding (Mục 4.2)

### 1. Biến mệnh đề sơ cấp (Propositional Variables)
- Với mỗi nhân vật $i$, định nghĩa biến $C_i$:
  - $C_i = \text{True} \iff$ nhân vật $i$ là **Criminal**.
  - $C_i = \text{False} \iff$ nhân vật $i$ là **Innocent**.
- Lớp `VarManager`:
  - Sắp xếp xác định (deterministic) danh sách nhân vật theo thứ tự bảng chữ cái tên hiển thị (display name), sử dụng tọa độ ô cờ làm tie-breaker.
  - Đánh số các biến sơ cấp từ $1$ đến $N^2$.
  - Biến phụ trợ (Auxiliary Variables) được quản lý riêng biệt, đánh số từ $N^2 + 1, \dots$ và không bao giờ trùng lặp với biến sơ cấp.

### 2. Ngôn ngữ Clue cốt lõi & Mã hóa CNF
- **`FACT(person, status)`**: Sinh unit clause $(C_i)$ hoặc $(\neg C_i)$.
- **`SAME(p1, p2)`**: $C_1 \leftrightarrow C_2 \equiv (\neg C_1 \vee C_2) \wedge (C_1 \vee \neg C_2)$.
- **`DIFFERENT(p1, p2)`**: $C_1 \oplus C_2 \equiv (C_1 \vee C_2) \wedge (\neg C_1 \vee \neg C_2)$.
- **`EXACTLY(k, region)`**: $\sum_{i \in R} C_i = k$. Mã hóa tổ hợp nhị thức kết hợp $\text{AT\_LEAST}(k) \wedge \text{AT\_MOST}(k)$.
- **`AT_LEAST(k, region)`**: Mỗi tập con kích thước $n - k + 1$ phải chứa ít nhất 1 biến True.
- **`AT_MOST(k, region)`**: Mỗi tập con kích thước $k + 1$ không được toàn bộ là True (mỗi tập con chứa ít nhất 1 biến False).

### 3. Các Phần Mở rộng (Extensions)
- **`PARITY`**: Ràng buộc số Criminal trong một vùng là Chẵn (EVEN) hoặc Lẻ (ODD). Mã hóa xâu chuỗi XOR tuyến tính với biến phụ trợ ($O(n)$ mệnh đề).
- **`COUNT_COMPARE`**: So sánh tương đối số lượng tội phạm giữa 2 vùng ($R_1 > R_2$, $R_1 == R_2$, v.v.).
- **`ALL_SAME`**: Ràng buộc tất cả các nhân vật trong một vùng có cùng trạng thái.
- **`Advanced Regions`**: Hỗ trợ các vùng `CORNERS`, `BOUNDARY`, `INTERIOR`, `COMMON_NEIGHBORS(c1, c2)`, `BETWEEN(c1, c2)`, `INTERSECTION`, `UNION`, `DIFFERENCE`.

### 4. Đánh giá Ngữ nghĩa Trực tiếp (Semantic Evaluator)
Lớp `SemanticEvaluator` kiểm tra tính đúng đắn của bất kỳ clue nào dưới một phép gán hoàn chỉnh mà **hoàn toàn không gọi đến bộ mã hóa CNF**.

### 5. Kiểm tra Chéo bằng Vét cạn (Brute-Force Cross-Check)
Module `tests/test_cross_check.py` duyệt qua tất cả $2^{|V|}$ trường hợp phép gán khả dĩ đối với từng template clue, đảm bảo tính tương đương logic tuyệt đối:
$$\text{Evaluator}(CL, \alpha) == \text{CNF\_is\_satisfied}(CNF(CL), \alpha)$$

### 6. Mô hình Cơ sở Tri thức ($KB_t$)
Lớp `KnowledgeBase` mô hình hóa tri thức tại bước $t$:
$$KB_t = CNF(\text{revealed clues}) \wedge \text{unit clauses for proved verdicts}$$
- **Bảo mật tuyệt đối:** Hoàn toàn độc lập với phần "hidden" của Engine, không truy xuất nhãn bí mật hay các clue chưa lật.
- Hỗ trợ xuất ra định dạng chuẩn quốc tế DIMACS CNF (`kb.to_dimacs()`).
- Báo cáo chi tiết số lượng biến sơ cấp, biến phụ trợ và số lượng mệnh đề CNF (`kb.report_stats()`).

---

## 🔗 Giao tiếp với các thành viên khác

- **Với Thành viên B (SAT + Agent):**
  - Nhận $KB_t$ hoặc tập mệnh đề CNF từ `kb.get_clauses()` (danh sách `List[List[int]]` chuẩn DIMACS).
  - Sử dụng `VarManager` để tra cứu giữa tên nhân vật/ô cờ và biến số nguyên.
- **Với Thành viên C (Engine + GUI):**
  - Sử dụng `RegionResolver.get_referenced_cells(clue)` để lấy danh sách các ô cần highlight trên giao diện khi người dùng click vào một clue.
  - Sử dụng `Character`, `Clue`, `Status` để hiển thị và cập nhật trạng thái thẻ bài.
- **Với Thành viên D (Puzzle + Thực nghiệm):**
  - Đã có sẵn 3 puzzle mẫu chuẩn schema trong `src/puzzles/data/` (đều có nghiệm duy nhất đã được kiểm chứng tự động).
  - Có thể sử dụng `SemanticEvaluator` và `VarManager` để viết bộ sinh puzzle (generator) và benchmark.
