# Báo cáo Phần A: Logic Core & CNF Encoding
**Môn học:** CSC14003 - Nhập môn Trí tuệ Nhân tạo  
**Đồ án:** Griductive Solver  
**Người thực hiện:** Thành viên phụ trách Phần A (Logic Core)

---

## 1. Mô tả bài toán & Biểu diễn Logic Mệnh đề

### 1.1. Biến mệnh đề sơ cấp (Primary Propositional Variables)
Với mỗi nhân vật $i$ tại ô $(r, c)$ trên lưới $N \times N$, ta định nghĩa một biến mệnh đề sơ cấp duy nhất:
$$C_i = \begin{cases} \text{True}, & \text{nếu nhân vật } i \text{ là Tội phạm (Criminal)} \\ \text{False}, & \text{nếu nhân vật } i \text{ là Vô tội (Innocent)} \end{cases}$$

Quy tắc ánh xạ xác định (Deterministic Mapping):
- Các nhân vật được sắp xếp theo thứ tự bảng chữ cái tên hiển thị (display name) theo quy định mục 2.1 của đề bài, với ô tọa độ làm tie-breaker.
- Các biến sơ cấp được đánh số liên tục từ $1$ đến $M = N^2$.
- Ánh xạ hai chiều được duy trì: `name -> var_id`, `cell_id -> var_id`, và `var_id -> cell_id/name`.

### 1.2. Biến phụ trợ (Auxiliary Variables)
Các biến phụ trợ (Auxiliary Variables) được sinh tự động khi mã hóa các ràng buộc nâng cao (như chuỗi XOR chẵn/lẻ Parity hoặc so sánh số lượng Count Compare).
- Tất cả các biến phụ trợ được phân tách nghiêm ngặt với biến sơ cấp: bắt đầu từ số hiệu $M + 1, M + 2, \dots$.
- Trình quản lý biến `VarManager` theo dõi và báo cáo chính xác số lượng biến sơ cấp và biến phụ trợ.

---

## 2. Ngôn ngữ Clue cốt lõi & Dẫn xuất CNF

Mỗi clue có cấu trúc $CL$ được tự động chuyển đổi thành tập các mệnh đề CNF $CNF(CL)$.

### 2.1. Clue Đơn vị (FACT)
- **Ý nghĩa:** Một nhân vật xác định có trạng thái cụ thể.
- **Dạng logic:** $C_i$ (nếu Criminal) hoặc $\neg C_i$ (nếu Innocent).
- **Mệnh đề CNF:**
  - Nếu Criminal: $(C_i)$ [1 mệnh đề unit literal $+v_i$]
  - Nếu Innocent: $(\neg C_i)$ [1 mệnh đề unit literal $-v_i$]

### 2.2. Clue Cùng trạng thái (SAME)
- **Ý nghĩa:** Hai nhân vật $i$ và $j$ có cùng trạng thái (cùng là Criminal hoặc cùng là Innocent).
- **Dạng logic:** $C_i \leftrightarrow C_j \equiv (C_i \rightarrow C_j) \wedge (C_j \rightarrow C_i)$.
- **Dẫn xuất CNF:**
  $$C_i \leftrightarrow C_j \equiv (\neg C_i \vee C_j) \wedge (C_i \vee \neg C_j)$$
- **Số mệnh đề:** 2 mệnh đề nhị phân: $[-v_i, v_j]$ và $[v_i, -v_j]$.

### 2.3. Clue Khác trạng thái (DIFFERENT)
- **Ý nghĩa:** Hai nhân vật $i$ và $j$ có trạng thái trái ngược nhau (phép XOR).
- **Dạng logic:** $C_i \oplus C_j \equiv (C_i \vee C_j) \wedge \neg(C_i \wedge C_j)$.
- **Dẫn xuất CNF:**
  $$C_i \oplus C_j \equiv (C_i \vee C_j) \wedge (\neg C_i \vee \neg C_j)$$
