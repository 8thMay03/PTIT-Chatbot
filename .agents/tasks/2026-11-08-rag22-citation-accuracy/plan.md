# Plan: 2026-11-08-rag22-citation-accuracy

Nhánh: `feat/rag22-citation-accuracy` tách từ `dev` đã cập nhật. Mặc định một agent (`agent-claude`) làm tuần tự. Nếu có thêm agent: S-01 (luồng trả lời) và S-02/S-03 (Điều/Khoản) không chung file mã nên chạy song song được. S-05a phải chạy trước mọi thay đổi ở `citations.py` để chụp locator "trước".

## Phân công

### S-01 — Bỏ tự gắn citation, nhận diện câu từ chối

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-01`, `AC-02`.
  - Module mới `backend/app/generation/refusal.py`: hằng số `NO_CONTEXT_ANSWER` (chuyển từ `rag_chain.py:20`), hàm `is_refusal(answer)` theo hợp đồng bên dưới. Thay literal ở `routes.py:1451`, `llm.py:142` bằng hằng số. `rag_chain.py` import lại `NO_CONTEXT_ANSWER` để không vỡ import cũ.
  - `_normalize_answer_citations` (`llm.py:132-148`): bỏ nhánh nối `[min(valid_ids)]`; câu từ chối thì xóa mọi `[n]`; còn lại chỉ xóa `[n]` không hợp lệ. Giữ chữ ký và tên hàm.
  - `sources` rỗng khi câu trả lời là câu từ chối: `/chat/stream` (`routes.py`, event `done` và `assistant_metadata["sources"]`), `/chat` (`rag_chain.py:110`). `contexts`/`retrieval_debug` lưu DB giữ nguyên để debug.
  - `build_context_prompt` (`prompts.py`) thêm dòng câu từ chối "không có thông tin" nguyên văn, cạnh dòng câu từ chối ngoài phạm vi.
- Phạm vi file được sửa: `backend/app/generation/refusal.py` (mới), `backend/app/generation/llm.py`, `backend/app/generation/prompts.py`, `backend/app/generation/rag_chain.py`, `backend/app/api/routes.py` (chỉ đoạn `public_citations`/câu từ chối/chuẩn hóa trong luồng chat), `backend/tests/test_refusal.py` (mới), `backend/tests/test_prompts.py`, `backend/tests/test_rag_chain.py`, test luồng `/chat/stream` hiện có có kiểm `sources` (tìm bằng `rg "sources" backend/tests`).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng `is_refusal`; test cho đủ các trường hợp trong `AC-01`, `AC-02` (gồm sửa `test_answer_citations_are_limited_to_provided_sources`, hiện khẳng định hành vi tự gắn `[1]`).
- Người nhận: `agent-claude` (S-06, verifier).

### S-02 — Quy tắc Điều/Khoản/Điểm dùng chung

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: hàm thuần trích Điều/Khoản/Điểm theo cấu trúc, chỉ nhận Khoản/Điểm trong ngữ cảnh Điều; `citations.py` dùng hàm này làm đường dự phòng thay cho regex cũ. Phục vụ `AC-03`, là nền cho S-03.
- Phạm vi file được sửa: `backend/app/ingestion/legal_units.py` (mới; đặt ở `ingestion` để chunker dùng được, `citations.py` import một chiều), `backend/app/generation/citations.py`, `backend/tests/test_legal_units.py` (mới), `backend/tests/test_citations.py`.
- Phụ thuộc: S-05a đã chụp locator "trước" (S-02 là thay đổi đầu tiên làm đổi locator).
- Đầu ra/bàn giao: hợp đồng `extract_legal_units` (mục Hợp đồng dùng chung); test: danh sách đánh số/`a)` ngoài Điều, bảng chứa `1.` trong ô, Điều ở heading, Điều ở `section_path`, Điều chỉ có ở các dòng đầu của text (bản LlamaParse hay để Điều dạng chữ đậm, không phải heading), các test Điều 33/Điều 12 hiện có.
- Người nhận: `agent-claude` (S-03).

### S-03 — Ghi Khoản/Điểm vào metadata lúc chunking và chuyển qua retrieval

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-04`.
  - Chunker tính `legal_*` cho từng chunk bằng `extract_legal_units`, mang trạng thái Khoản đang mở qua các child liên tiếp của cùng một section (kể cả khi section bị chia thành nhiều parent), để child bắt đầu bằng `b)` nhận đúng số Khoản. Áp dụng cho cả `split_parent_child` và `split_text` (đường không dùng parent-child).
  - `pipeline._chunk_records` (`pipeline.py:786-845`) ghi `legal_article`, `legal_clauses`, `legal_points` vào metadata.
  - `_format_chunk_context` (`pgvector_store.py:187-212`) và snapshot BM25 (`bm25.py:110-130`) chép các khóa này vào context nếu có trong metadata (không có thì không đặt khóa, để citation biết là chunk cũ).
  - `collapse_parent_results` (`parent_child.py`) lấy `legal_*` theo child bằng chứng, cập nhật cùng lúc với `evidence_text` khi child tốt hơn thay thế.
  - `citations._citation_metadata` dùng `legal_*` của context khi có khóa `legal_clauses`; ngược lại gọi `extract_legal_units` trên `heading`/`section_path`/`evidence_text` (không có kế thừa Khoản).
