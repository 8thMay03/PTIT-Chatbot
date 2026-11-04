# Verification: 2026-11-04-llamaparse-tier-select

- Verifier: `claude-code`.
- Trạng thái tổng: `passed` (test tự động); kiểm tra thủ công `not_run`.
- Bản được kiểm tra: working tree nhánh `feat/llamaparse-tier-select` trên `3cf9375`.
- Môi trường: Windows 11, Python `.venv` của backend, Node/Vite/Vitest của frontend.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code / 2026-11-04T22:54:52+07:00.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q`.
- Kỳ vọng: test mới `test_selected_tier_overrides_configured_default` (4 tier: SDK nhận đúng tier, cache theo tier, `llamaparse` chỉ dùng chung cache khi trùng tier mặc định), `test_unknown_tier_is_rejected`, `test_upload_parses_with_selected_parser_and_stores_it` (metadata lưu `llamaparse:agentic`) đạt; test cũ không hỏng.
- Kết quả thực tế: lần chạy toàn bộ cuối cùng `723 passed, 21 skipped`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest trong phiên.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code / 2026-11-04T22:54:52+07:00.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `test_parsers.py::test_llamaparse_is_an_opt_in_alternative_to_docling`.
- Kỳ vọng: item LlamaParse có `variants` đủ 4 tier và `default_variant = cost_effective`; Docling/Text không đổi.
- Kết quả thực tế: đạt trong lần chạy V-01.
- Trạng thái: `passed`.
- Bằng chứng: output pytest.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code / 2026-11-04T22:54:52+07:00.
- Loại: test tự động + build.
- Thư mục chạy: `frontend`.
- Lệnh / thao tác: `npx vitest run`, `npx vite build`.
- Kỳ vọng: `ParserSelectionModal.test.jsx` (tier ẩn khi chọn Docling, hiện 4 tier khi chọn LlamaParse, mặc định `cost_effective`, gửi `llamaparse:cost_effective` / `llamaparse:agentic_plus`; `parserTitle`/`parserBaseName`) đạt; build thành công.
- Kết quả thực tế: `25 files / 182 tests passed`; build `✓ built in 2.17s`.
- Trạng thái: `passed`.
- Bằng chứng: output vitest/vite trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu 2 test pipeline lỗi vì fake `convert_with_llamaparse` không nhận `tier=`; đã sửa fake (`**_`), chạy lại đạt.
- Chưa kiểm tra thủ công giao diện trên trình duyệt và chưa gọi LlamaCloud thật với từng tier (`not_run`).

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03 (test tự động).
- Tiêu chí chưa đạt/chưa xác minh: kiểm tra thủ công UI/LlamaCloud thật.
- Đề xuất: người dùng thử modal trên trình duyệt trước khi merge.