- **Số mệnh đề:** 2 mệnh đề nhị phân: $[v_i, v_j]$ và $[-v_i, -v_j]$.

### 2.4. Clue Đếm số lượng (Cardinality Constraints)

Gọi vùng tham chiếu $R = \{x_1, x_2, \dots, x_n\}$ là tập hợp các literal tương ứng với các nhân vật trong vùng (với $n = |R|$). Nếu đếm Criminal, $x_i = +v_i$; nếu đếm Innocent, $x_i = -v_i$.

#### A. Ràng buộc Tối thiểu $\text{AT\_LEAST}(k, R)$: $\sum_{i \in R} x_i \ge k$
- **Ý nghĩa:** Có ít nhất $k$ người mang trạng thái mục tiêu trong vùng $R$.
- **Dẫn xuất Tổ hợp trực tiếp (Binomial Encoding):**
  Để có ít nhất $k$ biến mang giá trị True trong $n$ biến, không thể tồn tại bất kỳ tập con nào gồm $n - k + 1$ biến mà toàn bộ đều nhận giá trị False. Do đó, với mỗi tập con $S \subseteq R$ có kích thước $|S| = n - k + 1$:
  $$\bigvee_{x \in S} x$$
- **Số mệnh đề sinh ra:** $\binom{n}{n - k + 1} = \binom{n}{k - 1}$.
- **Ví dụ cụ thể:** Với $R = \{A, B, C\}$ ($n=3$), yêu cầu $\ge 2$ Criminals ($k=2$):
  - Kích thước tập con: $3 - 2 + 1 = 2$.
  - Các cặp tập con: $\{A, B\}, \{A, C\}, \{B, C\}$.
  - Công thức CNF: $(C_A \vee C_B) \wedge (C_A \vee C_C) \wedge (C_B \vee C_C)$.

#### B. Ràng buộc Tối đa $\text{AT\_MOST}(k, R)$: $\sum_{i \in R} x_i \le k$
- **Ý nghĩa:** Có nhiều nhất $k$ người mang trạng thái mục tiêu trong vùng $R$.
- **Dẫn xuất Tổ hợp trực tiếp (Binomial Encoding):**
  Để có nhiều nhất $k$ biến mang giá trị True, không thể tồn tại bất kỳ tập con nào gồm $k + 1$ biến mà toàn bộ đều nhận giá trị True. Do đó, với mỗi tập con $S \subseteq R$ có kích thước $|S| = k + 1$:
  $$\bigvee_{x \in S} \neg x$$
- **Số mệnh đề sinh ra:** $\binom{n}{k + 1}$.
- **Ví dụ cụ thể:** Với $R = \{A, B, C\}$ ($n=3$), yêu cầu $\le 1$ Criminal ($k=1$):
  - Kích thước tập con: $1 + 1 = 2$.
  - Công thức CNF: $(\neg C_A \vee \neg C_B) \wedge (\neg C_A \vee \neg C_C) \wedge (\neg C_B \vee \neg C_C)$.

#### C. Ràng buộc Chính xác $\text{EXACTLY}(k, R)$: $\sum_{i \in R} x_i = k$
- **Dẫn xuất:**
  $$\text{EXACTLY}(k, R) \equiv \text{AT\_LEAST}(k, R) \wedge \text{AT\_MOST}(k, R)$$
- **Số mệnh đề sinh ra:** $\binom{n}{n - k + 1} + \binom{n}{k + 1}$.
- Các trường hợp đặc biệt:
  - $k = 0$: tương đương $n$ mệnh đề đơn vị $(\neg x_1) \wedge (\neg x_2) \wedge \dots \wedge (\neg x_n)$.
  - $k = n$: tương đương $n$ mệnh đề đơn vị $(x_1) \wedge (x_2) \wedge \dots \wedge (x_n)$.

---

## 3. Các Phần Mở rộng (Extensions)

Đề bài yêu cầu ít nhất 2 phần mở rộng riêng biệt. Phần A cài đặt 3 nhóm mở rộng vượt chuẩn:

