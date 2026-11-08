# Review: 2026-11-08-rag22-citation-accuracy

- Reviewer: `agent-claude`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập — người dùng chưa chỉ định reviewer khác).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/rag22-citation-accuracy`, diff `e6981f1..4977e1f` (lượt 2; mã không đổi so với `c4bcd78`, `4977e1f` chỉ thêm báo cáo và năm file task) và báo cáo `documents/rag-eval/rag-22/*` chụp ở `c4bcd78`.
- Cập nhật lúc: `2026-11-08T11:46:50+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-06; S-01…S-07.
- File/thay đổi cần đọc: `backend/app/generation/{refusal,llm,prompts,rag_chain,citations}.py`, `backend/app/api/routes.py` (đoạn `_iter_chat_stream_events`), `backend/app/ingestion/{legal_units,chunker,pipeline}.py`, `backend/app/vectordb/pgvector_store.py`, `backend/app/retrieval/{bm25,parent_child}.py`, `backend/scripts/{dump_citation_locators,refresh_legal_metadata,refresh_search_text}.py`, `frontend/src/{ChatView.jsx,lib/citations.js}` và test tương ứng.
- Bằng chứng kiểm chứng: `verification.md` V-01…V-06 (`passed`); kiểm tay `/chat/stream` qua HTTP với LLM thật `not_run`.
- Điểm cần đánh giá: không còn đường nào thêm `[n]`; nhận diện từ chối không nuốt câu trả lời một phần có trích dẫn; `sources` của luồng stream nhất quán giữa event `done` và metadata lưu; văn bản/ranh giới chunk không đổi; metadata đi đúng theo child bằng chứng; backfill chỉ ghi 3 khóa; kiểm ngẫu nhiên ≥ 10 thay đổi locator.

## Nhận xét

Đã đọc toàn bộ diff trên. Kiểm ngẫu nhiên 27 thay đổi locator đối chiếu `parsed_text` (15 + 12, xem V-05). Lượt đầu tìm ra lỗi kế thừa Khoản (R-01), đã sửa trước khi chụp bản cuối. Không còn nhận xét bắt buộc.

### R-01 — Khoản kế thừa sai khi bản parse gộp nhiều Khoản vào một đoạn

- Vị trí: `backend/app/ingestion/legal_units.py` (`extract_legal_units`), bản `46bb3d4`.
- Liên quan: AC-04, AC-05 / S-02, S-03.
- Mức độ: `high`.
- Bắt buộc sửa: có.
- Trạng thái: `resolved`.
- Vấn đề và tác động: chỉ nhận Khoản ở đầu dòng; Sổ tay D26 (LlamaParse) có 170 dấu "N." giữa dòng trong các chunk thuộc Điều, nên Khoản đang mở bị giữ ở số cũ và chunk sau nhận nhầm (ví dụ `parent-514::child-0` "… Hội đồng. 5. Hai tuần …" thành "Khoản 1"). Script diff vẫn xếp vào `added_inherited_clause` nên chỉ kiểm tay mới thấy.
- Đề nghị xử lý: theo dõi số Khoản giữa dòng; khi không chắc thì bỏ Khoản đang mở thay vì đoán.
- Người xử lý: `agent-claude`.
- Phản hồi/cách sửa: `c4bcd78` — nhận "N." giữa dòng (sau dấu kết câu, trước chữ hoa) khi đúng số kế tiếp; số khác thì Khoản đang mở = không rõ; đánh số bắt đầu lại (dấu Khoản đầu ≤ Khoản kế thừa) thì bỏ Khoản kế thừa; thêm nhóm `added_inline_clause` trong script diff.
- Bằng chứng sau sửa: 6 test mới trong `test_legal_units.py`; backfill lại (118 rồi 7 chunk đổi); diff cuối `other` = 0, 0 vi phạm; kiểm tay lượt 2: 12/12 đúng.
- Xác nhận của reviewer: đã đọc lại diff `c4bcd78` và kết quả chụp lại — `resolved`.

### R-02 — Câu trả lời một phần nằm gọn trong một câu có cụm từ chối bị coi là từ chối

- Vị trí: `backend/app/generation/refusal.py` (`is_refusal`).
- Liên quan: AC-02 / S-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: "Mình không tìm thấy thông tin này về A, nhưng B là … [1]." (một câu) bị coi là từ chối, mất `[1]` và `sources`. Hợp đồng chỉ xét `[n]` sau câu đầu; LLM thật trong mẫu 10+2 câu không tạo dạng này.
- Đề nghị xử lý: theo dõi khi có log câu trả lời thật; nếu gặp, chỉ coi là từ chối khi phần còn lại của câu đầu ngắn.
- Người xử lý: `agent-claude`.
- Nếu deferred: không bắt buộc; ghi là giới hạn trong bàn giao. Coordinator `agent-claude` chấp nhận hoãn.
- Ghi chú lượt 2: đồng ý hoãn. Khi xử lý, có thể sửa rẻ bằng điều kiện bổ sung: câu đầu có `[n]` hợp lệ thì chỉ coi là từ chối khi phần câu đầu ngoài lõi ngắn (ví dụ ≤ 40 ký tự sau chuẩn hóa), để "Chưa tìm thấy thông tin này trong tài liệu [1]." vẫn là từ chối mà câu trả lời một phần gộp một câu thì không.

### R-03 — Danh sách "1." trong một Điều nhưng không phải Khoản vẫn thành Khoản

- Vị trí: `backend/app/ingestion/legal_units.py`.
- Liên quan: AC-03 / S-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: giới hạn đã nêu trong plan; hành vi giống trước RAG-22. Ghi trong README mục RAG-22.
- Nếu deferred: theo dõi qua báo cáo locator khi thêm tài liệu mới.

### R-04 — Lõi câu từ chối chỉ bắt các biến thể của câu chuẩn

- Vị trí: `backend/app/generation/refusal.py` (`REFUSAL_CORES`).
- Liên quan: AC-02 / S-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: chạy thử `is_refusal` lượt 2: "Tài liệu không có thông tin về học bổng X." và "Không có thông tin về vấn đề này trong tài liệu được cung cấp." trả `False`. Với các diễn đạt này câu trả lời không còn bị gắn `[n]` (đã hết lỗi chính của thẻ), nhưng `sources` vẫn được trả và giao diện hiện "Nguồn liên quan" dưới một câu từ chối. Mức ảnh hưởng thấp vì prompt nay nêu nguyên văn câu từ chối; mẫu LLM thật trong V-02 trả đúng câu chuẩn.
- Đề nghị xử lý: không sửa trong task này; khi có log câu trả lời thật, cân nhắc thêm lõi "không có thông tin" nhưng chỉ khi toàn bộ câu trả lời không có `[n]` hợp lệ (tránh nuốt câu trả lời một phần).
- Người xử lý: `agent-claude`.

### R-05 — Điểm giữa dòng không được nhận, trong khi Khoản giữa dòng thì có

- Vị trí: `backend/app/ingestion/legal_units.py` (`_marker_events`: `_INLINE_CLAUSE_RE` chỉ cho Khoản; `_POINT_RE` chỉ ở đầu dòng).
- Liên quan: AC-04 / S-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: bản LlamaParse gộp cả Khoản lẫn Điểm vào một đoạn. Ví dụ `parent-495::child-0` (Điều 5. Cơ sở thực tập tốt nghiệp): "1. … a) … b) … 2. … a) … b) …" cho locator "Khoản 1, 2", không có "Điểm a, b". Không phải hồi quy (bản trước cũng không có Điểm cho chunk này) và không vi phạm AC-05, nhưng locator thiếu chi tiết với đúng loại đoạn mà R-01 đã xử lý cho Khoản.
- Đề nghị xử lý: việc tiếp theo (cùng nhóm với R-03): nhận `a)` giữa dòng sau dấu kết câu/`:`, chỉ khi đang ở trong một Khoản đã biết.
- Người xử lý: `agent-claude`.

### R-06 — Nhật ký còn chỗ giữ chỗ commit S-07; báo cáo JSON lớn

- Vị trí: `implementation.md` (bảng tổng quan, dòng "(commit S-07)"); `documents/rag-eval/rag-22/` (8.2 MB, trong đó `locators_before/after_*` ~7.5 MB).
- Liên quan: S-07.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: (1) commit S-07 thực tế là `4977e1f`, bảng chưa ghi; (2) thư mục báo cáo lớn gấp đôi các task đánh giá trước (`rag-06` 4.4 MB, `rag-18` 4.0 MB). Bản `locator_diff_*` đã chứa đủ các thay đổi và metadata (fingerprint, sha256, commit); hai bản dump đầy đủ chỉ cần để chạy lại `--diff`.
- Đề nghị xử lý: điền `4977e1f` vào bảng; người dùng quyết định có giữ hai bản dump đầy đủ trong repo không (có thể tái tạo bằng `dump_citation_locators` trên cùng index).
- Người xử lý: `agent-claude`.

## Lịch sử các vòng review

- trước `2026-11-08T11:13:19+07:00` (thời điểm commit bản sửa) — agent-claude (self_review) — `46bb3d4`…`bdc6d0f` + diff locator lượt 1 — `changes_requested`: R-01.
- `2026-11-08T11:15:39+07:00` — agent-claude (self_review) — `c4bcd78` + báo cáo chụp lại — `approved`; R-01 `resolved`, R-02/R-03 `deferred`.
- `2026-11-08T11:46:50+07:00` — agent-claude (self_review lượt 2, phiên làm việc mới, không mang ngữ cảnh của phiên triển khai; vẫn là cùng agent nên không tính là review độc lập) — `4977e1f` — `approved`. Đã làm:
  - Đọc lại toàn bộ diff mã `e6981f1..4977e1f` (backend, frontend, ba script) và báo cáo `locator_diff_*`.
  - Chạy lại: backend `.venv/Scripts/python.exe -m pytest -q` → `1335 passed, 24 skipped`; frontend `npx vitest run` → `32 files, 217 tests passed`.
  - Chạy thử `is_refusal`/`_normalize_answer_citations` với 7 biến thể ngoài test (trả lời một phần không `[n]`, từ chối kèm `[1]`, từ chối + gợi ý có `[1]`, diễn đạt "không có thông tin", "Theo Điều 5. …"): đúng hợp đồng, phát hiện R-04.
  - Kiểm tay 6 thay đổi locator ngẫu nhiên (seed 7, `added_inherited_clause`/`added_inline_clause`) đối chiếu `text` chunk và chunk liền trước trong DB: 6/6 đúng Khoản (`parent-337::child-0` → Khoản 6, `parent-580::child-1` → Khoản 4, 5, `parent-596::child-0` → Khoản 4, 5, `parent-577::child-1` → Khoản 3, `parent-495::child-0` → Khoản 1, 2, `parent-646::child-1` → Khoản 2); phát hiện R-05.
  - Kiểm `locator_diff_rag_300.json`: không citation nào có Điều bị mất Điểm (`with_points` 699 → 691 chỉ do bỏ Điểm ở chunk không có Điều).
  - Nhận xét mới R-04, R-05, R-06 đều `low`, không bắt buộc.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-02, R-03 (giới hạn đã ghi). Nhận xét `low` không bắt buộc còn `open`: R-04, R-05, R-06 (coordinator quyết định sửa hay hoãn).
- Phần chưa review / giới hạn: chưa có review độc lập (cả hai lượt đều là `self_review`); kiểm tay HTTP `/chat/stream` với LLM thật chưa chạy; không đọc từng dòng hai bản dump JSON đầy đủ, chỉ đọc bản diff.
- Bước tiếp theo: người dùng quyết định review độc lập, push nhánh và mở PR vào `dev`; sau merge chạy `refresh_legal_metadata --apply` trên môi trường khác và cập nhật thẻ Notion RAG-22.
