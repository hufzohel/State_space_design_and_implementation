# AI Search Project

Project tìm hiểu và triển khai các thuật toán tìm kiếm trên không gian trạng thái cho hai bài toán:

* **Pipes**
* **Minesweeper**

Project sử dụng **Python 3** cho phần xử lý bài toán và thuật toán tìm kiếm, **FastAPI** làm backend API, và **HTML/CSS/JavaScript** cho giao diện web.

---

## Cài đặt và chạy

Yêu cầu: Python 3.

Cài thư viện (từ thư mục gốc của repo):

```text
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Trên Linux/macOS, thay lệnh kích hoạt bằng `source .venv/bin/activate`.

Chạy backend (từ thư mục gốc của repo):

```text
uvicorn backend.main:app
```

Backend lắng nghe tại `http://127.0.0.1:8000`, đúng địa chỉ mà `frontend/js/api.js` gọi (`http://127.0.0.1:8000/api`). CORS được cấu hình cho phép mọi origin (`allow_origins=["*"]` trong `backend/main.py`).

Chạy frontend, chọn một trong hai cách:

* Mở `frontend/index.html` bằng Live Server (VS Code).
* Hoặc, trong thư mục `frontend`, chạy `python -m http.server 5500` rồi mở `http://localhost:5500`.

Phần benchmark xem ở mục "Chạy benchmark" cuối file.

---

## 1. Cấu trúc thư mục

```text
ai-search-project/
│
├── README.md
├── requirements.txt
├── .gitignore
│
├── backend/
│   ├── main.py
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py
│   │   └── .gitkeep
│   │
│   ├── common/
│   │   ├── __init__.py
│   │   ├── search.py
│   │   ├── node.py
│   │   ├── result.py
│   │   └── .gitkeep
│   │
│   ├── puzzles/
│   │   ├── pipes/
│   │   │   ├── state.py
│   │   │   ├── puzzle.py
│   │   │   ├── generator.py
│   │   │   ├── heuristic.py
│   │   │   └── .gitkeep
│   │   │
│   │   └── minesweeper/
│   │       ├── state.py
│   │       ├── puzzle.py
│   │       ├── generator.py
│   │       ├── heuristic.py
│   │       └── .gitkeep
│   │
│   └── search/
│       ├── __init__.py
│       ├── bfs.py
│       ├── dfs.py
│       ├── astar.py
│       └── .gitkeep
│
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── style.css
│   │   └── .gitkeep
│   │
│   ├── js/
│   │   ├── app.js
│   │   ├── api.js
│   │   ├── renderer.js
│   │   ├── playback.js
│   │   └── .gitkeep
│   │
│   └── assets/
│       └── .gitkeep
│
├── experiments/
│   ├── run_benchmark.py
│   ├── verify_pipes_heuristic.py
│   │
│   └── results/
│
├── tests/
│   ├── test_pipes.py
│   ├── test_minesweeper.py
│   ├── test_search.py
│   ├── test_generators.py
│   └── .gitkeep
│
└── docs/
    ├── state-space.md
    ├── algorithms.md
    ├── experiments.md
    ├── architecture.md
    └── .gitkeep
```

---

# 2. Phạm vi từng thư mục

## `backend/`

Chứa toàn bộ phần xử lý phía server:

* Logic của hai puzzle.
* Biểu diễn state.
* Sinh successor.
* Thuật toán tìm kiếm.
* Heuristic.
* API giao tiếp với frontend.

Không chứa code giao diện.

---

## `backend/api/`

Phụ trách **giao tiếp giữa frontend và backend**.

### `routes.py`

Định nghĩa các API endpoint, ví dụ:

* Tạo puzzle.
* Lấy state hiện tại.
* Cập nhật state.
* Yêu cầu solver giải.
* Lấy kết quả/statistics.

**Không viết logic giải puzzle hoặc thuật toán tìm kiếm trực tiếp ở đây.**

---

## `backend/common/`

