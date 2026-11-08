# Task: RAG-22 — Citation: bỏ tự gắn [n], nhận diện câu từ chối, Khoản/Điểm theo cấu trúc Điều

- ID: `2026-11-08-rag22-citation-accuracy`
- Trạng thái: `in_review`
- Coordinator: `agent-claude`
- Người yêu cầu: `user` (thẻ Notion [RAG-22](https://app.notion.com/p/40f334d296eb818ea3d0e1f77d007a68), ưu tiên P1, nguồn: rà soát toàn hệ thống 2026-11-05)
- Tạo lúc: `2026-11-08T10:32:28+07:00`
- Cập nhật lúc: `2026-11-08T11:15:39+07:00`

## Yêu cầu và kết quả mong muốn

**Hiện trạng.** (Số dòng trên thẻ Notion đã cũ; số dưới đây theo `dev` tại `e6981f1`.)

1. **Tự gắn citation giả.** `_normalize_answer_citations` (`backend/app/generation/llm.py:132-148`) xóa số `[n]` không hợp lệ, rồi nếu câu trả lời không còn `[n]` nào thì nối thêm `[min(valid_ids)]`. Câu trả lời một phần ("tài liệu chưa đề cập ...") hoặc câu LLM cố ý không trích dẫn vì vậy vẫn mang một trích dẫn trỏ vào nguồn số 1. Hàm này chạy ở cả `/chat` (qua `answer_with_llm`) và `/chat/stream` (`backend/app/api/routes.py:1497-1503`, sau khi stream xong, trước event `done`).
2. **Nhận diện câu từ chối bằng so khớp nguyên văn.** Chỉ khi câu trả lời đúng y hệt `"Chưa tìm thấy thông tin này trong tài liệu."` hoặc `OUT_OF_SCOPE_ANSWER` thì mới không bị gắn citation (`llm.py:142`). Thêm một chữ ("Xin lỗi, chưa tìm thấy ...", "... trong tài liệu được cung cấp.") là bị gắn `[1]`. Thêm vào đó:
   - Câu từ chối "không có thông tin" bị lặp literal ở 3 nơi (`rag_chain.py:20` `NO_CONTEXT_ANSWER`, `routes.py:1451`, `llm.py:142`).
   - `SYSTEM_PROMPT` yêu cầu "chỉ trả lời chính xác câu từ chối đã quy định" nhưng `build_context_prompt` (`backend/app/generation/prompts.py`) chỉ đưa câu từ chối ngoài phạm vi, không đưa câu "không có thông tin", nên LLM tự diễn đạt và gần như không bao giờ khớp nguyên văn.
   - Khi LLM từ chối, `sources` vẫn trả đủ danh sách context (`routes.py:1437`, `rag_chain.py:110`), nên giao diện vẫn hiện khối "Nguồn trích dẫn" dưới một câu từ chối.
3. **Khoản/Điểm đoán bằng regex trên toàn bộ text.** `_citation_metadata` (`backend/app/generation/citations.py:33-51`) lấy "Khoản" từ mọi dòng bắt đầu bằng `1.`/`2)` trong `evidence_text`, và lấy "Điểm" từ `a)`/`b.` nếu có Điều *hoặc* có Khoản (`_extract_numbered_units`, `citations.py:71-78`). Hệ quả:
   - Danh sách đánh số trong mục không phải văn bản pháp quy (ví dụ các bước thủ tục trong Sổ tay) hiện thành "Khoản 1, 2, 3"; danh sách `a)`/`b)` đi kèm thành "Điểm a, b".
   - Ngược lại, child bắt đầu giữa một Khoản (chỉ chứa `b)`, `c)` của Khoản 2) mất số Khoản vì regex không biết ngữ cảnh phía trước.
   - Locator tham gia khóa gộp citation (`_citation_key`), nên Khoản sai còn làm tách/gộp nhầm số citation.

Chunker (`backend/app/ingestion/chunker.py`, RAG-06) đã chia parent theo Điều/mục và child theo Khoản/đoạn, nhưng không ghi số Khoản/Điểm vào metadata chunk (`pipeline.py:810-824`).

**Kết quả cần có.**

- Không bao giờ tự chèn `[n]` vào câu trả lời. Câu trả lời không có `[n]` vẫn trả `sources` (nguồn liên quan), giao diện ghi rõ đó là nguồn liên quan chứ không phải trích dẫn.
- Câu từ chối được nhận diện ổn định (một hằng số, prompt nêu rõ câu, so khớp chịu được biến thể nhỏ); câu từ chối không có `[n]` và không kèm `sources`.
- Khoản/Điểm chỉ xuất hiện khi chunk thuộc một Điều; được tính lúc chunking từ cấu trúc section và lưu vào metadata chunk; citation ưu tiên metadata, có đường dự phòng cho chunk cũ.
- Locator của các Điều/Khoản thật trên golden set không bị mất hay đổi sai (có báo cáo trước/sau).

## Phạm vi

- Bao gồm:
  - Chuẩn hóa citation và nhận diện câu từ chối: `backend/app/generation/llm.py`, module mới `backend/app/generation/refusal.py`, `prompts.py`, `rag_chain.py`, `backend/app/api/routes.py` (chỉ đoạn câu từ chối/`sources` của luồng chat).
  - Trích Điều/Khoản/Điểm theo cấu trúc: hàm thuần dùng chung, ghi metadata lúc chunking (`backend/app/ingestion/chunker.py`, `pipeline.py`), chuyển metadata qua retrieval (`backend/app/vectordb/pgvector_store.py`, `backend/app/retrieval/bm25.py`, `parent_child.py`), dùng trong `citations.py`.
  - Script backfill metadata cho index đang có mà không chunk lại/embed lại (theo mẫu `backend/scripts/refresh_search_text.py`).
  - Script và báo cáo so sánh locator trước/sau trên golden set (`documents/rag-eval/rag-22/`, mục mới trong `documents/rag-eval/README.md`).
  - Nhãn khối nguồn trong `frontend/src/ChatView.jsx` ("Nguồn trích dẫn" ↔ "Nguồn liên quan").
- Ngoài phạm vi:
  - Gate confidence (RAG-18, đã merge), scope guardrail (RAG-19), viết lại prompt sinh câu trả lời ngoài các dòng về câu từ chối.
  - Thay đổi cách chia chunk (ranh giới parent/child), embedding, `search_text`, trọng số retrieval/reranker.
  - Kiểm tra từng nhận định có đúng là được `[n]` hỗ trợ (faithfulness của citation) — chỉ xử lý số citation và locator.
  - Đổi schema `Source` của API (`backend/app/api/schemas.py:11-19`) hay cách render chip `[n]` trong `frontend/src/lib/markdown.js`.
- Ràng buộc:
  - Không cần migration: metadata chunk là cột JSON (`models.py:166`). Chunk cũ không có khóa mới vẫn phải cho citation hợp lý (đường dự phòng theo quy tắc Điều mới, không quay về regex cũ).
  - Backfill chỉ ghi các khóa metadata mới, chỉ khi tập id và `text` chunk khớp DB; không đổi `text`, `search_text`, vector.
  - Luồng stream: người dùng thấy delta thô trong lúc stream, event `done` thay bằng câu đã chuẩn hóa (`ChatView.jsx:396-410`). Không đổi cơ chế này; không dùng marker đặc biệt mà người dùng có thể thấy trong lúc stream.
  - Giữ tên `_normalize_answer_citations` import trong `routes.py` (test `test_chat_error_privacy.py:167` monkeypatch tên này) hoặc cập nhật test tương ứng.
  - Nhánh `feat/rag22-citation-accuracy` tách từ `dev` đã cập nhật; commit message tiếng Anh. Lúc tạo task, các file `M` trên `dev` chỉ là stat/CRLF (`git diff HEAD --stat` rỗng); kiểm tra lại trước khi tạo nhánh, có thay đổi nội dung thật thì hỏi người dùng.

## Tiêu chí nghiệm thu

- [x] AC-01: Không tự gắn citation. Unit test: câu trả lời không có `[n]` (gồm câu trả lời một phần "tài liệu chưa đề cập ...") được trả nguyên, không có `[n]` nào được thêm; `[n]` không hợp lệ vẫn bị xóa; `[n]` hợp lệ giữ nguyên; `sources` vẫn được trả với câu trả lời không phải từ chối. Kiểm ở cả `answer_with_llm`/`/chat` và `/chat/stream` (event `done` và metadata đã lưu).
- [x] AC-02: Nhận diện câu từ chối. Một hằng số cho câu "không có thông tin", dùng ở `llm.py`, `rag_chain.py`, `routes.py`, và được nêu nguyên văn trong `build_context_prompt`. Unit test cho: câu đúng nguyên văn; có thêm chữ trước/sau ("Xin lỗi, ...", "... được cung cấp."); khác hoa/thường, dấu câu, có `**`; có `[n]` dính kèm; câu từ chối ngoài phạm vi có biến thể. Tất cả trả về không có `[n]` và `sources` rỗng. Câu bắt đầu bằng cụm từ chối nhưng sau đó có nội dung kèm `[n]` hợp lệ được coi là trả lời một phần (giữ citation và `sources`).
- [x] AC-03: Khoản/Điểm chỉ trong Điều. Unit test: danh sách `1.`/`2)` và `a)`/`b.` trong mục không phải Điều (heading, `section_path` và các dòng đầu không có "Điều N") cho `clauses == []`, `points == []`, `locator` = heading; danh sách trong bảng cũng không thành Khoản. Các test hiện có trong `backend/tests/test_citations.py` (Điều 33, Điều 12) vẫn xanh.
- [x] AC-04: Metadata lúc chunking. Child chunk mới có `legal_article`, `legal_clauses`, `legal_points` trong metadata; child bắt đầu giữa Khoản nhận số Khoản đang mở; mục không phải Điều có `legal_clauses == []`. Metadata đi qua vector, BM25 và gộp parent-child (lấy theo child bằng chứng). `public_citations` dùng metadata khi có, dùng quy tắc dự phòng của AC-03 khi không có. Script backfill có dry-run và `--apply`, bỏ qua tài liệu lệch `text`. Có unit test cho từng phần.
- [x] AC-05: Locator golden set không đổi với Điều/Khoản thật. Báo cáo trong `documents/rag-eval/rag-22/` so locator của context top-k (pipeline `full`, embedding cache) cho `ptit_rag_300.json` và `ptit_ragas_100.json` trước (commit nền) và sau (index đã backfill): mọi citation có Điều ở bản trước giữ nguyên `article` và không mất Khoản nào; mọi thay đổi được liệt kê và phân loại (bỏ Khoản/Điểm ngoài Điều, thêm Khoản kế thừa, khác). Nhóm "khác" bằng 0 hoặc từng trường hợp có giải thích được người dùng chấp nhận. Ghi fingerprint kho, dataset sha256, git commit.
- [x] AC-06: Không vỡ tương thích. Schema `Source` không đổi; `python -m pytest` toàn bộ `backend` xanh; test frontend liên quan (`ChatView`, `markdown`) xanh; khối nguồn hiện "Nguồn liên quan" khi câu trả lời không có chip `[n]` hợp lệ và "Nguồn trích dẫn" khi có.

## Tài liệu và phụ thuộc

- Notion: [RAG-22](https://app.notion.com/p/40f334d296eb818ea3d0e1f77d007a68). Liên quan: RAG-18 (gate, đã merge PR #56 — câu từ chối khi gate không đạt), RAG-06 (chunking Điều/Khoản), RAG-25 (bộ đánh giá).
- Mã: `backend/app/generation/{citations,llm,prompts,rag_chain}.py`, `backend/app/api/routes.py:1436-1451, 1497-1503`, `backend/app/ingestion/{chunker,pipeline}.py`, `backend/app/vectordb/pgvector_store.py:187-212`, `backend/app/retrieval/{bm25,parent_child}.py`, `backend/scripts/refresh_search_text.py` (mẫu backfill), `backend/scripts/eval_retrieval.py` (pipeline `full`, cache embedding).
- Frontend: `frontend/src/ChatView.jsx:656-682`, `frontend/src/lib/markdown.js:120-152`.
- Test hiện có: `backend/tests/test_citations.py`, `test_prompts.py` (`test_answer_citations_are_limited_to_provided_sources` đang khẳng định hành vi tự gắn `[1]` — phải đổi), `test_rag_chain.py`, `test_chat_error_privacy.py`, `test_chunker.py`.
- Đánh giá: `documents/rag-eval/README.md`, `backend/tests/fixtures/ptit_rag_300.json`, `ptit_ragas_100.json`. Index local là bản LlamaParse của D26, khác bản converted mà test lint đọc (xem nhật ký RAG-18).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai S-01…S-07 trên nhánh `feat/rag22-citation-accuracy` (`4ce8bad`…`c4bcd78` + commit báo cáo/task); index local đã backfill `legal_*`. Verification V-01…V-06 `passed`; review `self_review` `approved`, R-01 (high) đã sửa, R-02/R-03 (low) hoãn.
- Blocker: không có.
- Bước tiếp theo: người dùng quyết định có review độc lập không; push nhánh, mở PR vào `dev`; sau merge chạy `python -m scripts.refresh_legal_metadata --apply` trên môi trường khác và khởi động lại backend; cập nhật thẻ Notion RAG-22; coordinator chuyển `done`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-08T10:32:28+07:00 — agent-claude: tạo task từ thẻ Notion RAG-22, trạng thái `ready`. Bổ sung so với thẻ:
  1. Câu từ chối không kèm `sources` (thẻ chỉ nói không gắn `[n]`), vì khối "Nguồn trích dẫn" dưới câu từ chối cũng là trích dẫn giả.
  2. Nhận diện từ chối bằng hằng số + so khớp sau chuẩn hóa, không dùng marker riêng: marker sẽ hiện ra trong lúc stream trước khi `done` thay câu.
  3. Đưa câu "không có thông tin" vào prompt; đây là nguyên nhân LLM không bao giờ trả đúng nguyên văn.
  4. Chọn ghi Khoản/Điểm vào metadata lúc chunking như thẻ đề xuất, kèm backfill không embed lại và đường dự phòng cho chunk cũ.
  5. Định nghĩa "locator golden set không đổi" là không mất Điều/Khoản thật; cho phép thay đổi đã phân loại (bỏ Khoản ngoài Điều, thêm Khoản kế thừa), vì golden set không có nhãn locator.
  6. Thêm đổi nhãn khối nguồn ở frontend để người dùng phân biệt trích dẫn với nguồn liên quan.
- 2026-11-08T11:15:39+07:00 — agent-claude: chuyển `in_review`. Điều chỉnh trong lúc làm (không đổi tiêu chí):
  1. Bỏ dạng `N)` khỏi Khoản (đo: 0 lần trong Điều trên index local), theo điều khoản đo-rồi-quyết trong hợp đồng `extract_legal_units`.
  2. Mở rộng quy tắc kế thừa Khoản: nhận Khoản giữa dòng khi đúng số kế tiếp, kế thừa khi có nội dung trước dấu Khoản đầu tiên, bỏ kế thừa khi đánh số bắt đầu lại — vì bản LlamaParse gộp nhiều Khoản vào một đoạn (R-01). Báo cáo AC-05 thêm nhóm `added_inline_clause` (thuộc loại "thêm Khoản", không mất Khoản nào).
  3. Nhãn khối nguồn đặt trong `frontend/src/lib/citations.js` thay vì `lib/markdown.js` để không kéo module markdown (lazy) vào bundle ban đầu.
  4. Tách `rechunk_matching_db` trong `refresh_search_text.py` để hai script backfill dùng chung điều kiện khớp DB.
- 2026-11-08T11:57:06+07:00 — agent-claude (coordinator): quyết định cho nhận xét `low` của review lượt 2: R-04, R-05 hoãn sang task sau (cùng nhóm với R-02/R-03; không vi phạm AC); R-06 — đã điền `4977e1f` vào `implementation.md`, giữ hai bản dump đầy đủ trong repo vì `--diff` cần chúng để tái lập báo cáo trên cùng index. Người dùng yêu cầu push và mở PR vào `dev`.
