# Task: Tách test khỏi dữ liệu thật trong data/

- ID: `2026-10-21-tests-off-data-corpus`
- Trạng thái: `done`
- Coordinator: `agent-opencode`
- Người yêu cầu: Người dùng (issue "26 test fail/lỗi vì đọc file trong data/")
- Tạo lúc: `2026-10-21T00:06:03+07:00`
- Cập nhật lúc: `2026-10-21T00:06:03+07:00`

## Yêu cầu và kết quả mong muốn

26 test fail/lỗi khi chạy trên bản clone sạch vì đọc các file trong `data/` (bị gitignore):

- `test_ptit_faq.py` cần `so-tay-sinh-vien-d21.md`.
- `test_chunker_tables_benchmark.py` cần `test_chunker_tables _1_.md`.

Kết quả mong muốn: test không phụ thuộc dữ liệu thật trong `data/` khi thiếu; phần cần kho đầy đủ được đánh dấu `@pytest.mark.corpus` và tự skip kèm lý do rõ ràng.

Quyết định phạm vi (đã xác nhận với người dùng ngày 2026-10-20): test FAQ **chuyển sang dùng sổ tay D26** (kho hiện tại), thay vì giữ D21.

## Phạm vi

- Bao gồm: `backend/tests/test_ptit_faq.py`, `backend/tests/test_chunker_tables_benchmark.py`, `backend/tests/fixtures/ptit_faq.json` (cập nhật case theo D26), `backend/tests/fixtures/corpus/` (fixture mới), `backend/pyproject.toml` (đăng ký marker).
- Ngoài phạm vi: pipeline ingestion, kho tài liệu thật trong `data/`, `scripts/evaluate*.py`, `ptit_ragas_100.json` (đã soát — không chứa sự thật bị thay đổi).
- Ràng buộc: fixture không chứa thông tin cá nhân (SĐT/email), dung lượng < 200 KB; trên bản clone sạch `pytest` phải 0 failed, 0 errors.

## Tiêu chí nghiệm thu

- [x] AC-01: Trên bản clone sạch (không có `data/`), `pytest` cho kết quả 0 failed, 0 errors.
- [x] AC-02: `pytest -m corpus` chạy được khi có dữ liệu; khi skip phải in lý do.
- [x] AC-03: Fixture không chứa thông tin cá nhân, dung lượng dưới 200 KB.
- [x] AC-04: Marker `corpus` được đăng ký trong `pyproject.toml`.

## Tài liệu và phụ thuộc

- `backend/tests/fixtures/ptit_faq.json` — bộ case FAQ.
- `data/processed/Sổ tay sinh viên D26 _1_ _1_.md` — nguồn trích fixture (gitignored, không vào repo).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: hoàn tất — cả 4 AC có bằng chứng `passed`, review `approved` (self_review) trên bản mới nhất.
- Blocker: không có.
- Bước tiếp theo: không có; task đóng.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-20T22:30:00+07:00` — `agent-opencode`: người dùng chọn phương án "Chuyển sang D26" thay vì giữ D21; scope mở rộng để cập nhật các case FAQ bị thay đổi sự thật theo kho D26.
- `2026-10-21T00:06:03+07:00` — `agent-opencode`: chuyển sang `in_review` sau khi có bằng chứng cho cả 4 AC.
- `2026-10-21T00:06:03+07:00` — `agent-opencode` (coordinator): chuyển sang `done` sau khi review `approved`.