Chứa những thành phần thực sự dùng chung cho nhiều puzzle/search algorithm.

### `search.py`

Các interface hoặc thành phần dùng chung cho search.

### `node.py`

Định nghĩa cấu trúc node trong search tree/graph.

Ví dụ thông tin có thể gồm:

* State.
* Parent.
* Action.
* Cost.
* Depth.

### `result.py`

Định nghĩa kết quả trả về từ thuật toán tìm kiếm.

Có thể chứa:

* Solution.
* Path.
* Number of expanded nodes.
* Execution time.
* Memory usage.
* Search status.

**Chỉ đặt code dùng chung ở đây. Nếu code chỉ phục vụ Pipes hoặc Minesweeper thì để trong puzzle tương ứng.**

---

# 3. Puzzle modules

## `backend/puzzles/pipes/`

Toàn bộ logic riêng của **Pipes**.

### `state.py`

Định nghĩa cách biểu diễn state của Pipes.

Ví dụ:

* Vị trí các tile.
* Orientation của từng tile.
* Các thông tin cần thiết để xác định trạng thái.

### `puzzle.py`

Chứa luật của puzzle:

* State ban đầu.
* Goal test.
* Các action hợp lệ.
* Sinh successor.
* Kiểm tra trạng thái hợp lệ.

### `generator.py`

Sinh các input Pipes để:

* Test.
* Demo.
* Benchmark.

### `heuristic.py`

Các heuristic dành riêng cho Pipes.

---

## `backend/puzzles/minesweeper/`

Toàn bộ logic riêng của **Minesweeper**.

### `state.py`

Định nghĩa state representation của Minesweeper.

### `puzzle.py`

Chứa:

* Luật Minesweeper.
* Goal test.
* Các action.
* Sinh successor.
* Kiểm tra trạng thái.

### `generator.py`

Sinh các board Minesweeper dùng cho:

* Test.
* Demo.
* Benchmark.

### `heuristic.py`

Các heuristic dành riêng cho Minesweeper.

---

# 4. Search algorithms

## `backend/search/`

Chứa các thuật toán tìm kiếm **độc lập với puzzle**.

### `bfs.py`

Breadth-First Search.

### `dfs.py`

Depth-First Search.

### `astar.py`

A* Search.

Các thuật toán trong thư mục này **không được chứa logic riêng của Pipes hoặc Minesweeper**.

Thay vào đó, search algorithm làm việc thông qua interface của puzzle:

```text
State
  ↓
Possible Actions
  ↓
Successor States
  ↓
Goal Test
```

Nhờ đó cùng một BFS/DFS/A* có thể sử dụng cho nhiều puzzle.

---

# 5. Frontend

## `frontend/`

Chứa toàn bộ giao diện web.

Frontend chỉ chịu trách nhiệm:

* Hiển thị puzzle.
* Nhận input từ người dùng.
* Gửi request tới backend.
* Hiển thị kết quả.
* Playback solution.

**Không đặt logic BFS/DFS/A* hoặc luật puzzle ở frontend.**

---

## `frontend/index.html`

Cấu trúc chính của trang web.

Ví dụ:

* Puzzle board.
* Buttons.
* Control panel.
* Algorithm selection.
* Statistics.
* Solution controls.

---

## `frontend/css/`

### `style.css`

Chứa:

* Layout.
* Grid.
* Button.
* Màu sắc.
* Animation.
* Responsive styling.

---

## `frontend/js/`

### `app.js`

Controller chính của frontend.

Chịu trách nhiệm kết nối các thành phần:

```text
User Input
    ↓
app.js
    ↓
api.js
    ↓
Backend
```

### `api.js`

Chứa các hàm gọi FastAPI.

Ví dụ:

```text
createPuzzle()
solvePuzzle()
updateState()
getResult()
```

### `renderer.js`

Chịu trách nhiệm render state lên màn hình.

Ví dụ:

```text
State
  ↓
renderer.js
  ↓
HTML elements
```

### `playback.js`

