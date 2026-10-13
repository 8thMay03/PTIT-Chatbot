# Review: 2026-10-13-models-view-redesign

- Reviewer: `claude`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree trên base `79dae24`; diff `frontend/src/ModelsView.jsx`, `frontend/src/styles/models.css`, `frontend/src/styles/components.css`.
- Cập nhật lúc: `2026-10-14T00:36:10+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 → AC-07, S-01.
- Bằng chứng kiểm chứng: V-01 → V-07 passed; V-08 not_run.
- Điểm cần đánh giá: đúng hợp đồng API, không làm mất khoá/giá trị trên máy chủ, bảo mật API key, hồi quy CSS dùng chung, khả năng truy cập.

Đã đối chiếu payload với `update_runtime_config`:

- Không gửi chuỗi rỗng cho `openai_compatible_api_key` (backend sẽ đặt `None`).
- Base URL OpenAI chỉ gửi khi người dùng sửa.
- Reranker không gửi `enabled`.

Kiểm tra `create_llm_provider_from_config`: khi `api_key` là `null`, backend dùng khoá đã lưu, nên "Kiểm tra kết nối" hoạt động cả khi không nhập lại khoá.

## Nhận xét

### R-01 — Trạng thái bật/tắt reranker có thể cũ

- Vị trí: `frontend/src/ModelsView.jsx`, `RerankerSection`.
- Liên quan: AC-05.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: Settings giữ cả hai tab luôn mounted. Nếu người dùng bật/tắt reranker ở Cấu hình RAG rồi quay lại tab Mô hình, nhãn "Đang bật/Đang tắt" vẫn là giá trị lúc tải trang cho tới khi tải lại.
- Đề nghị xử lý: tải lại `/config` khi tab Mô hình được hiển thị, hoặc đưa cấu hình lên `SettingsView` làm nguồn chung.
- Người xử lý: `claude`.
- Nếu deferred: chỉ ảnh hưởng nhãn hiển thị, không ảnh hưởng dữ liệu lưu. Theo dõi khi gom trạng thái Settings.

### R-02 — Backend không trả base URL OpenAI khi nhà cung cấp khác đang được dùng

- Vị trí: `backend/app/core/config.py` (`get_runtime_config_dict`); `frontend/src/ModelsView.jsx` (`sendOnlyIfChanged`).
- Liên quan: AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: khi đổi sang OpenAI từ nhà cung cấp khác, ô Base URL hiện trống dù máy chủ có thể đang lưu một giá trị. Giao diện đã tránh xoá nhầm bằng cách chỉ gửi trường này khi người dùng sửa, nhưng người dùng không nhìn thấy giá trị cũ.
- Đề nghị xử lý: backend trả thêm `openai_base_url` trong `LLMConfigPayload`. Việc này nằm ngoài phạm vi (không sửa backend).

### R-03 — Selector chết trong config.css

- Vị trí: `frontend/src/styles/config.css`, media query `max-width: 900px` (`.model-mgmt-page`).
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: class này không còn được dùng; không gây lỗi hiển thị. Không sửa để giữ phạm vi file đã đăng ký.

## Lịch sử các vòng review

- 2026-10-14T00:36:10+07:00 — claude — working tree trên base `79dae24` — approved; R-01 → R-03 low, deferred.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02, R-03.
- Phần chưa review / giới hạn: chưa chạy với backend thật (V-08).
- Bước tiếp theo: coordinator đóng task.
