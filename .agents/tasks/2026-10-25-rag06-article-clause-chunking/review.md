# Review: 2026-10-25-rag06-article-clause-chunking

- Reviewer: `zcode-agent`.
- Hình thức: `self_review` (một agent làm toàn bộ).
- Trạng thái: `changes_requested` (nhận xét bắt buộc R-01 thuộc AC-05 — xử lý bởi người dùng, xem cuối file).
- Bản được review: working tree nhánh `feat/rag06-article-clause-chunking` (nền `f3e95ed`, chưa commit).
- Cập nhật lúc: `2026-10-25T11:10:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-06 của trang task; nhiệm vụ S-01…S-05 của `plan.md`.
- File/thay đổi cần đọc: `backend/app/ingestion/{chunker,cleaner,pipeline}.py`, `backend/app/db/{models,repositories}.py`, `backend/alembic/versions/0003_add_chunk_search_text.py`, `backend/app/retrieval/bm25.py`, `backend/app/vectordb/pgvector_store.py`, `backend/app/core/config.py`, `backend/scripts/{check_chunks,eval_retrieval}.py`, tests, `documents/rag-eval/rag-06/`.
- Bằng chứng kiểm chứng: V-01…V-07 trong `verification.md`.
- Điểm cần đánh giá: tính đúng đắn của regex lọc nhiễu (rủi ro bỏ nhầm nội dung), đúng đắn chunker (AC-01/02), tương thích schema, và tính trung thực của kết luận eval.

## Nhận xét

### R-01 — AC-05 không đạt: chất lượng hybrid ngang bằng, nhóm thủ tục giảm

- Vị trí: `verification.md` V-05; cấu hình `EMBEDDING_INPUT_FIELD` trong `backend/app/core/config.py`.
- Vấn đề: tiêu chí "hit@4 và MRR hybrid tăng; nhóm thủ tục không giảm" không đạt (overall ngang bằng; nhóm thủ tục −5.6 điểm hit@4, nguồn mất điểm là guide "HƯỚNG DẪN THỦ TỤC HÀNH CHÍNH" khi parent theo mục làm evidence phân mảnh). Ngoài ra cấu hình embed `search_text` (đúng chữ đề bài) còn tụt rõ hơn (0.820/0.738) — quyết định mặc định `text` là trái đề bài về mặt chữ dù có đo lường.
- Tác động: task không thể đóng `done` theo quy ước.
- Mức độ: `high`, bắt buộc xử lý trước khi hoàn tất.
- Người xử lý: người dùng (quyết định phạm vi nằm ngoài khả năng agent: thay tiêu chí, hay nhận hướng xử lý tiếp).
- Cách xác nhận: chọn một phương án ở "Kết luận" của `verification.md`; nếu chọn (b)/(c) thì tạo task mới, giữ task này ở trạng thái hiện tại.
- Trạng thái: `open`.

### R-02 — Regex cleaner có rủi ro bỏ nhầm nội dung thật

- Vị trí: `backend/app/ingestion/cleaner.py` (`_SIGNER_ROLE`, `_PERSON_NAME`, `_TOC_LINE_LIKE`, section "MỤC LỤC").
- Vấn đề: luật dựa trên mẫu hẹp và đã soát trên 9 tài liệu `data/` + sửa 2 âm tính giả ("Thư ký hội đồng thông qua…", form nhiều ô trống). Vẫn còn khả năng bỏ nhầm trên tài liệu tương lai (vd. nội dung thật kết thúc bằng số trang trông giống entry mục lục, một đoạn sau "(đã ký)" không phải tên người).
- Tác động: mất dữ liệu index âm thầm nếu mẫu khớp nhầm.
- Mức độ: `medium`, không bắt buộc sửa ngay.
- Người xử lý: `zcode-agent` (đã giảm rủi ro bằng: luật single-leader-run, thoát section TOC khi gặp dòng không giống entry, checker `noise_chunk` in ra từng dòng sẽ bị bỏ khi dry-run).
- Cách xác nhận: chạy `check_chunks --data <dir>` và soát danh sách "cleaner sẽ bỏ N dòng" trước khi ingest kho mới.
- Trạng thái: `resolved` (đã giảm rủi ro + có công cụ soát; theo dõi khi thêm tài liệu mới).

### R-03 — `min_child_size` có thể làm child vượt `child_size` khi gộp cuối bảng

- Vị trí: `backend/app/ingestion/chunker.py` (`_merge_short_pieces` nhánh bảng).
- Vấn đề: khi gộp ghi chú ngắn vào bảng đã vượt soft-limit, child có thể vượt `child_size` đáng kể (bảng dài). Đây là hành vi có chủ đích (giữ ghi chú kèm bảng) nhưng chưa được assert trong test.
- Tác động: một số child dài hơn cấu hình; BM25/embedding vẫn hoạt động.
- Mức độ: `low`, không bắt buộc.
- Người xử lý: `zcode-agent` — test `test_trailing_note_after_table_attaches_to_table_chunk` chốt hành vi gộp; benchmark `_assert_stress_child_sizes` vẫn cho phép bảng vượt hạn mức như trước RAG-06.
- Trạng thái: `resolved` (hành vi được test chốt, thống nhất với chính sách bảng từ trước).

### R-04 — Migration backfill `search_text = text` chỉ là giá trị tạm

- Vị trí: `backend/alembic/versions/0003_add_chunk_search_text.py`.
- Vấn đề: bản chưa re-ingest có `search_text` trùng `text` (thiếu header) — BM25 chạy ngay sau migration sẽ không có ngữ cảnh cho dữ liệu cũ.
- Tác động: hạn chế thời gian ngắn; re-ingest là bước bắt buộc của task này và đã thực hiện trên index local.
- Mức độ: `low`, không bắt buộc.
- Người xử lý: `zcode-agent` — ghi chú rõ trong migration; `check_chunks --db` phát hiện `search_text_missing_context` nếu quên re-ingest.
- Trạng thái: `resolved`.

## Kết luận

- `changes_requested` — chỉ còn R-01 (bắt buộc, thuộc quyền quyết định người dùng về AC-05). R-02…R-04 đã xử lý hoặc ghi nhận có hướng theo dõi.
- Không có nhận xét về tính đúng đắn của mã: AC-01…AC-04, AC-06 có bằng chứng đạt; suite 324 passed / 1 skipped.
