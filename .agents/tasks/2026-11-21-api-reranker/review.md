# Review: 2026-11-21-api-reranker

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree chưa commit trên `feat/api-reranker` (nền `430f2ca`), lúc
  `2026-11-21T22:04:53+07:00`.
- Cập nhật lúc: `2026-11-21T22:04:53+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-08 trong `task.md`; bằng chứng trong `verification.md`.
- Đã đọc toàn bộ diff backend (`config.py`, `config_store.py`, `model_profiles.py`, `schemas.py`, `routes.py`,
  `reranker.py`, `confidence.py`), frontend (`catalog.js`, `ModelKindPanel.jsx`, `modelProfiles.js`, `fields.jsx`,
  `pipelineSummary.js`, `ConfigView.jsx`, `RetrievalTestPanel.jsx`), test và `.env.example`.
- Điểm bảo mật đã kiểm:
  - Khoá: chỉ lưu bản mã (`encrypt_secret`, `SECRET_FIELDS`); response chỉ có `has_api_key`; log fallback không có khoá,
    câu hỏi, nội dung đoạn hay body response; DOM không giữ khoá sau khi lưu.
  - SSRF: Base URL kiểm allowlist khi lưu, khi chọn, khi nạp từ DB và trước mỗi lần gọi; không theo redirect.
  - Khoá `.env` không dự phòng (D-02); `test-reranker` không dùng khoá profile LLM.
- Không làm hỏng heuristic/cross-encoder: test cũ giữ nguyên và đạt; cross-encoder chỉ thêm log khi lỗi.

## Nhận xét

### R-01 — `low` — không bắt buộc — `deferred`

- Vị trí: `backend/app/retrieval/reranker.py` (`Reranker.rerank`) và `app/generation/confidence.py`.
- Vấn đề: khi Rerank API (hoặc cross-encoder) lỗi, câu hỏi đó dùng điểm heuristic (0–1, tương đối) nhưng gate vẫn so
  với ngưỡng rerank của provider đang cấu hình.
- Tác động: với ngưỡng ghi đè cho thang 0–1, top-1 heuristic thường gần 1 nên gate dễ đạt hơn — nghiêng về trả lời,
  không từ chối sai. Hành vi giống cross-encoder hiện có.
- Hướng theo dõi: đánh dấu kết quả fallback để gate bỏ tín hiệu rerank; làm cùng task hiệu chỉnh ngưỡng API.

### R-02 — `low` — không bắt buộc — `deferred`

- Vị trí: `backend/app/retrieval/reranker.py` (`_log_fallback`).
- Vấn đề: dịch vụ hỏng kéo dài sinh một cảnh báo cho mỗi câu hỏi.
- Tác động: log nhiều hơn, không lộ dữ liệu. D-04 yêu cầu log mỗi lần lỗi nên giữ.
- Hướng theo dõi: nếu cần, giới hạn tần suất log theo (provider, host, lý do).

### R-03 — `low` — không bắt buộc — `deferred`

- Vị trí: `backend/scripts/eval_confidence.py` (dòng kiểm `provider == "cross-encoder"`).
- Vấn đề: script hiệu chỉnh chưa coi `rerank_api` là điểm tuyệt đối.
- Tác động: chưa hiệu chỉnh được ngưỡng cho mô hình API bằng script; ngoài phạm vi theo task.md.
- Hướng theo dõi: task hiệu chỉnh ngưỡng mô hình API.

### R-04 — `low` — không bắt buộc — `deferred`

- Vị trí: `POST /api/model-profiles/test-reranker`.
- Vấn đề: khoá đã lưu của profile có thể được gửi tới một Base URL khác (do admin nhập trong hộp thoại) miễn nằm trong
  allowlist.
- Tác động: cần quyền admin và host trong allowlist; cùng mô hình tin cậy với `test-llm`.
- Hướng theo dõi: chỉ dùng khoá đã lưu khi Base URL trùng Base URL của profile, nếu muốn chặt hơn.

## Kết luận

- `approved` (self review) trên bản ghi ở đầu file: không có nhận xét `critical`/`high`/`medium`; R-01 … R-04 là `low`,
  không bắt buộc, đã ghi hướng theo dõi.
