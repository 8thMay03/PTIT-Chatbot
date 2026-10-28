# Review: 2026-10-28-persist-runtime-config

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: commit `4f362c3` trên `feat/persist-runtime-config` (từ `dev` `4880b47`).
- Cập nhật lúc: `2026-10-28T22:40:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06, S-01, S-02.
- File: `backend/app/core/{config,config_crypto,config_store}.py`, `backend/app/db/models.py`,
  `backend/alembic/versions/0006_app_config_overrides.py`, `backend/app/api/{routes,schemas}.py`,
  `backend/app/main.py`, `backend/pyproject.toml`, `backend/tests/{conftest,test_config_persistence}.py`,
  `.env.example`, `frontend/src/ModelsView.jsx`.
- Bằng chứng: V-01..V-06.
- Điểm đánh giá: secret không bao giờ ở dạng rõ trong DB/log/response; fail closed khi thiếu khoá;
  tính nguyên tử giữa RAM và DB; startup không sập; test không chạm DB dev.

## Nhận xét

### R-01 — Log "Đã áp N cấu hình" không hiện dưới uvicorn

- Vị trí: `backend/app/core/config_store.py` (`load_persisted_config`).
- Liên quan: AC-01.
- Mức độ: `low`. Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: uvicorn không cấu hình logger `app.*` ở mức INFO nên dòng thông báo khi nạp
  không xuất hiện (V-05). Cảnh báo (dòng hỏng, DB lỗi) ở mức WARNING vẫn hiện.
- Nếu deferred: cấu hình logging chung cho app là việc riêng; hành vi đã kiểm qua API (V-05).

### R-02 — Nhiều worker không đồng bộ khi đang chạy

- Vị trí: `config_store.apply_config_update`.
- Liên quan: AC-01.
- Mức độ: `medium`. Bắt buộc sửa: không (ngoài phạm vi, hiện 1 worker).
- Trạng thái: `deferred`.
- Vấn đề và tác động: PUT chỉ đổi RAM của worker nhận request; worker khác thấy thay đổi sau khi
  restart. Không xảy ra với cấu hình hiện tại (uvicorn 1 worker).
- Nếu deferred: khi tăng worker, thêm kiểm `max(updated_at)` theo chu kỳ hoặc LISTEN/NOTIFY.

Đã xem và không có vấn đề: rollback settings khi lỗi (`model_dump` snapshot, kể cả lỗi validate);
reset xoá DB trước khi reset RAM; secret `None` (xoá key compatible) lưu thành dòng rỗng và nạp lại
`None`; `config_encryption_key` nằm trong `_RESET_EXCLUDED_FIELDS`; `PERSISTED_FIELDS` có test chặn
trường bảo mật và tên giống secret chưa mã hoá.

## Lịch sử các vòng review

- 2026-10-28T22:40:00+07:00 — claude-agent — working tree — approved; R-01, R-02 deferred.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02 (lý do ở trên).
- Phần chưa review / giới hạn: self_review; chưa có ảnh giao diện.
- Bước tiếp theo: người yêu cầu merge vào `dev`.