### 3.1. Mở rộng 1: Ràng buộc Tính chẵn lẻ (PARITY Constraint)
- **Cú pháp:** $\text{PARITY}(R, p)$ với $p \in \{0, 1\}$ ($p = 0$: số Criminal là CHẴN; $p = 1$: số Criminal là LẺ).
- **Dạng logic:** $x_1 \oplus x_2 \oplus \dots \oplus x_n = p$.
- **Mã hóa CNF tuyến tính dùng biến phụ trợ:**
  Thay vì bùng nổ lũy thừa $2^{n-1}$ mệnh đề, ta xâu chuỗi các biến phụ trợ $a_1, a_2, \dots, a_{n-2}$:
  $$a_1 \leftrightarrow (x_1 \oplus x_2), \quad a_2 \leftrightarrow (a_1 \oplus x_3), \quad \dots, \quad a_{n-2} \leftrightarrow (a_{n-3} \oplus x_{n-1})$$
  Mỗi phương trình $a \leftrightarrow (b \oplus c)$ được chuyển thành 4 mệnh đề 3-literal:
  $$(\neg b \vee \neg c \vee \neg a) \wedge (b \vee c \vee \neg a) \wedge (b \vee \neg c \vee a) \wedge (\neg b \vee c \vee a)$$
  Mệnh đề cuối cùng liên kết $a_{n-2} \oplus x_n = p$.
- **Hiệu quả:** Số biến phụ trợ là $n - 2$, số mệnh đề chỉ là $4(n-2) + 2 = 4n - 6$ (tuyến tính $O(n)$).

### 3.2. Mở rộng 2: So sánh Số lượng giữa hai Vùng (COUNT_COMPARE)
- **Cú pháp:** $\text{COUNT\_COMPARE}(R_1, \text{op}, R_2)$ với $\text{op} \in \{>, \ge, ==, !=, <, \le\}$.
- **Ý nghĩa:** Số lượng Criminal ở vùng $R_1$ thỏa mãn phép toán so sánh với vùng $R_2$.
- **Mã hóa CNF:**
  Đặt các biến chỉ thị phụ trợ $p_k \leftrightarrow (\sum_{R_1} = k)$ và $q_m \leftrightarrow (\sum_{R_2} = m)$.
  Với mọi cặp $(k, m)$ mà $\text{op}(k, m) == \text{False}$, ta thêm mệnh đề cấm:
  $$(\neg p_k \vee \neg q_m)$$

### 3.3. Mở rộng 3: Bộ Resolver Vùng Nâng cao (Advanced Regions)
- `CORNERS`: 4 ô góc của bàn cờ $N \times N$.
- `BOUNDARY`: Các ô trên đường bao ngoài của bàn cờ.
- `INTERIOR`: Các ô nằm hoàn toàn bên trong.
- `COMMON_NEIGHBORS(c1, c2)`: Các ô đồng thời là hàng xóm của cả $c1$ và $c2$.
- `BETWEEN(c1, c2)`: Các ô nằm thẳng hàng nằm giữa hai nhân vật.
- `INTERSECTION`, `UNION`, `DIFFERENCE`: Các phép toán tập hợp đại số trên vùng.

---

## 4. Evaluator Ngữ nghĩa Trực tiếp (Direct Semantic Evaluator)

Yêu cầu mục 4.2 nêu rõ:
> "At least one direct semantic evaluator must be implemented for each required clue template. Given a complete assignment, this evaluator states whether the clue is true without calling the CNF encoder."

Class `SemanticEvaluator` cài đặt việc kiểm tra trực tiếp:
- Nhận vào một `Clue` và một phép gán hoàn chỉnh `Dict[str, bool]` (hoặc `Dict[str, Status]`).
- Truy xuất trạng thái trực tiếp của các ô tham chiếu thông qua `RegionResolver`.
- Đếm số lượng, kiểm tra logic trực tiếp mà hoàn toàn không gọi đến bộ mã hóa CNF.
- Đảm bảo độc lập tuyệt đối giữa mô hình ngữ nghĩa và mô hình giải tích mệnh đề.

