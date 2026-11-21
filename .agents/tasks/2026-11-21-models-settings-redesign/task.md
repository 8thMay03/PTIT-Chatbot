# Task: Cài đặt quản trị — thiết kế lại màn "Mô hình"

- ID: `2026-11-21-models-settings-redesign`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("design lại màn hình 'Mô hình' trong phần cài đặt của admin")
- Tạo lúc: `2026-11-21T18:07:19+07:00`
- Cập nhật lúc: `2026-11-21T21:18:07+07:00`

## Yêu cầu và kết quả mong muốn

Thiết kế lại tab "Mô hình" của màn Cài đặt quản trị (sau task `2026-11-21-settings-pipeline-layout`). Người dùng
duyệt mockup trước khi triển khai, như lần redesign trước.

**Hiện trạng** (`ModelsView` + `models/ModelKindPanel.jsx`):

- Chọn mô hình ở hai nơi: ô select "Mô hình đang dùng" bên trái và danh sách "Mô hình đã cấu hình" bên phải liệt kê
  cùng một kho; đổi mô hình cần chọn ở ô rồi bấm "Dùng mô hình này".
- Bấm Sửa ở cột phải thì form mở ở cột trái; bốn ô nhà cung cấp bị bóp trong cột hẹp.
- Thanh Ngôn ngữ / Nhúng / Xếp hạng không cho thấy mô hình đang dùng hay cảnh báo của từng khâu.
- Banner thông tin chung chiếm một dòng ở mọi loại mô hình.

**Mockup**: `docs/design/mockups/settings-models.html` (bản có ảnh màn cũ: artifact riêng của người dùng), ba phương án:
A · Chọn từ danh sách (đề xuất), B · Tổng quan theo luồng, C · Kho chung + chi tiết. Người dùng chọn **A**.

**Kết quả cần có** (phương án A):

- Ba thẻ khâu (Sinh câu trả lời / Nhúng văn bản / Xếp hạng lại) thay thanh Ngôn ngữ / Nhúng / Xếp hạng. Mỗi thẻ là
  link `#settings/models-*`, hiện mô hình đang dùng, nhà cung cấp/mô hình và trạng thái (đang chạy, thiếu API key, chờ
  khởi động lại, lỗi khi nạp, đang bật/tắt).
- Mỗi loại một card danh sách duy nhất: hàng đầu là cấu hình `.env` (reranker: Heuristic), sau đó các mô hình trong kho.
  Hàng đang dùng được đánh dấu; các hàng khác có nút "Dùng" đổi mô hình ngay. Bỏ ô select và nút "Dùng mô hình này".
- Đổi mô hình nhúng cần hộp xác nhận (khởi động lại backend, nạp lại tài liệu). Mô hình khác `VECTOR_DIM` không "Dùng" được.
- Thêm/sửa mở hộp thoại ở giữa màn hình (Esc/scrim đóng khi chưa có thay đổi), nhà cung cấp xếp lưới 2 cột. Bản đầu
  là ngăn kéo bên phải; đổi theo yêu cầu người dùng, xem lịch sử quyết định.
- Banner thông tin chung thành dòng chú thích cuối trang; cảnh báo thiếu `CONFIG_ENCRYPTION_KEY` giữ nguyên.
- Mobile <1024px: danh sách mục `#settings` hiện mô hình đang dùng của ba loại; trang loại mô hình ẩn ba thẻ.

## Phạm vi

- Bao gồm:
  - `frontend/src/ModelsView.jsx`, `frontend/src/models/ModelKindPanel.jsx`, `frontend/src/models/fields.jsx`.
  - Mới `frontend/src/models/ModelKindCards.jsx`, `frontend/src/models/activeModels.js` (+ test),
    `frontend/src/models/ProfileDialog.jsx`.
  - `frontend/src/SettingsView.jsx` (bỏ thanh loại, truyền điều hướng, tóm tắt mô hình cho danh sách mobile),
    `frontend/src/settings/SettingsNav.jsx` (bỏ `ModelKindNav`, export helper điều hướng).
  - `frontend/src/styles/models.css`, `frontend/src/styles/config.css` (bỏ CSS thanh loại).
  - Test: `models/ModelsView.test.jsx`, `SettingsView.test.jsx`, `settings/SettingsNav.test.jsx`,
    `ConfigView.cache.test.jsx` nếu bị ảnh hưởng.
