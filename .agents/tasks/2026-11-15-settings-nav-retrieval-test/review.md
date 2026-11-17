# Review: 2026-11-15-settings-nav-retrieval-test

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (chỉ một agent trong phiên).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/settings-nav-retrieval-test`, commit `7e38867`
  (tách từ `dev` `08f90bb`).
- Cập nhật lúc: `2026-11-17T21:11:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01` … `AC-07`; `S-01` … `S-05`.
- File/thay đổi đã đọc: toàn bộ diff `dev..7e38867` (backend config store/route/schema
  và test; route/SettingsView/SettingsNav/ConfigView/ModelsView/RetrievalTestPanel/
  gateDecision/retrieval API/CSS và test; ảnh chụp).
- Bằng chứng kiểm chứng: `verification.md` V-01 … V-07, gồm test tự động, đo Chromium
  và ảnh 1366/1024/390 sáng/tối.
- Điểm đánh giá: tương thích hash cũ; không trộn hai kiểu lưu; luật gate frontend khớp
  backend; huỷ request; a11y danh mục/drawer; bundle trang chat; nguồn `updated_at` khi
  xoá dòng/reset; giữ bản nháp khi đổi mục.

## Nhận xét

### R-01 — Luật gate phía client là bản sao có chủ đích

- Vị trí: `frontend/src/lib/gateDecision.js`.
- Vấn đề: luật AND và thứ tự lý do được sao chép từ
  `backend/app/generation/confidence.py`; nếu backend đổi luật mà frontend không đổi,
  kết luận "Bản nháp" sẽ lệch.
- Tác động: chỉ ảnh hưởng phần so ngưỡng nháp, không ảnh hưởng câu trả lời thật.
- Mức độ: `low`; bắt buộc sửa: không.
- Cách giảm thiểu đã có: comment chéo tới file backend, bộ ca `gateDecision.test.js`
  chép từ `test_retrieval_confidence.py`, và verification chạy cả hai bộ.
- Trạng thái: `deferred` — nếu luật gate thay đổi thường xuyên, chuyển phần tính bản
  nháp sang backend (đã ghi trong rủi ro của `plan.md`).

### R-02 — Ảnh chụp dùng API giả lập

- Vị trí: `docs/design/assets/settings-nav-retrieval-test/`.
- Vấn đề: Chromium chặn `/api/**` bằng dữ liệu giả thay vì chạy pipeline thật.
- Tác động: ảnh chứng minh bố cục, trạng thái và tương tác, không chứng minh chất lượng
  truy xuất thật.
- Mức độ: `low`; bắt buộc sửa: không.
- Trạng thái: `deferred` — cùng cách làm của task `settings-gate-savebar`; kiểm tra
  truy xuất thật cần môi trường có dữ liệu/embedding và tốn chi phí.

## Lịch sử các vòng review

- `2026-11-17T21:11:00+07:00` — vòng 1, `self_review` trên `7e38867`: đối chiếu
  `AC-01` … `AC-07`, đọc diff và bằng chứng; không có nhận xét bắt buộc. Kết luận
  `approved`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: `R-01`, `R-02` (không bắt buộc, đã có hướng theo dõi).
- Phần chưa review / giới hạn: không chạy `POST /retrieval/test` với backend thật và dữ
  liệu thật; không kiểm tra trình duyệt ngoài Chromium.
- Bước tiếp theo: coordinator đóng task và mở PR vào `dev` khi người dùng yêu cầu.
