# Review: 2026-11-15-settings-gate-savebar

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: `feat/settings-gate-savebar` tại `415afe3` (diff `a57e4b7..415afe3`).
- Cập nhật lúc: `2026-11-16T00:06:27+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01` … `AC-07`; `S-01` … `S-05`.
- File đã đọc: `backend/app/core/config.py`, `backend/app/api/schemas.py`, hai file test backend,
  `frontend/src/ConfigView.jsx`, `lib/configDraft.js` (+ test), `components/SaveBar.jsx`, `ConfigView.gate.test.jsx`,
  `ConfigView.cache.test.jsx`, `styles/config.css`, `styles/responsive.css`, `SettingsView.jsx`,
  `admin/AdminShell.jsx`, `models/catalog.js`, hai test nhãn.
- Bằng chứng kiểm chứng: `verification.md` V-01 … V-07; 16 ảnh trong `docs/design/assets/settings-gate-savebar/`.
- Điểm đã đánh giá: hợp đồng gate RAG-18 và tương thích ngược `/config`; payload chỉ gồm trường đổi; không mất bản
  nháp; a11y thanh lưu và nút trả từng trường; sáng/tối; hooks không nằm sau `return` sớm.

## Nhận xét

### R-01 — Nhãn loại mô hình viết hoa giữa câu

- Vị trí: `frontend/src/models/ModelKindPanel.jsx:158`, `:559` (dùng `KINDS[kind].label`).
- Vấn đề: sau khi đổi nhãn, câu thành "Đã chuyển Mô hình ngôn ngữ (LLM) sang …", "Chưa có Mô hình xếp hạng lại
  (Reranker) nào".
- Tác động: chữ hoa giữa câu, đọc vẫn hiểu.
- Mức độ: `low`; bắt buộc: không; người xử lý: `claude-agent`.
- Trạng thái: `deferred` — file ngoài phạm vi task; nên thêm trường `noun` (chữ thường) vào `KINDS` khi task
  `2026-11-15-settings-nav-retrieval-test` sửa màn Mô hình.

### R-02 — Ngưỡng cosine 0.30 bị máy chủ bỏ qua

- Vị trí: `backend/app/generation/confidence.py` (`effective_vector_override`), `ConfigView.jsx` (gợi ý 0.30).
- Vấn đề: nhập đúng 0.30 thì lưu "thành công" nhưng máy chủ giữ ngưỡng cũ (luật tương thích RAG-18).
- Tác động: thấp; UI đã hiện gợi ý khi bản nháp là 0.30.
- Mức độ: `low`; bắt buộc: không.
- Trạng thái: `deferred` — đổi luật gate ngoài phạm vi (task.md).

### R-03 — `null` về giá trị `.env`, không phải luôn về bảng hiệu chỉnh

- Vị trí: `backend/app/core/config.py` `update_runtime_config`.
- Vấn đề: nếu `.env` đặt `RETRIEVAL_MIN_VECTOR_SCORE`, gửi `null` trả về giá trị `.env`, nguồn vẫn `override`; link
  "Dùng giá trị hiệu chỉnh" khi đó không đưa về bảng hiệu chỉnh.
- Tác động: chỉ khi triển khai đặt biến này; đúng hợp đồng đã ghi trong plan ("settings về giá trị `.env` ban đầu").
- Mức độ: `low`; bắt buộc: không.
- Trạng thái: `deferred` — ghi trong bàn giao; nếu cần, UI có thể ẩn link khi response sau lưu vẫn `override`.

### R-04 — Response `/config` thêm trường

- Vị trí: `schemas.py` `GuardrailsConfigPayload`, `config.py` `get_runtime_config_dict`.
- Vấn đề: plan ghi "Không đổi schema response" nhưng triển khai thêm 3 trường tuỳ chọn.
- Đánh giá: cần thiết cho AC-01/AC-03, chỉ bổ sung, client cũ không vỡ; quyết định D-1 đã ghi trong
  `implementation.md`, coordinator cập nhật hợp đồng trong `plan.md`.
- Mức độ: `low`; bắt buộc: không.
- Trạng thái: `resolved`.

### R-05 — Ô số rỗng khi đang gõ xoá ghi đè

- Vị trí: `ConfigView.jsx` `parseThreshold` (bản `026b8d0`).
- Vấn đề: chuỗi rỗng/dở dang (ví dụ "0." trong `type=number`) được hiểu là `null` → bản nháp nhảy về giá trị hiệu
  chỉnh khi đang gõ.
- Mức độ: `medium`; bắt buộc: có; người xử lý: `claude-agent`.
- Cách sửa: `415afe3` — chuỗi không phải số thì bỏ qua; bỏ ghi đè chỉ qua link. Thêm ca test "model chưa hiệu chỉnh:
  ô rỗng khi đang gõ không tạo thay đổi…".
- Xác nhận: test mới xanh; `npm test` 303/303.
- Trạng thái: `resolved`.

### R-06 — Hộp xác nhận khôi phục chưa liệt kê trường sẽ bị xoá

- Vị trí: `ConfigView.jsx` `Modal` khôi phục.
- Vấn đề: D-02 của tài liệu nghiên cứu gợi ý liệt kê trường khác mặc định; AC-05 chỉ yêu cầu giữ hộp xác nhận hiện có.
- Mức độ: `low`; bắt buộc: không.
- Trạng thái: `deferred` — cần API trả danh sách override (gần với D-08), để giai đoạn 2.

## Lịch sử các vòng review

- Vòng 1 (`026b8d0`): R-01 … R-06 mở; R-05 bắt buộc → `changes_requested`.
- Vòng 2 (`415afe3`): R-05 `resolved` với bằng chứng; R-04 `resolved` (quyết định ghi nhận); còn lại `deferred`,
  không bắt buộc → `approved`.

## Kết luận

- Kết luận: `approved` (self_review) trên `415afe3`.
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-01, R-02, R-03, R-06 (đều `low`).
- Phần chưa review / giới hạn: chưa có review độc lập; chưa kiểm backend thật + Postgres; chưa kiểm trình đọc màn hình.
- Bước tiếp theo: coordinator push nhánh và mở PR vào `dev` khi người dùng đồng ý.
