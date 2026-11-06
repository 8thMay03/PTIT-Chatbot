# Review: 2026-11-05-table-chunking-coverage

- Reviewer: `claude-code-agent`.
- Hình thức: `self_review`.
- Trạng thái: `approved` (vòng 2: AC-07/R-05 đạt qua task `2026-11-05-table-search-context`).
- Bản được review: nhánh `feat/table-chunking-coverage` sau S-01…S-07 + 2 vòng sửa review.
- Cập nhật lúc: `2026-11-06T22:52:59+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-08; S-01…S-07.
- File/thay đổi cần đọc: diff nhánh `feat/table-chunking-coverage` so với `dev` — `backend/app/ingestion/chunker.py`, `backend/app/ingestion/cleaner.py`, `backend/app/ingestion/pipeline.py`, `backend/alembic/env.py`, tests và fixture mới, `documents/rag-eval/table-chunking/` (8 JSON + README).
- Bằng chứng kiểm chứng: V-01…V-08 trong `verification.md` (V-07 `failed` ở vế cải thiện bảng; còn lại `passed`), full pytest 782 passed/1 skipped.
- Điểm cần đánh giá: không mất/cắt hàng trong mọi đường tách bảng; regex mới không nhận nhầm văn xuôi; gộp bảng ngắt trang không gộp nhầm bảng khác; tương thích bảng `---` và fixture hiện có; cleaner không lọc thiếu bảng mục lục; cảnh báo pipeline không gây ồn hay chặn ingest; số liệu eval trước/sau cùng index.

## Nhận xét

- R-01 (`medium`, không bắt buộc): gộp bảng ngắt trang vẫn gộp hai bảng cùng header
  bị ngăn cách bởi `---` có dòng trống quanh nó (khối `---` bị bỏ lặng khi tách nên hai
  bảng thành kề nhau). Hành vi lành tính (hàng nguyên vẹn, cùng header nên gộp nhóm
  đúng cho retrieval) và chưa từng gặp trên D26; docstring `_merge_page_break_tables`
  đã ghi đúng hành vi. Người xử lý: `claude-code-agent` (ghi chú). Trạng thái: `resolved`.
- R-02 (`low`, không bắt buộc): `_log_table_coverage` chạy toàn bộ bất biến trên mọi
  ingest có ≥ 5 dòng `|` (vài giây với tài liệu cỡ D26) và `clean_text` chạy 2 lần.
  Chấp nhận được (ingest vốn bị chi phối bởi embedding); có thể thêm fast-path sau.
  Người xử lý: `claude-code-agent`. Trạng thái: `resolved` (chấp nhận chi phí, ghi nhận).
- R-03 (`high`, bắt buộc — đã sửa trong vòng review): regex `_HTML_TABLE_CLOSE` thừa;
  `_peek_table_run` nuốt cả heading khi bảng HTML cụt (mất nội dung sau mục lục);
  checker `missing_header` HTML gắn cờ oan cho bảng không `<thead>`. Đã sửa cả ba +
  thêm 2 test hồi quy (`test_clean_text_truncated_toc_table_does_not_swallow_rest`,
  `test_html_table_without_thead_has_no_missing_header`); full suite xanh.
  Người xử lý: `claude-code-agent`. Trạng thái: `resolved`.
- R-04 (`high`, bắt buộc — đã sửa trong lúc triển khai): `alembic/env.py` gọi
  `fileConfig` vô điều kiện làm disable mọi logger → test caplog chạy sau
  `test_alembic_upgrade_check_and_downgrade_cycle` rớt oan (ô nhiễm toàn suite).
  Sửa gốc: `env.py` tôn trọng `configure_logger=False`, test alembic đặt attribute
  này (production không đổi vì mặc định True). Nằm ngoài phạm vi file của plan nhưng
  cần thiết để AC-08 xanh; không đổi hành vi migration. Người xử lý:
  `claude-code-agent`. Trạng thái: `resolved`.
- R-05 (`high`, chặn `done` của task — KHÔNG phải lỗi mã nguồn): AC-07 vế tăng hit@4
  bảng chưa đạt (bm25 0.857→0.857, hybrid 0.786→0.786): hàng đã nguyên vẹn nhưng
  chunk chứa hàng không vào top-k — lever nằm ở `search_text` (D-01, đã hoãn có điều
  kiện). Chuyển sang task tiếp theo `2026-11-05-table-search-context` làm tiêu chí
  chính; task này giữ `in_review`. Người xử lý: task tiếp theo.
  Trạng thái: `resolved` (`2026-11-06T22:52:59+07:00`): task `2026-11-05-table-search-context`
  đạt AC-03/AC-04 — bảng bm25 hit@4 0.857→0.929, hybrid không giảm; golden không thụt lùi về
  thực chất (hybrid −1 câu do nhiễu HNSW, có đối chứng) — xem V-07 và
  `documents/rag-eval/table-search-context/README.md`.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-05T23:42:51+07:00`, self_review): đọc diff + bằng chứng V-01…V-08;
  nêu R-01…R-05; sửa R-03 (3 lỗi), xác nhận R-04 đã sửa đúng; R-01/R-02 chấp nhận có
  ghi nhận; R-05 chuyển follow-up. Kết luận `approved` cho mã nguồn.
- Vòng 2 (`2026-11-06T22:52:59+07:00`, self_review): đối chiếu bằng chứng task
  `2026-11-05-table-search-context`; R-05 → `resolved`. Mã nguồn của task này không đổi.
  Kết luận `approved` (task + mã nguồn).

## Kết luận

- Kết luận: `approved` (vòng 2: R-05/AC-07 đã đạt qua task `2026-11-05-table-search-context`).
- Nhận xét bắt buộc còn mở: không còn (R-03, R-04 đã sửa + kiểm tra lại xanh; R-05 đã
  `resolved` qua `2026-11-05-table-search-context`).
- Nhận xét hoãn lại: R-01, R-02 (không bắt buộc, có lý do và hướng theo dõi trong mục trên).
- Phần chưa review / giới hạn: self_review (một agent); eval retrieval phụ thuộc DB local
  và API embedding (đã chạy thật, số liệu trong `documents/rag-eval/table-chunking/`).
- Bước tiếp theo: không còn — người dùng đóng task (`2026-11-06T22:57:08+07:00`).