- Phạm vi file được sửa: `backend/app/ingestion/chunker.py` (thêm trường có giá trị mặc định vào `Chunk`, `ParentChildChunk`; tính `legal_*`; không đổi ranh giới chia), `backend/app/ingestion/pipeline.py` (chỉ `_chunk_records`), `backend/app/vectordb/pgvector_store.py` (chỉ `_format_chunk_context`), `backend/app/retrieval/bm25.py` (chỉ snapshot chunk), `backend/app/retrieval/parent_child.py`, `backend/app/generation/citations.py`, `backend/tests/test_chunker.py`, `backend/tests/test_parent_child*.py` hoặc test hiện có của `collapse_parent_results`, `backend/tests/test_citations.py`, test pipeline/ingest có kiểm metadata.
- Phụ thuộc: S-02.
- Đầu ra/bàn giao: chunk mới mang `legal_*`; test chứng minh văn bản/ranh giới chunk không đổi (so `text` của mọi chunk trên fixture chunker hiện có trước/sau), child giữa Khoản nhận Khoản kế thừa, metadata đi hết đường vector → BM25 → parent-child → citation.
- Người nhận: `agent-claude` (S-04).

### S-04 — Backfill metadata cho index đang có

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: `python -m scripts.refresh_legal_metadata` (dry-run mặc định, `--apply` để ghi) chia lại `parsed_text` đã lưu bằng đúng `_chunk_records`, chỉ khi tập id chunk và `text` từng chunk khớp DB thì gộp `legal_*` vào `chunk_metadata` (giữ mọi khóa khác); tài liệu lệch thì bỏ qua và báo cáo. Không ghi `text`, `search_text`, vector. Phục vụ `AC-04`, là điều kiện cho S-05b.
- Phạm vi file được sửa: `backend/scripts/refresh_legal_metadata.py` (mới, theo mẫu `refresh_search_text.py`; tách hàm dùng chung nếu cần thì ghi lý do vào `implementation.md`), `backend/tests/test_refresh_legal_metadata.py` (mới).
- Phụ thuộc: S-03.
- Đầu ra/bàn giao: script + test (dry-run không ghi; `--apply` chỉ đổi khóa `legal_*`; tài liệu lệch bị bỏ qua); số tài liệu/chunk đã cập nhật trên index local ghi vào `implementation.md`. Ghi chú vận hành: backend đang chạy phải khởi động lại để BM25 dựng lại snapshot.
- Người nhận: `agent-claude` (S-05b).

