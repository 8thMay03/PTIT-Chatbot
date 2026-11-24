# Review: 2026-11-24-reembed-documents

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/reembed-documents` (tách từ `dev` tại `e477524`), toàn bộ diff trong
  `implementation.md`.
- Cập nhật lúc: `2026-11-24T23:59:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-07, S-01 … S-04.
- Bằng chứng kiểm chứng: V-01 … V-07.
- Điểm đã đánh giá:
  - Đúng không gian vector: chữ ký lấy cùng khoá với mô hình (`_acquire`), nên job/truy vấn đang chạy khi đổi mô hình vẫn
    ghi/lọc đúng chữ ký của mô hình đã tạo vector.
  - Ghi đè dữ liệu mới: `UPDATE` so `text` + `search_text` nên không gắn vector cũ cho đoạn vừa chia đoạn lại (id đoạn tất
    định nên chỉ so id là không đủ).
  - Kết quả tìm kiếm khi không có vector lệch: giữ đường truy vấn nhanh, thêm một `SELECT … LIMIT 1`.
  - Đổi embedding thất bại: 422 trước khi lưu; settings `embedding_*` được khôi phục; lưu DB thất bại sau khi đổi thì cố quay
    lại embedder trước.
  - Test không chạm DB dev: lifespan có bước ghi DB (`adopt_unsigned_vectors`) bị chặn bằng fixture autouse; settings
    `embedding_*` khôi phục sau mỗi test.
  - Bảo mật: route mới đều `require_admin`; lỗi job dùng `reason` an toàn của `EmbeddingUnavailableError`/`EmbeddingAPIError`.

## Nhận xét

### R-01 — `POST /config/reset` không đổi embedder ngay

- Vị trí: `backend/app/core/config.py` (`reset_runtime_config`), `model_profiles.registry_state`.
- Liên quan: AC-04.
- Mức độ: `low`. Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: reset đặt `embedding_profile_id=None` nhưng embedder vẫn chạy profile cũ. Trang Mô hình báo "Chưa áp
  dụng" và hướng dẫn bấm "Dùng" lại; hành vi này giống trước task.
- Hướng theo dõi: nếu cần, gọi `_switch_embedding_if_changed(None)` trong route reset (đã ghi "Ngoài phạm vi" ở `task.md`).

### R-02 — Thống kê dataset đếm đoạn lệch theo từng dataset

- Vị trí: `backend/app/db/repositories.py` `list_datasets_with_stats`.
- Liên quan: AC-05.
- Mức độ: `low`. Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: thêm 2 truy vấn mỗi dataset (cùng kiểu N+1 với `get_dataset_stats` đã có). Số dataset nhỏ nên không
  đáng kể.
- Hướng theo dõi: gộp thành một truy vấn `GROUP BY dataset_id` nếu số dataset tăng nhiều.

## Lịch sử các vòng review

- 2026-11-24T23:59:00+07:00 — claude-agent — working tree `feat/reembed-documents` — `approved`; R-01, R-02 `deferred`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02 (lý do và hướng theo dõi ở trên).
- Phần chưa review / giới hạn: self review; chưa chạy với dịch vụ embedding thật và container đã build lại.
- Bước tiếp theo: người dùng build lại container và thử luồng đổi mô hình → nhúng lại toàn bộ.
