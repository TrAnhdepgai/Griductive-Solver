# Báo cáo Phần A: Logic Core & CNF Encoding
**Môn học:** CSC14003 - Nhập môn Trí tuệ Nhân tạo  
**Đồ án:** Griductive Solver  
**Người thực hiện:** Thành viên phụ trách Phần A (Logic Core)

---

## 1. Mô tả bài toán & Biểu diễn Logic Mệnh đề

### 1.1. Biến mệnh đề sơ cấp (Primary Propositional Variables)
Với mỗi ô $(r, c)$ trên lưới $N \times N$, ta định nghĩa một biến mệnh đề sơ cấp:
$$C_i = \begin{cases} \text{True}, & \text{nếu ô } i \text{ là Tội phạm (Criminal)} \\ \text{False}, & \text{nếu ô } i \text{ là Vô tội (Innocent)} \end{cases}$$

**Quy tắc ánh xạ xác định (Deterministic Mapping):**
Module hỗ trợ linh hoạt cả hai quy ước chuẩn của nhóm:
1. **Chuẩn Row-major (quy ước chung nhóm và bài kiểm tra `cross_check.py`):**
   - Tọa độ ô $(r, c)$ với hàng $r \in \{1, \dots, N\}$, cột $c \in \{0, \dots, N-1\}$:
     $$\text{cell\_index} = (r - 1) \times N + c, \quad \text{var} = \text{cell\_index} + 1$$
   - Ví dụ lưới 3×3: $A1=1, B1=2, C1=3, A2=4, B2=5, C2=6, A3=7, B3=8, C3=9$.
2. **Chuẩn Alphabetical tên nhân vật (mục 2.1 đề bài lý thuyết):**
   - Khi bàn chơi có tên hiển thị nhân vật (Display Name), hệ thống tự động ánh xạ hai chiều `name -> var_id` và `cell_id -> var_id`.

### 1.2. Biến phụ trợ (Auxiliary Variables)
Các biến phụ trợ (Auxiliary Variables) được sinh tự động khi mã hóa các ràng buộc nâng cao (chuỗi XOR Parity, so sánh số lượng Compare giữa 2 vùng):
- Tất cả biến phụ trợ được phân tách nghiêm ngặt: luôn có chỉ số lớn hơn số lượng biến sơ cấp ($> N^2$).
- `VarManager` theo dõi, phân bổ độc lập và giải thích ngữ nghĩa của từng biến phụ trợ.

---

## 2. Ngôn ngữ Clue cốt lõi & Dẫn xuất CNF

Mỗi clue có cấu trúc $CL$ được tự động chuyển đổi thành tập các mệnh đề CNF $CNF(CL)$.

### 2.1. Clue Đơn vị (FACT)
- **Ý nghĩa:** Một nhân vật xác định có trạng thái cụ thể.
- **Mệnh đề CNF:**
  - Nếu Criminal: $(C_i)$ [1 mệnh đề unit literal $+v_i$]
  - Nếu Innocent: $(\neg C_i)$ [1 mệnh đề unit literal $-v_i$]

### 2.2. Clue Cùng trạng thái (SAME)
- **Ý nghĩa:** Hai nhân vật $i$ và $j$ có cùng trạng thái ($C_i \leftrightarrow C_j$).
- **Dẫn xuất CNF:**
  $$C_i \leftrightarrow C_j \equiv (\neg C_i \vee C_j) \wedge (C_i \vee \neg C_j)$$
- **Số mệnh đề:** 2 mệnh đề nhị phân: $[-v_i, v_j]$ và $[v_i, -v_j]$.

### 2.3. Clue Khác trạng thái (DIFFERENT)
- **Ý nghĩa:** Hai nhân vật $i$ và $j$ có trạng thái trái ngược nhau (phép XOR $C_i \oplus C_j$).
- **Dẫn xuất CNF:**
  $$C_i \oplus C_j \equiv (C_i \vee C_j) \wedge (\neg C_i \vee \neg C_j)$$
- **Số mệnh đề:** 2 mệnh đề nhị phân: $[v_i, v_j]$ và $[-v_i, -v_j]$.

### 2.4. Clue Đếm số lượng (Cardinality Constraints)
Gọi vùng tham chiếu $R = \{x_1, x_2, \dots, x_n\}$ là tập hợp các literal tương ứng với các ô trong vùng ($n = |R|$). Với Criminal, $x_i = +v_i$; với Innocent, $x_i = -v_i$.

