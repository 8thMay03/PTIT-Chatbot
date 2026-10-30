# Review: 2026-10-30-model-registry

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree `feat/model-registry` sau commit `0463d9b` (gồm sửa R-01).
- Cập nhật lúc: `2026-10-30T22:25:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06, S-01, S-02.
- Bằng chứng: V-01..V-05.
- Điểm đánh giá: khoá không rò ra client/log/DB dạng rõ, không gửi khoá sang nhà cung cấp/máy chủ khác;
  tính nguyên tử DB + settings; khởi động không sập; tương thích PUT /config và màn Cấu hình RAG.

## Nhận xét

### R-01 — Đổi nhà cung cấp giữ khoá của nhà cung cấp cũ

- Vị trí: `backend/app/core/model_profiles.py` (`update_profile`).
- Mức độ: `high`. Bắt buộc sửa: có. Trạng thái: `resolved`.
- Vấn đề: sửa profile OpenAI thành Gemini mà không nhập khoá mới thì bản mã khoá OpenAI vẫn được giữ và
  sẽ được gửi cho Gemini; UI lại hiển thị "chưa có khoá".
- Cách sửa: `provider != row.provider` và không nhập khoá → bỏ khoá. Test
  `test_changing_provider_drops_key_of_old_provider` (V-01).

### R-02 — Script CLI không dùng embedding đã chọn

- Vị trí: `backend/scripts/ingest.py` (không chạy lifespan).
- Mức độ: `medium`. Bắt buộc sửa: không. Trạng thái: `deferred`.
- Vấn đề: chọn profile embedding trên UI rồi nạp tài liệu bằng script CLI sẽ nhúng bằng mô hình `.env`,
  lệch với vector truy vấn của server. UI đã ghi chú giới hạn này.
- Hướng theo dõi: gọi `load_persisted_config()` + `load_selected_embedding_at_startup()` ở đầu các
  script nhúng.

### R-03 — Khoá profile LLM đang dùng lưu ở hai bảng

- Vị trí: `activate_profile` → `save_overrides`.
- Mức độ: `low`. Bắt buộc sửa: không. Trạng thái: `deferred`.
- Vấn đề: bản mã khoá nằm ở `model_profiles` và `app_config_overrides`; cả hai đều mã hoá, đồng bộ trong
  cùng transaction khi sửa profile đang dùng. Chấp nhận để giữ một đường áp cấu hình duy nhất.

Đã xem và không có vấn đề: test-llm với profile tương thích OpenAI không có khoá dùng `not-needed` thay vì
khoá đang chạy; URL profile kiểm lại allowlist khi kích hoạt; xoá profile đang chọn 409; PUT /config
temperature giữ lựa chọn profile; reset giữ embedder đang chạy nhưng bỏ lựa chọn.

## Lịch sử các vòng review

- 2026-10-30T22:23:00+07:00 — claude-agent — sau `0463d9b` — changes_requested (R-01).
- 2026-10-30T22:25:00+07:00 — claude-agent — working tree — approved; R-01 resolved, R-02/R-03 deferred.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Phần chưa review / giới hạn: self_review; chưa xem giao diện bằng trình duyệt (V-06).
