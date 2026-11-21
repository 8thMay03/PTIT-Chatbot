# Review: 2026-11-21-settings-pipeline-layout

- Reviewer: `claude-agent`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/settings-pipeline-layout` (nền `43e48f8`): toàn bộ `git diff` + file mới
  trong `frontend/src/settings/`, `docs/design/mockups/settings-pipeline.html`.
- Cập nhật lúc: `2026-11-21T17:34:14+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-08; S-01 … S-03.
- File/thay đổi cần đọc: `SettingsView.jsx`, `ConfigView.jsx`, `settings/SettingsNav.jsx`, `settings/PipelineSteps.jsx`,
  `settings/pipelineSummary.js`, `styles/config.css`, `styles/models.css`, `styles/tokens.css`, các test sửa.
- Bằng chứng kiểm chứng: `verification.md` V-01 … V-08.
- Điểm cần đánh giá:
  - Giữ bản nháp khi đổi bước/tab.
  - Không đổi hợp đồng route/API.
  - Hành vi `RERANKER_PROVIDER_LABELS` sau khi chuyển file.
  - Truy cập bằng bàn phím và trình đọc màn hình.
  - CSS không ảnh hưởng nơi khác dùng `.config-field-group`.
  - Màu chỉ qua token.

## Nhận xét

Không có nhận xét bắt buộc. Các điểm đã đọc và kết luận:

- `RERANKER_PROVIDER_LABELS` có thêm `cross-encoder`. Trong `ConfigView` nhãn này chỉ dùng ở nhánh
  `!rerankApplies`, tức provider khác cross-encoder hoặc reranker đang tắt (khi tắt dùng câu riêng), nên câu hiển thị
  không đổi.
- Section ẩn bằng thuộc tính `hidden`. Trường trong bước ẩn không nhận focus bằng Tab, vẫn thuộc form, nên thanh lưu
  và tóm tắt thay đổi vẫn tính đủ. Người dùng thấy bước nào có thay đổi nhờ chấm trên dải bước và trên tab.
- Lưới hai cột nằm trong `@container` của `.config-section`. `.config-field-group` ngoài section (nếu có) không có
  container nên không bị ảnh hưởng.
- `aria-current="step"` cho dải bước, `"page"` cho tab và loại mô hình. Link giữ `href` thật và không chặn
  Ctrl/Cmd-click (có test).
- Màu mới (`--on-solid-soft`, `--shadow-brand`) khai báo trong `tokens.css`; `config.css` không thêm mã màu thô.
- Khi `/config` đang tải, `ConfigView` hiện spinner và chưa render dải bước. Chấp nhận được vì chưa có giá trị để tóm
  tắt; không ghi thành nhận xét.

## Lịch sử các vòng review

- 2026-11-21T17:34:14+07:00 — claude-agent — working tree sau khi sửa lỗi công tắc và header mobile — `approved`,
  không có R-*.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: không có.
- Phần chưa review / giới hạn:
  - Self-review, không có reviewer độc lập.
  - Chưa kiểm tra trên Safari/Firefox thật.
- Bước tiếp theo: coordinator đóng task; commit/PR khi người dùng đồng ý.