- Ngoài phạm vi: backend, API `/api/model-profiles`, hash `#settings/models-*`, trường và kiểm tra của form
  (`catalog.js`).
- Ràng buộc: giữ hành vi embedding (khởi động lại, `VECTOR_DIM`), không xoá được mô hình đang dùng, theme sáng/tối,
  mobile <1024px.

## Tiêu chí nghiệm thu

- [x] AC-01: Tab Mô hình có ba thẻ khâu là link `#settings/models-*` với `aria-current="page"` đúng loại; thẻ hiện mô hình
  đang dùng và trạng thái theo dữ liệu kho/cấu hình; không còn thanh Ngôn ngữ / Nhúng / Xếp hạng.
- [x] AC-02: Mỗi loại có một danh sách (hàng `.env`/Heuristic + kho); không còn ô select "Mô hình đang dùng"; bấm "Dùng"
  gửi `POST /model-profiles/activate` đúng `kind`/`profile_id` (kể cả `null` cho `.env`) và hàng chuyển sang đang dùng.
- [x] AC-03: Embedding: "Dùng" hỏi xác nhận trước khi gọi API; mô hình khác `VECTOR_DIM` bị khoá "Dùng"; báo cần
  khởi động lại / lỗi nạp như trước. Không xoá được mô hình đang dùng.
- [x] AC-04: Thêm/sửa mở hộp thoại ở giữa màn hình (dialog, focus vào ô đầu, Esc/scrim đóng khi chưa đổi, giữ mở khi đã đổi); lưu và
  kiểm tra kết nối hoạt động như trước; API key không còn trong DOM sau khi lưu.
- [x] AC-05: Mobile <1024px: danh sách `#settings` hiện mô hình đang dùng của ba loại; trang loại mô hình không có
  thanh cuộn ngang ở 390px.
- [x] AC-06: `npm test` và `npm run build` ở `frontend/` đạt; có ảnh chụp desktop sáng/tối (danh sách, ngăn kéo) và mobile.

## Tài liệu và phụ thuộc

- Mockup: `docs/design/mockups/settings-models.html`.
- Task trước: `.agents/tasks/2026-11-21-settings-pipeline-layout/`, `2026-10-30-model-registry/`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 … S-03 xong; AC-01 … AC-06 đạt (`verification.md`); review `approved` (self_review). Nhánh
  `feat/models-settings-redesign` (tách từ `dev` tại `2948dc0`); commit và mở PR vào `dev` theo yêu cầu người dùng.
- Blocker: không có.
- Bước tiếp theo: người dùng review và merge PR vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-21T18:07:19+07:00 — claude-agent: tạo task, dựng mockup ba phương án, chờ người dùng chọn.
- 2026-11-21T20:54:57+07:00 — claude-agent: người dùng chọn A; điền phạm vi, AC; chuyển `in_progress`.
- 2026-11-21T21:08:24+07:00 — claude-agent: đóng task sau khi verification đạt và review `approved`.
- 2026-11-21T21:18:07+07:00 — claude-agent: người dùng muốn bấm "Thêm mô hình" thì overlay hiện ở giữa màn hình thay vì bên phải. Đổi
  ngăn kéo thành hộp thoại giữa màn hình cho cả Thêm và Sửa (dùng chung thành phần) để hai thao tác nhất quán; sửa AC-04,
  thêm S-04, V-07. Task giữ `done` sau khi kiểm tra lại và review lại đạt.
- 2026-11-21T21:30:16+07:00 — claude-agent: người dùng yêu cầu commit và mở PR vào `dev`.