---

## 5. Kiểm thử Chéo Toàn diện bằng Vét cạn (Brute-Force Cross-Check)

Theo checklist bắt buộc trước khi nộp:
> "Test chéo encoder và evaluator bằng brute-force"

Tập test `tests/test_cross_check.py` thực hiện kiểm thử hình thức:
- Với mỗi template clue ($CL$), duyệt qua toàn bộ $2^{|V|}$ phép gán chân trị khả dĩ (với $|V|$ là số biến trong phạm vi của clue).
- Kiểm tra tính tương đương logic tuyệt đối:
  $$\text{SemanticEvaluator.evaluate}(CL, \alpha) == \text{CNFFormula.is\_satisfied\_by}(\alpha)$$
- Đối với các công thức có biến phụ trợ, kiểm tra:
  $$\text{SemanticEvaluator.evaluate}(CL, \alpha) \iff \exists \beta_{\text{aux}}: \text{CNFFormula.is\_satisfied\_by}(\alpha \cup \beta_{\text{aux}})$$

**Kết quả thực nghiệm:**
Toàn bộ 20 bài test trong `tests/run_tests.py` (bao gồm kiểm thử vét cạn mọi giá trị $k$, các toán tử so sánh, chẵn lẻ, các phép toán vùng) đạt tỉ lệ chính xác **100% (20/20 passed)** trong thời gian **0.011s**.

---

## 6. Mô hình Cơ sở Tri thức ($KB_t$)

Lớp `KnowledgeBase` duy trì trạng thái tri thức công khai tại bước suy luận $t$:
$$KB_t = CNF(\text{revealed clues}) \wedge \bigwedge_{v \in \text{proved}} (\text{unit clause for } v)$$

- **Nguyên tắc cô lập:** Tuyệt đối không đọc trường `hidden_status` hay các clue chưa lật của nhân vật.
- Hỗ trợ xuất dữ liệu ra định dạng chuẩn quốc tế DIMACS CNF (`to_dimacs()`) để các thành viên Phần B (DPLL Solver) dễ dàng tích hợp.
- Cung cấp hàm `report_stats()` trả về số lượng biến sơ cấp, biến phụ trợ và số mệnh đề CNF sinh ra.

---

## 7. Phụ lục: Quá trình sử dụng Generative AI & Prompts

| Mục đích | Prompt sử dụng | Đánh giá & Điều chỉnh |
|---|---|---|
| Thiết kế kiến trúc module Logic | "Thiết kế kiến trúc module logic cho bài toán Griductive Solver gồm VarManager, RegionResolver, SemanticEvaluator, CNFEncoder theo đúng đặc tả mục 4.2 của đề tài." | Mô hình đề xuất cấu trúc phân tách rõ ràng; đã bổ sung thêm tie-breaker cho thứ tự nhân vật và ánh xạ tọa độ chuẩn. |
| Dẫn xuất công thức Parity tuyến tính | "Viết công thức mã hóa CNF cho ràng buộc xor(x1..xn) = p sử dụng biến phụ trợ sao cho số mệnh đề là tuyến tính O(n)." | Sử dụng mô hình xâu chuỗi biến phụ trợ $a_i \leftrightarrow a_{i-1} \oplus x_i$. Đã kiểm tra lại tính đúng đắn bằng bảng chân trị. |
| Xây dựng test chéo vét cạn (brute-force) | "Viết script brute-force duyệt qua toàn bộ 2^N mô hình để đối chiếu kết quả của Semantic Evaluator và CNF Encoder cho mọi clue template." | Sinh ra module `test_cross_check.py`. Giúp phát hiện sớm và chuẩn hóa trường hợp biến phụ trợ bằng phép chiếu nghiệm tồn tại $\exists \beta$. |
