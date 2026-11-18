# Phần B — DPLL SAT Solver + Deductive Logic Agent (mục 4.3 + 4.4)

## Module

| File | Nội dung |
|---|---|
| `src/sat/dpll.py` | `DPLLSolver`: unit propagation (two-watched-literals), phát hiện conflict, chọn biến tất định (`first` / `jw`), rẽ nhánh đệ quy + backtrack, trả về SAT + model đầy đủ hoặc UNSAT, thống kê decisions / propagations / backtracks / conflicts / runtime. Hỗ trợ *assumptions* nên 1 instance trả lời được nhiều truy vấn. |
| `src/sat/entailment.py` | `EntailmentChecker`: `classify(v)` đúng theo mục 3.4 (KB∧¬C UNSAT → CRIMINAL, KB∧C UNSAT → INNOCENT, cả hai SAT → UNKNOWN, KB UNSAT → INCONSISTENT); `classify_many(..., strategy="naive" \| "pruned")`; `count_models` (blocking clause trên biến primary). Mọi lời gọi SAT được log thành `SATQuery`. |
| `src/agent/interface.py` | Hợp đồng Engine ↔ Agent: `PublicState` (chỉ dữ liệu công khai), `SubmitResult`, `GameEngineProtocol` (`public_state()`, `submit_verdict()`). |
| `src/agent/knowledge.py` | `build_kb(state)`: KB_t = CNF(clue đã lộ) ∧ unit clause của verdict đã chứng minh, dùng encoder của phần A, biến row-major (A1=1, B1=2, ...). |
| `src/agent/agent.py` | `LogicAgent.run()/step()/hint()`, `classify_state`, `judge_verdict` (ACCEPTED / NOT_PROVABLE / CONTRADICTED cho GUI), `explain` (tập clue tối thiểu chứng minh 1 verdict, dùng cho Hint), `format_trace`. |
| `src/agent/uniqueness.py` | `check_uniqueness` / `check_puzzle_uniqueness`: kiểm tra nghiệm duy nhất của **toàn bộ** clue set, tách biệt với vòng lặp chơi. |
| `src/agent/local_engine.py` | Engine headless tối thiểu (cho test/benchmark). Engine GUI của phần C chỉ cần cài đặt cùng 2 phương thức. |

## Hai chiến lược phân loại

* `naive`: 2 lời gọi SAT / nhân vật, đúng nguyên văn mục 3.4.
* `pruned` (mặc định): mỗi model tìm được là một *witness*. Nếu các witness đã cho thấy C_i nhận cả True lẫn False → UNKNOWN, không cần gọi SAT; nếu chỉ thấy giá trị b → 1 lời gọi KB ∧ (C_i ≠ b) là đủ. Kết quả giống hệt `naive` (có test kiểm chứng) nhưng ít lời gọi hơn — có thể dùng làm so sánh trong phần thực nghiệm.

## Vòng lặp agent

1. Lấy `PublicState` → dựng KB_t.
2. Phân loại mọi nhân vật chưa giải.
3. KB_t UNSAT → `INCONSISTENT`; không ai bị ép → `STUCK` (không đoán, không submit).
4. Chọn nhân vật bị ép đầu tiên theo row-major, submit; engine lật thẻ và trả về clue mới.
5. Lặp tới khi `SOLVED`.

Mỗi bước ghi `TraceStep`: số bước, wave, clue đang active, kích thước KB_t, danh sách SAT query (công thức + kết quả + thống kê), phân loại, verdict, phản hồi của engine, clue vừa lộ. Định nghĩa *wave* giống `tools/reference.py`.

## Chạy

```bash
python -m src.agent puzzles/3x3_easy_01.json --queries     # trace chi tiết
python -m src.agent "puzzles/*.json" --summary             # bảng tóm tắt
python -m src.agent puzzles/4x4_hard_01.json --strategy naive --heuristic jw --json out.json
python -m unittest tests.test_sat_agent -v
python tools/benchmark.py --backend team --timeout 60
```

## Dùng từ GUI (phần C)

```python
from src.agent import LogicAgent, judge_verdict
status = judge_verdict(engine.public_state(), "B2", "CRIMINAL")   # ACCEPTED / NOT_PROVABLE / CONTRADICTED
hint = LogicAgent(engine).hint()        # hint.cell, hint.verdict, hint.supporting_clues (để highlight), hint.message
result = LogicAgent(engine).run()       # Auto Solve; result.trace để hiển thị
```

## Kết quả kiểm chứng

* DPLL khớp brute-force trên 1500 CNF ngẫu nhiên (cả 2 heuristic), model trả về luôn thỏa công thức.
* `classify_state` khớp brute-force (tools/reference.py) trên trạng thái ngẫu nhiên của mọi puzzle 3x3/4x4, cả `naive` và `pruned`.
* Agent giải đủ 24/24 puzzle, thứ tự lật thẻ trùng `meta.reveal_order`, số wave trùng reference; uniqueness check xác nhận cả 24 puzzle có đúng 1 nghiệm và bằng `solution`.
