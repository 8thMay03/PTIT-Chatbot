# Implementation: 2026-10-21-tests-off-data-corpus

## Tổng quan triển khai

Hoàn tất trên nhánh `refactor/tests-off-data-corpus`. Cả hai test file không còn
đọc bắt buộc `data/` khi dữ liệu thiếu; phần cần kho đầy đủ được đánh dấu
`@pytest.mark.corpus` và skip kèm lý do.

## Nhật ký theo nhiệm vụ

### S-01 — agent-opencode

- Cập nhật lúc: `2026-10-21T00:06:03+07:00`.
- Đã làm:
  - Soát 20 case FAQ trong `ptit_faq.json` trên bản D26
    (`data/processed/Sổ tay sinh viên D26 _1_ _1_.md`). 17 case giữ nguyên;
    3 case cập nhật theo sự thật D26:
    - `director_ptit`: Giám đốc Học viện là **PGS.TS. Đặng Hoài Bắc** (trước đây
      là Vũ Văn San theo D21).
    - `chairman_council` → thay bằng `union_chairman`: D26 không liệt kê Chủ tịch
      Hội đồng Học viện; chủ tịch Công đoàn là PGS.TS. Trần Quang Anh.
    - `double_degree`: D26 không dùng cụm "2 văn bằng"/"2 ngành"; theo D26 sinh
      viên đăng ký "học 2 CTĐT đồng thời" (Phòng Giáo vụ giải quyết).
  - Trích `fixtures/corpus/so-tay-sinh-vien-d26-excerpt.md` (~15 KB) bằng script
    một lần (không commit): chọn section theo anchor, gộp span chồng lấn, lọc bỏ
    mọi dòng có email/số điện thoại/hotline. Nguồn sự thật là file D26 đã convert.
  - Dựng `fixtures/corpus/chunker-tables-benchmark.md` (~5 KB) — dữ liệu giả lập:
    bảng markdown 20 dòng `TX-2026-001..020` có header "Mã Giao Dịch", 2 bảng
    markdown phụ (`USR-`, `FTR-`), 1 bảng HTML có `<thead>`; đủ dài để chunker
    phải tách và lặp header.
- File thay đổi: `backend/tests/fixtures/corpus/so-tay-sinh-vien-d26-excerpt.md` (mới),
  `backend/tests/fixtures/corpus/chunker-tables-benchmark.md` (mới),
  `backend/tests/fixtures/ptit_faq.json`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: cấu trúc fixture
  `fixtures/corpus/` là nguồn chuẩn cho test; `ptit_ragas_100.json` đã soát,
  không chứa sự thật bị thay đổi nên giữ nguyên.
- Kiểm tra đã chạy: xác minh từng case bằng logic chunk 900/150 + BM25 như test
  (chi tiết trong `verification.md`).
- Còn lại/blocker: không có.

### S-02 — agent-opencode

- Cập nhật lúc: `2026-10-21T00:06:03+07:00`.
- Đã làm:
  - `test_ptit_faq.py`: test xếp hạng BM25 (top_k=50) chạy trên trích ngắn đóng
    gói; thêm biến thể `@pytest.mark.corpus` chạy trên toàn bộ file `.md` trong
    `settings.documents_path` (quét rglob), skip với lý do rõ ràng khi không có
    file nào. Biến thể corpus kiểm tra "bằng chứng tồn tại trong kho" (quét toàn
    bộ chunk) thay vì thứ hạng top-50, vì trên kho đầy đủ các đoạn cùng chủ đề
    (ví dụ "Giám đốc Học viện" của đơn vị trực thuộc) có thể lấn át kết quả đúng.
  - `test_chunker_tables_benchmark.py`: các bất biến benchmark tách thành hàm
    dùng chung, chạy trên fixture tổng hợp (luôn chạy); thêm 1 test
    `@pytest.mark.corpus` chạy lại toàn bộ bất biến trên
    `data/test_chunker_tables _1_.md` khi có, skip kèm lý do khi thiếu.
  - `pyproject.toml`: đăng ký marker `corpus` trong `[tool.pytest.ini_options]`.
- File thay đổi: `backend/tests/test_ptit_faq.py`,
  `backend/tests/test_chunker_tables_benchmark.py`, `backend/pyproject.toml`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: `pytest`, `pytest -m corpus`, mô phỏng clone sạch bằng
  `DOCUMENTS_PATH` trỏ sang thư mục rỗng (chi tiết trong `verification.md`).
- Còn lại/blocker: không có.

## Trao đổi giữa agents

### MSG-agent-opencode-001

- Lúc: `2026-10-20T22:30:00+07:00`.
- Từ: `agent-opencode`; đến: `coordinator`.
- Nhiệm vụ: `S-01`.
- Loại: `decision`.
- Nội dung: người dùng xác nhận chuyển test FAQ sang D26. Khảo sát cho thấy 3/20
  case FAQ lệch sự thật theo D26 (Giám đốc mới, không còn Chủ tịch Hội đồng,
  quy định học 2 CTĐT thay cho "2 văn bằng").
- Hành động mong muốn: ghi nhận vào phạm vi task (đã cập nhật `task.md`).

### MSG-agent-opencode-002

- Lúc: `2026-10-21T00:06:03+07:00`.
- Từ: `agent-opencode`; đến: `coordinator`.
- Nhiệm vụ: `S-01`, `S-02`.
- Loại: `handoff`.
- Nội dung: hoàn tất cả hai nhiệm vụ, cả 4 AC có bằng chứng.
- Hành động mong muốn: review diff trên bản mới nhất.

## Bàn giao

### HANDOFF-agent-opencode-002 — S-01, S-02

- Từ / đến: `agent-opencode` / `reviewer (self_review)`.
- Đã hoàn tất: fixture corpus D26 + benchmark tổng hợp; tách test + marker.
- File/branch/commit/patch: nhánh `refactor/tests-off-data-corpus`, working tree
  (chưa commit tại thời điểm bàn giao).
- Kiểm chứng: xem `verification.md`, cả 4 AC `passed`.
- Review: xem `review.md`.
- Hạn chế / còn lại: file benchmark thật trong `data/` đã mất; corpus test phụ
  thuộc dữ liệu thật nên chỉ chạy được trên máy có `data/`.
- Bước tiếp theo: review và kết luận.
- Phản hồi nhận bàn giao: (chưa có).