#### A. Ràng buộc Tối thiểu $\text{AT\_LEAST}(k, R)$: $\sum_{i \in R} x_i \ge k$
- **Dẫn xuất Tổ hợp trực tiếp (Binomial Encoding):**
  Để có ít nhất $k$ biến mang giá trị True trong $n$ biến, không thể tồn tại bất kỳ tập con nào gồm $n - k + 1$ biến mà toàn bộ đều nhận giá trị False:
  $$\bigwedge_{S \subseteq R, |S| = n - k + 1} \left( \bigvee_{x \in S} x \right)$$
- **Số mệnh đề sinh ra:** $\binom{n}{n - k + 1} = \binom{n}{k - 1}$.

#### B. Ràng buộc Tối đa $\text{AT\_MOST}(k, R)$: $\sum_{i \in R} x_i \le k$
- **Dẫn xuất Tổ hợp trực tiếp (Binomial Encoding):**
  Để có nhiều nhất $k$ biến nhận giá trị True trong $n$ biến, không thể tồn tại bất kỳ tập con nào gồm $k + 1$ biến mà toàn bộ đều nhận giá trị True:
  $$\bigwedge_{S \subseteq R, |S| = k + 1} \left( \bigvee_{x \in S} \neg x \right)$$
- **Số mệnh đề sinh ra:** $\binom{n}{k + 1}$.

#### C. Ràng buộc Chính xác $\text{EXACTLY}(k, R)$: $\sum_{i \in R} x_i = k$
- **Dẫn xuất:**
  $$\text{EXACTLY}(k, R) \equiv \text{AT\_LEAST}(k, R) \wedge \text{AT\_MOST}(k, R)$$
- **Trường hợp biên đặc biệt:**
  - $k = 0$: Mọi biến trong $R$ phải là False $\implies n$ unit clauses: $\bigwedge_{i \in R} (\neg x_i)$.
  - $k = n$: Mọi biến trong $R$ phải là True $\implies n$ unit clauses: $\bigwedge_{i \in R} (x_i)$.
  - $k < 0$ hoặc $k > n$: Vô nghiệm $\implies$ sinh mệnh đề rỗng `[]` (UNSAT).

---

## 3. Phần mở rộng nâng cao (Extensions)

### 3.1. Tính chẵn/lẻ số lượng tội phạm (PARITY)
- **Ý nghĩa:** $\left(\sum_{i \in R} x_i\right) \bmod 2 = \text{parity}$ ($0$: EVEN, $1$: ODD).
- **Mã hóa chuỗi biến phụ trợ (Chained XOR Encoding):**
  Với $n \ge 3$, đặt $y_1 = x_1 \oplus x_2, y_2 = y_1 \oplus x_3, \dots, y_{n-2} = y_{n-3} \oplus x_{n-1}$.
  Mỗi phép tương đương $y = u \oplus v$ được biểu diễn chính xác bằng 4 mệnh đề 3-literal:
  $$(\neg u \vee \neg v \vee \neg y) \wedge (u \vee v \vee \neg y) \wedge (u \vee \neg v \vee y) \wedge (\neg u \vee v \vee y)$$
  Cuối cùng, $y_{n-2} \oplus x_n = \text{parity}$ được mã hóa trực tiếp bằng 2 mệnh đề 2-literal.
- **Độ phức tạp:** $O(n)$ mệnh đề và $n-2$ biến phụ trợ, tối ưu hơn rất nhiều so với bùng nổ tổ hợp $2^{n-1}$.

### 3.2. So sánh số lượng giữa hai vùng (COMPARE / COUNT_COMPARE)
- **Ý nghĩa:** $\sum_{i \in R_1} x_i \text{ op } \sum_{j \in R_2} y_j$ với $\text{op} \in \{<, ==, >, \le, \ge, \ne\}$.
- **Mã hóa biến chỉ thị (Indicator Variables):**
  Định nghĩa các biến phụ $p_k \iff \sum_{i \in R_1} x_i = k$ và $q_m \iff \sum_{j \in R_2} y_j = m$.
  - Ép ít nhất một $p_k$ và một $q_m$ True: $(p_0 \vee \dots \vee p_{n_1})$, $(q_0 \vee \dots \vee q_{n_2})$.
  - Liên kết $p_k \rightarrow (\sum R_1 = k)$: $\bigwedge (\neg p_k \vee c)$ với $c \in \text{EXACTLY}(k, R_1)$.
  - Cấm tất cả các cặp $(k, m)$ vi phạm toán tử $\text{op}$: $(\neg p_k \vee \neg q_m)$.