Chạy lại solution/action sequence từng bước để người dùng quan sát quá trình giải.

Ví dụ:

```text
Initial State
      ↓
Action 1
      ↓
Action 2
      ↓
Action 3
      ↓
Solved State
```

---

## `frontend/assets/`

Chứa các tài nguyên tĩnh nếu cần:

* Images.
* Icons.
* Fonts.
* Các asset khác.

---

# 6. Experiments

## `experiments/`

Chứa code phục vụ **benchmark và thí nghiệm**.

Phần này nên độc lập với frontend.

### `run_benchmark.py`

Chạy benchmark trên nhiều cỡ bảng và nhiều seed:

* Pipes: DFS và A*.
* Minesweeper: Online DFS và Greedy.

Mỗi lần chạy là một tiến trình riêng; thời gian và bộ nhớ (tracemalloc) được đo ở hai lượt tách biệt. Mỗi lần chạy ghi một dòng JSON (status, seconds, steps, expanded, peak_mb, ...). Lệnh `summary` tổng hợp file kết quả thành bảng theo cỡ bảng và thuật toán. Cách chạy xem mục "Chạy benchmark" ở cuối file.

### `verify_pipes_heuristic.py`

Kiểm tra heuristic của Pipes trên các bàn 3x3 bằng cách so với khoảng cách tối ưu thật h*(s) (vét cạn mọi cấu hình đích): A* có tối ưu không, heuristic có vượt h* không, h = 0 có luôn là đích không, và việc cắt tỉa `outward_openings` có làm đổi kết quả A* không.

---

## `experiments/results/`

Nơi `run_benchmark.py` ghi kết quả (file `.jsonl`). Thư mục được tạo tự động khi chạy benchmark và nằm trong `.gitignore`, nên không được commit.

---

# 7. Tests

## `tests/`

Chứa automated tests.

### `test_pipes.py`

Kiểm tra logic Pipes.

### `test_minesweeper.py`

Kiểm tra logic Minesweeper.

### `test_search.py`

Kiểm tra BFS/DFS/A*.

### `test_generators.py`

Kiểm tra puzzle generators.

Mục tiêu chính:

```text
Puzzle logic đúng
        ↓
Search đúng
        ↓
Benchmark đáng tin cậy
```

---

# 8. Documentation

## `docs/`

Chứa tài liệu kỹ thuật của project.

### `state-space.md`

Mô tả:

* State representation.
* State space.
* Initial state.
* Goal state.
* Operators.
* Constraints.
* Heuristic-related information.

### `algorithms.md`

Mô tả:

* BFS.
* DFS.
* A*.
* Heuristic.

### `experiments.md`

Mô tả:

* Input generation.
* Benchmark methodology.
* Metrics.
* Experimental setup.
* Kết quả.

### `architecture.md`

Mô tả kiến trúc tổng thể:

```text
Browser
   ↓
HTML / CSS / JavaScript
   ↓
FastAPI
   ↓
Puzzle + Search
   ↓
Result / Solution Trace
   ↓
Frontend Playback
```

---

# 9. Nguyên tắc phân chia công việc

## 1. Làm việc trong scope của mình

Nếu được giao:

```text
backend/puzzles/pipes/
```

thì ưu tiên chỉ sửa các file trong module đó.

Không tự ý sửa module của người khác nếu không cần thiết.

---

## 2. Puzzle logic và Search phải tách biệt

Puzzle chịu trách nhiệm:

```text
State
Action
Successor
Goal Test
Heuristic
```

Search chịu trách nhiệm:

```text
BFS
DFS
A*
```

Ví dụ:

```text
          ┌──────────────┐
          │    Search    │
          │ BFS / DFS/A* │
          └──────┬───────┘
                 │
                 ↓
          ┌──────────────┐
          │    Puzzle    │
          │              │
          │ State        │
          │ Successor    │
          │ Goal Test    │
          │ Heuristic    │
          └──────────────┘
```

---

## 3. Frontend và Backend phải tách biệt

