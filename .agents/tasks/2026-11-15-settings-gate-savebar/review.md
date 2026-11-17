# Review: 2026-11-15-settings-gate-savebar

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: `feat/settings-gate-savebar` tại `415afe3` (diff `a57e4b7..415afe3`); vòng 3 đối chiếu tại
  `5d20891` (mã `backend/`, `frontend/` trùng `415afe3`, chỉ thêm nhật ký task và ảnh).
- Cập nhật lúc: `2026-11-17T20:11:17+07:00`.

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

### R-07 — Ghi đè ngưỡng rerank bị ẩn khi máy chủ đang tắt reranker

- Vị trí: `backend/app/generation/confidence.py` `thresholds_from_settings` (nhánh `not_applicable`),
  `frontend/src/lib/configDraft.js` `valuesFromConfig` (`minRerankScore`), `ConfigView.jsx` `rerankApplies`.
- Vấn đề: khi máy chủ tắt reranker (hoặc provider khác `cross-encoder`), response trả `min_rerank_score: null`,
  `rerank_threshold_source: "not_applicable"` dù `settings.retrieval_min_rerank_score` vẫn giữ một ghi đè đã lưu. Bật
  reranker trong bản nháp thì trường rerank hiện huy hiệu "Đã hiệu chỉnh cho <model>" với giá trị bảng hiệu chỉnh và
  không có link bỏ ghi đè; sau khi lưu, gate thực tế dùng ghi đè ẩn.
- Tác động: hiển thị sai ngưỡng cho tới khi lưu xong (response sau lưu trả `override` đúng); không xoá được ghi đè ẩn
  trong cùng lần lưu. Cần đủ ba điều kiện: từng ghi đè rerank, reranker đang tắt, bật lại ở form này.
- Mức độ: `low`; bắt buộc: không; người xử lý: `claude-agent`.
- Hướng sửa: backend trả thêm ghi đè thô (ví dụ `min_rerank_score_override`) bất kể có áp dụng hay không, và
  `valuesFromConfig` đọc trường đó.
- Trạng thái: `deferred` — gom vào task `2026-11-15-settings-nav-retrieval-test` (cùng sửa nhóm ngưỡng).

### R-08 — Cảnh báo nguồn ngưỡng hiện khi không đọc được `/config`

- Vị trí: `ConfigView.jsx` `uncalibratedWarning`, dòng `gate-rerank-na`; `calibratedFromConfig(undefined)`.
- Vấn đề: GET `/config` lỗi thì `calibrated` là `{ vector: null, rerank: null }`, form hiện "Chưa hiệu chỉnh cho mô hình
  hiện tại: chatbot đang bỏ qua tín hiệu này" và "không áp dụng với reranker hiện tại" — khẳng định về trạng thái máy
  chủ mà giao diện không biết.
- Tác động: thấp; alert đầu trang đã nói giá trị bên dưới là mặc định giao diện.
- Mức độ: `low`; bắt buộc: không.
- Hướng sửa: ẩn huy hiệu/cảnh báo nguồn ngưỡng khi `!configQuery.data`.
- Trạng thái: `deferred` — cùng hướng theo dõi R-07.

### R-09 — Thanh trượt và ô số ngưỡng lệch nhau

- Vị trí: `ConfigView.jsx` `#cfg-minvec` (0.1–0.8) so với `#cfg-minvec-number` (0–1); `#cfg-minrerank` (−10…10) so với
  `#cfg-minrerank-number` (−20…20); `parseThreshold`.
- Vấn đề: ghi đè ngoài khoảng thanh trượt (ví dụ 0.9) làm thanh kẹt ở đầu mút, chạm thanh thì giá trị nhảy về mút.
  Xoá hết chữ trong ô số thì bản nháp giữ giá trị cũ (đúng D-3) nhưng ô hiện rỗng trong khi thanh lưu vẫn ghi giá trị
  cũ, tới lần render sau.
- Mức độ: `low`; bắt buộc: không.
- Hướng sửa: cùng khoảng cho thanh và ô (hoặc nới thanh theo giá trị hiện tại); khôi phục chữ trong ô khi `blur`.
- Trạng thái: `deferred`.

## Lịch sử các vòng review

- Vòng 1 (`026b8d0`): R-01 … R-06 mở; R-05 bắt buộc → `changes_requested`.
- Vòng 2 (`415afe3`): R-05 `resolved` với bằng chứng; R-04 `resolved` (quyết định ghi nhận); còn lại `deferred`,
  không bắt buộc → `approved`.
- Vòng 3 (`5d20891`, `2026-11-17T20:11:17+07:00`, phiên làm việc mới, vẫn `self_review`): đọc lại toàn bộ diff
  `a57e4b7..415afe3` (backend `update_runtime_config` + thứ tự áp `reranker` trước `guardrails`, `exclude_unset` ở
  route; `configDraft.js`, `SaveBar.jsx`, `ConfigView.jsx`, CSS không có màu cứng), chạy lại `npx vitest run` 303/303
  (37 file), `npm run build` OK, `python -m pytest` 1346 passed / 24 skipped; xem ảnh `after-desktop-dark-gate.png`,
  `after-mobile-light-top.png`. Thêm R-07, R-08, R-09 (đều `low`, không bắt buộc, `deferred`). Giữ `approved`.

## Kết luận

- Kết luận: `approved` (self_review) trên `415afe3`; xác nhận lại ở vòng 3 trên `5d20891`.
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-01, R-02, R-03, R-06, R-07, R-08, R-09 (đều `low`).
- Phần chưa review / giới hạn: chưa có review độc lập; chưa kiểm backend thật + Postgres; chưa kiểm trình đọc màn hình.
- Bước tiếp theo: coordinator push nhánh và mở PR vào `dev` khi người dùng đồng ý.