### S-05 — So sánh locator trên golden set

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-05`.
  - **S-05a (làm ngay sau khi tạo nhánh, trước S-02):** script `python -m scripts.dump_citation_locators --dataset <json> --out <json>` chạy pipeline giống `eval_retrieval --mode full` (tái dùng `build_retrieval_fn`, cache embedding, `snapshot_*`, `git_info` của `scripts/eval_retrieval.py` bằng import), ghi cho mỗi câu và mỗi context top-k: `chunk_id`, `heading`, `section_path`, `article`, `clauses`, `points`, `locator`, cờ có `legal_*` trong metadata. Chạy trên commit nền cho `ptit_rag_300.json` và `ptit_ragas_100.json`, lưu `documents/rag-eval/rag-22/locators_before_*.json`. Commit script + bản "trước".
  - **S-05b (sau S-04 đã `--apply` trên index local):** chạy lại → `locators_after_*.json`; script `--diff before after` ghép theo (`id` câu, `chunk_id`) và phân loại: `unchanged`, `removed_non_article` (bỏ Khoản/Điểm ở chunk không có Điều), `added_inherited_clause`, `other`. Kiểm điều kiện AC-05 (mọi citation có Điều ở bản trước giữ `article`, không mất Khoản). Nếu thứ tự context giữa hai lần chạy khác nhau (không mong đợi vì retrieval không đổi) thì ghi rõ, chỉ so các cặp ghép được.
- Phạm vi file được sửa: `backend/scripts/dump_citation_locators.py` (mới), `backend/tests/test_dump_citation_locators.py` (mới, test phần diff/phân loại với dữ liệu giả), `documents/rag-eval/rag-22/*`.
- Phụ thuộc: S-05a không phụ thuộc gì; S-05b phụ thuộc S-04.
- Đầu ra/bàn giao: hai bản JSON + bảng phân loại; mọi trường hợp `other` liệt kê kèm giải thích; nếu `other` > 0 mà không giải thích được thì dừng, báo người dùng.
- Người nhận: `agent-claude` (S-07).

### S-06 — Nhãn khối nguồn ở frontend

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: khối nguồn dưới câu trả lời (`ChatView.jsx:656-682`) ghi "Nguồn trích dẫn" khi `content` có ít nhất một `[n]` khớp `citation_id` trong `sources`, ngược lại ghi "Nguồn liên quan". Câu từ chối có `sources` rỗng nên khối không hiện (hành vi sẵn có của điều kiện `sources?.length > 0`). Phục vụ `AC-06`.
- Phạm vi file được sửa: `frontend/src/ChatView.jsx` (chỉ đoạn khối nguồn; hàm kiểm `[n]` có thể đặt trong `frontend/src/lib/markdown.js` nếu dùng lại regex `^\[(\d{1,3})\]`), test `ChatView` hoặc `markdown` tương ứng.
- Phụ thuộc: hợp đồng `sources` của S-01 (làm song song được).
- Đầu ra/bàn giao: test cho cả hai nhãn và trường hợp `[n]` không có trong `sources`.
- Người nhận: `agent-claude` (verifier).

### S-07 — Báo cáo và bàn giao

- Agent: `agent-claude`
- Trạng thái: `done`
- Mục tiêu: mục "RAG-22" trong `documents/rag-eval/README.md` (bảng phân loại thay đổi locator, số chunk có Điều/có Khoản trước và sau, giới hạn, bước vận hành: chạy `refresh_legal_metadata --apply` rồi khởi động lại backend); chạy toàn bộ kiểm tra; chuyển task sang `in_review`. Phục vụ `AC-05`, `AC-06`.
- Phạm vi file được sửa: `documents/rag-eval/README.md`, `documents/rag-eval/rag-22/*`, năm file task.
- Phụ thuộc: S-01…S-06.
- Đầu ra/bàn giao: báo cáo cuối; bàn giao verifier/reviewer.
- Người nhận: verifier, reviewer.

## Hợp đồng dùng chung

- **`refusal.py`** (S-01 cung cấp; `llm.py`, `rag_chain.py`, `routes.py`, `prompts.py` dùng):
  - `NO_CONTEXT_ANSWER = "Chưa tìm thấy thông tin này trong tài liệu."` (giữ nguyên chuỗi người dùng đang thấy khi gate RAG-18 không đạt).
  - `is_refusal(answer: str) -> bool`: chuẩn hóa (bỏ `[n]`, `*_\``, gộp khoảng trắng, `casefold`, bỏ dấu câu cuối) rồi coi là từ chối khi **câu đầu tiên** chứa lõi của `NO_CONTEXT_ANSWER` hoặc `OUT_OF_SCOPE_ANSWER` (lõi = chuỗi đã chuẩn hóa, có thể bỏ cụm đuôi như "trong tài liệu"; S-01 chốt danh sách lõi bằng test) **và** câu trả lời gốc không còn `[n]` hợp lệ nào nằm ngoài câu đầu. Câu có phần nội dung kèm `[n]` hợp lệ sau cụm từ chối là trả lời một phần, không phải từ chối.
  - Hàm này không cần `contexts` cho phần so khớp; phần "còn `[n]` hợp lệ" do `_normalize_answer_citations` xác định trước khi gọi (S-01 chốt chữ ký, ví dụ `is_refusal(answer, valid_ids=frozenset())`).
- **`_normalize_answer_citations(answer, contexts) -> str`** (S-01): xóa `[n]` không hợp lệ; nếu `is_refusal` thì xóa mọi `[n]`; không bao giờ thêm `[n]`. Giữ câu chữ của LLM (không thay bằng câu chuẩn).
- **Quy tắc `sources`** (S-01): `sources = [] if is_refusal(answer) else public_citations(contexts)`, tính sau khi có câu trả lời cuối. Luồng stream tính lại trước event `done`; khi stream lỗi giữa chừng (`stream_error`) giữ nguyên hành vi hiện tại.
- **`extract_legal_units`** (S-02 cung cấp; chunker S-03, `citations.py` dùng):
  - `extract_legal_units(heading: str, section_path: str, text: str, open_clause: str | None = None) -> LegalUnits`, `LegalUnits` (dataclass frozen) gồm `article: str | None`, `clauses: list[str]`, `points: list[str]`, `last_clause: str | None` (Khoản cuối cùng thấy trong `text`, để chunker truyền sang chunk kế tiếp).
  - `article`: như `_extract_article` hiện tại (heading → các phần `section_path` → 8 dòng đầu text), cùng regex `Điều\s+\d+[a-zA-Z]?`.
  - Không có `article` → `clauses == []`, `points == []`, `last_clause is None`, bất kể text có danh sách đánh số.
  - Có `article`: Khoản = dòng bắt đầu bằng `\d{1,2}[.)]` + khoảng trắng (cho phép `-`/`*`/`**` đầu dòng như regex hiện tại), không nằm trong bảng markdown/HTML; Điểm = dòng bắt đầu bằng `[a-zđ][.)]`. Nếu dòng đánh dấu đầu tiên là Điểm (hoặc text không có Khoản) và `open_clause` có giá trị thì `clauses` bắt đầu bằng `open_clause`. Giới hạn 12 phần tử như hiện tại.
  - S-02 đo trên index local số chunk có `1)`/`a.` trong Điều; nếu dạng `\d)` chỉ gặp ở danh sách không phải Khoản thì được bỏ, ghi quyết định vào `implementation.md`.
- **Khóa metadata chunk và context** (S-03 cung cấp; S-04, S-05, `citations.py` dùng): `legal_article: str | None`, `legal_clauses: list[str]`, `legal_points: list[str]`. Có khóa `legal_clauses` (kể cả rỗng) = metadata có thẩm quyền; không có khóa = chunk cũ, dùng đường dự phòng. Không thêm khóa vào schema `Source` API; `public_citations` vẫn trả `article`, `clauses`, `points`, `locator` như hiện tại.
- File mã nguồn dùng chung và người sửa: `citations.py` — S-02 rồi S-03 (tuần tự); `routes.py`, `llm.py`, `prompts.py`, `rag_chain.py` — chỉ S-01; `chunker.py`, `pipeline.py`, `pgvector_store.py`, `bm25.py`, `parent_child.py` — chỉ S-03; `scripts/eval_retrieval.py` — không ai sửa trừ khi S-05a ghi lý do và chạy lại `test_eval_retrieval.py`.
- Lượt ghi năm file task: coordinator `agent-claude` ghi tuần tự; agent khác (nếu có) gửi nội dung qua mục trao đổi trong `implementation.md`.

## Phân công kiểm chứng và review

- Verifier: `agent-claude`; phạm vi: `AC-01`…`AC-06`; chạy `python -m pytest` toàn bộ trong `backend`, test frontend (`npm test` trong `frontend`, ít nhất `ChatView` và `markdown`), `refresh_legal_metadata` dry-run/`--apply` trên index local, `dump_citation_locators --diff`. Kiểm tay luồng `/chat/stream` với một câu hỏi có trong tài liệu, một câu trả lời một phần và một câu không có đáp án nếu có LLM được cấu hình (ghi `not_run` nếu không có).
- Reviewer: ưu tiên reviewer độc lập do người dùng chỉ định; nếu không có, `agent-claude` ghi `self_review`. Phạm vi: diff toàn nhánh, báo cáo `documents/rag-eval/rag-22/`, kiểm ngẫu nhiên ≥ 10 thay đổi locator trong báo cáo đối chiếu với tài liệu gốc.
- Hình thức review: `independent` nếu có reviewer khác, ngược lại `self_review` (ghi rõ trong `review.md`). Lượt này: `self_review` (người dùng chưa chỉ định reviewer khác).
- Người xử lý nhận xét: `agent-claude` cho mọi `S-*`; reviewer xác nhận sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. Kiểm `git diff HEAD --name-only` rỗng trên `dev`, `git pull origin dev`, tạo nhánh `feat/rag22-citation-accuracy`; ghi commit nền vào `implementation.md`.
2. S-05a: viết script dump, chạy trên commit nền với index local (chưa backfill), commit script + `locators_before_*.json`.
3. S-01 (một commit) — độc lập với 4–6.
4. S-02 → S-03 (mỗi nhiệm vụ một commit); chạy `pytest tests/test_legal_units.py tests/test_citations.py tests/test_chunker.py` và test retrieval liên quan sau mỗi bước.
5. S-04: commit script; chạy dry-run rồi `--apply` trên index local; ghi số liệu.
6. S-05b: chụp `locators_after_*.json`, chạy diff, kiểm điều kiện AC-05.
7. S-06 (một commit) — làm được bất kỳ lúc nào sau khi hợp đồng `sources` của S-01 chốt.
8. S-07: báo cáo, toàn bộ pytest backend + test frontend; chuyển task `in_review`.
9. Verifier điền `verification.md` (V-01…V-06 tương ứng AC); reviewer ghi `review.md`; agent sửa `R-*` bắt buộc, verifier chạy lại phần bị ảnh hưởng.
10. Coordinator đối chiếu AC, review `approved` trên bản mới nhất, mở PR vào `dev` khi người dùng yêu cầu, cập nhật thẻ Notion RAG-22, rồi chuyển task `done`.

## Rủi ro và điều chỉnh kế hoạch

- **Nhận diện từ chối quá rộng**: câu trả lời một phần thường mở đầu "Tài liệu chưa đề cập ..." rồi mới trả lời. Xử lý: chỉ coi là từ chối khi không còn `[n]` hợp lệ ngoài câu đầu; test riêng cho câu trả lời một phần có và không có `[n]`. Câu trả lời một phần *không* có `[n]` nào và mở đầu bằng cụm từ chối sẽ bị coi là từ chối (mất `sources`) — chấp nhận, ghi trong báo cáo.
- **Nhiều câu trả lời không còn `[n]`**: bỏ tự gắn làm lộ các câu LLM không trích dẫn (trước đây bị che bằng `[1]`). Không đo được nếu không gọi LLM; nếu verifier có LLM thì đếm tỉ lệ trên một mẫu nhỏ, ngược lại ghi là giới hạn. Không sửa prompt ngoài dòng câu từ chối trong task này.
- **Điều không ở heading**: bản LlamaParse có thể để "Điều N" dạng chữ đậm trong thân, không thành heading, khi đó section không biết mình thuộc Điều. Đường `8 dòng đầu text` giữ nguyên để không mất Điều; báo cáo S-05 đếm số chunk có Điều trước/sau để phát hiện mất mát.
- **Danh sách đánh số bên trong một Điều không phải Khoản** (ví dụ phụ lục, danh mục trong Điều): vẫn bị coi là Khoản theo định nghĩa. Ghi là giới hạn; nhóm `other` của S-05 sẽ cho thấy nếu có trường hợp đáng kể.
- **Index chưa backfill**: chunk cũ dùng đường dự phòng (không kế thừa Khoản) cho tới khi chạy S-04. Môi trường khác (server) cần chạy `refresh_legal_metadata --apply`; ghi trong README và mô tả PR.
- **Đổi số citation**: locator là một phần của `_citation_key`, nên bỏ Khoản sai hoặc thêm Khoản kế thừa có thể gộp/tách số citation trong prompt. Đây là thay đổi mong muốn; S-05 báo cáo theo chunk nên không phụ thuộc số citation.
- **Snapshot "trước" phải chụp trước backfill và trước S-02**: nếu lỡ, chụp lại bằng cách checkout commit nền trong worktree riêng với cùng DB chưa backfill; nếu DB đã backfill thì khóa `legal_*` không ảnh hưởng code ở commit nền (code cũ không đọc khóa này), nên vẫn chụp lại được.