### 3.3. Các biểu thức vùng nâng cao (Advanced Region Expressions)
Hỗ trợ đầy đủ bộ phân giải vùng:
- Core: `row`, `column`, `neighbors`, `cells` (explicit list).
- Advanced: `corners`, `boundary`, `interior`, `common_neighbors`, `between`, và các phép toán tập hợp `intersection`, `union`, `difference`.

---

## 4. Kết quả thực nghiệm & Kiểm tra chéo (Cross-Check)

Theo checklist bắt buộc trước khi nộp đồ án: **"Test chéo encoder và evaluator bằng brute-force"**.

### 4.1. Bộ test chéo tích hợp với Thành viên D (`tools/cross_check.py`)
Đã tích hợp hoàn hảo với hệ thống benchmark và 24 puzzle JSON chính thức của Thành viên D:
- **Tập kiểm tra:**
  - $N=3$: Toàn bộ 141 clues (puzzles + random candidates) $\times$ 512 phép gán toàn cục exhaustive ($2^9$).
  - $N=4$: 236 clues $\times$ 400 phép gán ngẫu nhiên.
  - $N=5$: 160 clues $\times$ 400 phép gán ngẫu nhiên.
- **Kết quả kiểm tra:**
  ```text
  N=3: 141 clues x 512 assignments checked
  N=4: 236 clues x 400 assignments checked
  N=5: 160 clues x 400 assignments checked

  230592 checks, 0 failures
  ```
  **100% khớp tuyệt đối qua 230,592 phép thử!**

### 4.2. Bộ Unit Test độc lập (`tests/run_tests.py`)
Bao gồm 20 bài kiểm tra đơn vị:
- Kiểm tra tính toán tọa độ, 8-neighbors, và phân giải vùng.
- Kiểm tra VarManager với 2 quy tắc sắp xếp (Row-major và Alpha).
- Kiểm tra đánh giá ngữ nghĩa trực tiếp (SemanticEvaluator).
- Kiểm tra tương đương logic giữa CNF và Semantic Evaluator trên không gian trạng thái $2^{|V|}$.
- Kết quả: **20/20 test cases PASSED** trong 0.014s.

---

## 5. Phụ lục AI / LLM Usage

Theo quy định báo cáo của môn học:
- **Mục đích sử dụng AI:**
  1. Hỗ trợ rà soát các trường hợp biên của dẫn xuất CNF cardinality constraints (binomial encoding và indicator variables).
  2. Thiết kế và kiểm tra các công thức Boolean logic cho Chained XOR Parity Encoding.
  3. Viết bộ kiểm thử tự động, chuẩn hóa typing và docstrings cho Python.
- **Các prompt tiêu biểu đã dùng:**
  - *"Dẫn xuất công thức CNF tối ưu cho phép toán so sánh count(R1) op count(R2) với op thuộc [<, ==, >] sử dụng auxiliary indicator variables sao cho DPLL solver giải nhanh và tránh bùng nổ mệnh đề."*
  - *"Viết script kiểm tra chéo exhaustive brute-force so sánh chân trị ngữ nghĩa của Clue với tính khả thỏa của công thức CNF sau khi gán biến sơ cấp."*


---

## 6. Tài liệu tham khảo (References)

1. **Game tham khảo:** Cơ chế suy luận thẻ bài dựa trên trò chơi gốc **Clues By Sam** ([https://cluesbysam.com/](https://cluesbysam.com/)).
2. **Tài liệu hướng dẫn môn học:** Đồ án 2 - Logic Mệnh đề & Trò chơi Griductive, Trường ĐH Khoa học Tự nhiên, ĐHQG-HCM.
3. **Mã hóa mệnh đề SAT:** C. Sinz, *"Towards an Optimal CNF Encoding of Boolean Cardinality Constraints"*, Principles and Practice of Constraint Programming - CP 2005.