Frontend không tự giải puzzle.

```text
Frontend
   │
   │ API request
   ↓
Backend
   │
   ├── Puzzle
   └── Search
   │
   ↓
Solution / Statistics
   │
   ↓
Frontend
```

---

## 4. Benchmark không phụ thuộc Frontend

Không đo thời gian kiểu:

```text
Browser → API → Solver → API → Browser
```

để đánh giá thuật toán.

Benchmark nên chạy trực tiếp:

```text
Input
  ↓
Search Algorithm
  ↓
Result
```

Điều này giúp tránh việc thời gian mạng, FastAPI hoặc rendering ảnh hưởng đến kết quả thuật toán.

---

## 5. Ưu tiên correctness trước optimization

Thứ tự phát triển:

```text
Puzzle logic
     ↓
Search correctness
     ↓
Frontend integration
     ↓
Benchmark
     ↓
Optimization
```

Không tối ưu trước khi có benchmark chứng minh vấn đề cần tối ưu.

---

# 10. Quy ước khi thêm file

Trước khi tạo file mới, kiểm tra xem chức năng đó có thực sự thuộc module hiện tại không.

Ví dụ:

```text
Pipes-specific
    → backend/puzzles/pipes/

Minesweeper-specific
    → backend/puzzles/minesweeper/

Search algorithm
    → backend/search/

Shared search component
    → backend/common/

Frontend display
    → frontend/

Benchmark
    → experiments/
```

Không tạo thêm abstraction chỉ để “cho đẹp”.

**Mục tiêu của structure này là modularity đủ để nhiều người làm song song, không phải over-engineering.**

---

# 11. Luồng hoạt động tổng quát

```text
                    USER
                      │
                      ↓
               ┌─────────────┐
               │   Browser   │
               │ HTML/CSS/JS │
               └──────┬──────┘
                      │
                   REST API
                      │
                      ↓
               ┌─────────────┐
               │   FastAPI   │
               └──────┬──────┘
                      │
             ┌────────┴────────┐
             ↓                 ↓
        ┌──────────┐      ┌──────────┐
        │  Pipes   │      │Minesweep.│
        └────┬─────┘      └────┬─────┘
             │                 │
             └────────┬────────┘
                      ↓
              ┌───────────────┐
              │ Search Engine │
              │ BFS / DFS/A*  │
              └───────┬───────┘
                      │
                      ↓
              Solution + Stats
                      │
                      ↓
                  Frontend
                      │
                      ↓
                  Playback
```

---

# 12. Git workflow cơ bản

Mỗi thành viên nên làm việc trên branch riêng:

```text
main
 │
 ├── feature/pipes
 ├── feature/minesweeper
 ├── feature/search
 ├── feature/frontend
 └── feature/benchmark
```

Commit nên mô tả rõ thay đổi:

```text
feat: implement pipes state
feat: add bfs search
feat: add minesweeper generator
feat: add solution playback
test: add pipes state tests
```

Tránh commit quá nhiều thay đổi không liên quan trong cùng một commit.

## Chạy benchmark

Chạy các lệnh dưới đây từ thư mục gốc của repo.

```text
python experiments/run_benchmark.py pipes        --out experiments/results/pipes.jsonl
python experiments/run_benchmark.py minesweeper  --out experiments/results/ms.jsonl --seeds 100
python experiments/run_benchmark.py summary      --out experiments/results/pipes.jsonl --kind pipes
python experiments/run_benchmark.py summary      --out experiments/results/ms.jsonl --kind minesweeper
python experiments/verify_pipes_heuristic.py
```

* Pipes mặc định chạy 10 seed mỗi cỡ bảng; Minesweeper dùng `--seeds 100`.
* Mỗi lần chạy là một tiến trình Python riêng. Thời gian và bộ nhớ (tracemalloc) được đo ở hai lượt tách biệt, vì tracemalloc làm chương trình chậm đi.
* Kết quả được ghi vào `experiments/results/` (thư mục này không được commit).