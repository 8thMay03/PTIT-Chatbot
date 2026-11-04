# Implementation: 2026-11-04-llamaparse-tier-select

## Tổng quan triển khai

S-01 và S-02 đã tích hợp trên nhánh `feat/llamaparse-tier-select` (tách từ `dev` tại `3cf9375`).

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-04T22:54:52+07:00`.
- Đã làm:
  - `ParserRegistry.get_parser` tách `<name>:<variant>`, kiểm tra variant thuộc `parser.variants` rồi gọi `parser.with_variant(variant)`; `list_parsers` thêm `variants`/`default_variant` khi parser có.
  - `LlamaParseParser(tier=None)`: `name` là `llamaparse` (theo `LLAMAPARSE_TIER`) hoặc `llamaparse:<tier>`; `LLAMAPARSE_TIERS = (fast, cost_effective, agentic, agentic_plus)`. Tier truyền xuống `convert_with_llamaparse`, `_parse_remote`, `_cache_path` (cache key theo tier thực tế nên `llamaparse` và `llamaparse:<tier mặc định>` dùng chung cache).
  - `resolve_parser_name` kiểm tra bằng `registry.get_parser` để chấp nhận tên có variant.
  - Vì `get_parser_name` trả `parser.name` của bản có variant, metadata tài liệu lưu `llamaparse:<tier>`; preview, rebuild, parse lại hàng loạt dùng lại đúng tier.
- File thay đổi: xem `plan.md` S-01; chưa commit.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng trong `plan.md`.
- Kiểm tra đã chạy: V-01, V-02.
- Còn lại/blocker: không có.

### S-02 — claude-code

- Cập nhật lúc: `2026-11-04T22:54:52+07:00`.
- Đã làm: khi chọn parser có `variants`, modal hiện nhóm radio 4 tier (tên, credit/trang, mô tả ngắn, badge Mặc định) ngay dưới thẻ parser; xác nhận gửi `llamaparse:<tier>`. `parserTitle` hiển thị `LlamaParse · Agentic`; thêm `parserBaseName` để `DatasetView` so khớp tệp hỗ trợ parser khi upload nhiều tệp. README mô tả lựa chọn tier.
- File thay đổi: xem `plan.md` S-02; chưa commit.
- Kiểm tra đã chạy: V-03.
- Còn lại/blocker: chưa kiểm tra thủ công trên trình duyệt.
