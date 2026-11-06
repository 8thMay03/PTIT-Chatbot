# Review: 2026-11-05-table-search-context

- Reviewer: `claude-code-agent`.
- Hình thức: `self_review` (một agent; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/table-search-context`, commit `3c26865` (nền `eeaf045`; S-01…S-03,
  gồm cả sửa R-01/R-02 trong lúc triển khai).
- Cập nhật lúc: `2026-11-06T22:57:08+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-05 (task này); R-05/AC-07 của task `2026-11-05-table-chunking-coverage`.
- File đã đọc: diff `backend/app/ingestion/chunker.py`, `backend/app/ingestion/pipeline.py`,
  `backend/scripts/refresh_search_text.py`, `backend/tests/test_table_search.py`,
  `backend/tests/test_refresh_search_text.py`, `backend/tests/test_document_pipeline.py`,
  `documents/rag-eval/table-search-context/`.
- Bằng chứng kiểm chứng: V-01…V-04 trong `verification.md` (đều `passed`).
- Điểm đánh giá: `text`/vector/id không đổi; không mất nội dung tìm kiếm khi bỏ hàng thô; điền ô
  không gán sai dữ liệu; script cập nhật DB an toàn (chỉ ghi khi khớp, từ chối khi vector phụ thuộc
  `search_text`); số liệu eval cùng index và giải thích câu tụt.

## Nhận xét

- R-01 (`high`, bắt buộc — đã sửa trong lúc triển khai): bản "thay hàng thô" đầu tiên làm mất nội
  dung của bảng chỉ có header khỏi `search_text` (14 bảng D26, vd. `|1|TS Đoàn Hiếu|Trưởng khoa|0934
  683 131|…|` — LlamaParse coi hàng dữ liệu duy nhất là header). Phát hiện khi số chunk đổi lệch
  (720 vs 706). Sửa: bảng không sinh dòng nào giữ các ô header; test
  `test_header_only_table_keeps_header_content`. Trạng thái: `resolved`.
- R-02 (`high`, bắt buộc — đã sửa trong lúc triển khai): điền mọi ô trống từ hàng trên gán sai dữ
  liệu cho bảng có ô "không áp dụng" (PHỤ LỤC 1 khung kỷ luật: `Khiển trách: 3; Cảnh cáo: 4` gán
  cho hàng 6–9), làm `late_tuition_30_days` rơi khỏi top-10 hybrid. Sửa: chỉ điền dãy ô trống đầu
  hàng (Q-02); test `test_empty_cells_after_first_value_are_not_filled`. Trạng thái: `resolved`.
- R-03 (`medium`, không bắt buộc): Q-02 bỏ sót gộp ô dọc ở cột giữa/cuối (vd. cột "Học kỳ" gộp cho
  nhiều hàng sẽ ra `|2|Giải tích|3||`). Đánh đổi có chủ đích: thiếu ngữ cảnh ít hại hơn gán sai;
  chưa có câu hỏi nào trong hai bộ eval cần. Hướng theo dõi: nếu gặp, điền ô trống cuối hàng chỉ khi
  cột đó có ô trống liên tiếp kết thúc ở hàng có giá trị (cần dữ liệu thật). Trạng thái: `deferred`.
- R-04 (`medium`, không bắt buộc): golden hybrid hit@4 −1 câu (`process_grade_complaint` 4→5) đến
  từ HNSW sau `UPDATE` (ANN đảo hai bản sao `Điều 30`), không phải từ `search_text` — đối chứng
  vector chính xác giữ 0.74 và MRR tăng (V-02). Hệ quả vận hành: chạy `refresh_search_text` (hoặc
  chunk lại) ở môi trường khác cũng xáo nhẹ kết quả ANN ở mức nhiễu ngưỡng; index trùng tài liệu
  (`.pdf` + `.md` cùng sổ tay) khuếch đại nhiễu này. Không `REINDEX` (cũng chỉ là một lần rút mẫu
  khác). Trạng thái: `resolved` (ghi nhận, có bằng chứng).
- R-05 (`low`, không bắt buộc): triển khai cho index đã có cần chạy `python -m
  scripts.refresh_search_text --apply` rồi khởi động lại backend (BM25 dựng trong bộ nhớ); nếu
  `EMBEDDING_INPUT_FIELD=search_text` thì script từ chối và ingest mới sẽ embed dạng tuần tự hóa —
  cần đo lại nếu chuyển cấu hình. Đã ghi trong docstring script, `implementation.md` (Bàn giao) và
  README. Trạng thái: `resolved`.
- R-06 (`low`, không bắt buộc): (a) khóa `(header, hàng)` trùng giữa hai bảng cùng header lấy ngữ
  cảnh điền của bảng đầu (`setdefault`) — chỉ ảnh hưởng hàng có ô đầu trống trùng nguyên văn;
  (b) bảng có header thật ra là hàng dữ liệu sinh cặp nhiễu kiểu `TS. Nguyễn Quý Sỹ: ThS. Phạm Phú
  Tài` — không mất nội dung. Trạng thái: `deferred` (theo dõi nếu eval cho thấy ảnh hưởng).
- R-07 (`low`, không bắt buộc): `test_refresh_search_text.py` import helper từ
  `tests.test_search_text` (đã có tiền lệ `tests.conftest`); chấp nhận để không nhân bản fixture DB.
  Trạng thái: `resolved`.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-06T22:52:59+07:00`, self_review): đọc diff + V-01…V-04; R-01/R-02 đã sửa trong lúc
  triển khai và có test hồi quy; R-03/R-06 hoãn có lý do; R-04/R-05/R-07 ghi nhận. Kết luận `approved`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có (R-01, R-02 đã sửa + test xanh).
- Nhận xét hoãn lại: R-03, R-06.
- Phần chưa review / giới hạn: self_review; eval chạy trên index local trùng tài liệu; `q_table_ulo13`
  và hybrid bảng chưa cải thiện (ngoài phạm vi, xem README).
- Bước tiếp theo: không còn — người dùng duyệt Q-01/Q-02 và đóng hai task (`2026-11-06T22:57:08+07:00`).
