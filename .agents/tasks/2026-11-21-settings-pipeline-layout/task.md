# Task: Cài đặt quản trị — bố cục "Đường ống trả lời" (phương án A)

- ID: `2026-11-21-settings-pipeline-layout`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("tôi muốn design lại màn hình cài đặt của admin", chọn phương án A)
- Tạo lúc: `2026-11-21T17:22:24+07:00`
- Cập nhật lúc: `2026-11-21T17:34:14+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng thấy màn Cài đặt quản trị "trông cũ/nhạt", muốn tái cấu trúc bố cục (giữ route và API) và duyệt mockup
trước. Ba phương án nằm ở `docs/design/mockups/settings-pipeline.html`; người dùng chọn **A · Đường ống trả lời**.

**Hiện trạng** (sau task `2026-11-15-settings-nav-retrieval-test`):

- Desktop có 4 cột: sidebar app, danh mục cài đặt, form, bảng "Thử với câu hỏi" (≥1280px). Form còn ~480px.
- Card trắng lồng card trắng, các mục giống nhau, ít phân cấp; dòng gợi ý kỹ thuật `#settings/gate` trong danh mục.
- "Hệ thống trả lời" là một form cuộn liền có scroll-spy; "Mô hình" là hai card cạnh nhau với banner xanh dương.

**Kết quả cần có** (phương án A):

- Bỏ cột danh mục trên desktop. Header trang "Cài đặt" + tab trên cùng: Hệ thống trả lời · Mô hình · Giao diện.
- Tab "Hệ thống trả lời" mở đầu bằng dải 4 bước theo thứ tự pipeline (Truy xuất → Xếp hạng lại → Ngưỡng tin cậy →
  Sinh câu trả lời). Mỗi bước hiện giá trị nháp đang dùng và chấm "chưa lưu"; bấm bước nào thì form bước đó hiện
  bên dưới, rộng hết khung, kiểu hàng nhãn trái – điều khiển phải. Vẫn một bản nháp, một thanh lưu chung.
- Tab "Mô hình" có thanh chọn loại (ngôn ngữ / nhúng / xếp hạng) thay cho danh mục.
- "Thử với câu hỏi" là ngăn kéo bên phải ở mọi khổ màn hình, mở từ nút ở header.
- Mobile (<1024px) giữ luồng danh sách → trang riêng có nút quay lại; danh sách hiện giá trị đang dùng của 4 bước.

## Phạm vi

- Bao gồm:
  - `frontend/src/SettingsView.jsx`, `frontend/src/ConfigView.jsx`, `frontend/src/ModelsView.jsx` (banner).
  - `frontend/src/settings/SettingsNav.jsx`, mới `frontend/src/settings/PipelineSteps.jsx`,
    mới `frontend/src/settings/pipelineSummary.js` (+ test), xoá `frontend/src/settings/scrollSpy.js` (+ test).
  - `frontend/src/settings/RetrievalTestPanel.jsx` (chỉ comment/hành vi drawer nếu cần).
  - `frontend/src/styles/config.css`, `frontend/src/styles/models.css` (tông banner/card), `frontend/src/styles/tokens.css`
    (2 token cho bước đang chọn).
  - Test: `SettingsView.test.jsx`, `settings/SettingsNav.test.jsx`, `admin/AdminApp.test.jsx`,
    `ConfigView.gate.test.jsx`, `ConfigView.cache.test.jsx` nếu bị ảnh hưởng.
  - Mockup: `docs/design/mockups/settings-pipeline.html`.
- Ngoài phạm vi: backend, API, route/hash (`#settings/<key>` giữ nguyên), nội dung trường cấu hình, form trong
  `ModelKindPanel`, nút "Về mặc định" theo từng bước (có trong mockup nhưng cần định nghĩa mặc định theo `.env`).
- Ràng buộc: không mất bản nháp khi đổi bước/tab; giữ test hiện có về payload, thanh lưu, ngưỡng; theme sáng/tối.

## Tiêu chí nghiệm thu

- [x] AC-01: Desktop ≥1024px không còn cột danh mục; header có tiêu đề "Cài đặt", 3 tab với `aria-current`, hash
  `#settings/<key>` vẫn mở đúng tab/bước/loại mô hình.
- [x] AC-02: Dải 4 bước hiện giá trị theo bản nháp (Top-K, tỷ trọng, reranker, ngưỡng, mô hình, temperature…), chấm
  "chưa lưu" đúng bước; bấm bước gọi `onSectionChange` và chỉ form của bước đó hiển thị.
- [x] AC-03: Đổi bước không mất bản nháp; một thanh lưu chung; payload PUT chỉ gồm trường đã đổi (test cũ vẫn đạt).
- [x] AC-04: Form từng bước dạng hàng nhãn – điều khiển, tự xếp một cột khi khung hẹp; section có header trong card.
- [x] AC-05: "Thử với câu hỏi" mở dạng ngăn kéo ở mọi khổ, Esc/scrim đóng, chỉ có ở tab Hệ thống trả lời.
- [x] AC-06: Tab Mô hình có thanh chọn 3 loại mô hình, mở đúng panel; banner kho mô hình bớt nổi.
- [x] AC-07: Mobile <1024px: `#settings` là danh sách có giá trị 4 bước; mục mở trang riêng có nút quay lại; không có
  thanh cuộn ngang ở 390px.
- [x] AC-08: `npm test` và `npm run build` ở `frontend/` đạt; có ảnh chụp desktop sáng/tối và mobile.

## Tài liệu và phụ thuộc

- Mockup: `docs/design/mockups/settings-pipeline.html` (bản có ảnh màn cũ: artifact riêng của người dùng).
- Task trước: `.agents/tasks/2026-11-15-settings-nav-retrieval-test/`, `2026-11-15-settings-gate-savebar/`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 … S-03 xong; AC-01 … AC-08 đạt (`verification.md`); review `approved` (self_review). Chưa commit.
- Blocker: không có.
- Bước tiếp theo: người dùng xem lại; commit và mở PR vào `dev` khi người dùng đồng ý.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-21T17:22:24+07:00 — claude-agent: người dùng chọn phương án A trong ba mockup. Bỏ nút "Về mặc định" theo
  bước khỏi phạm vi vì mặc định thật nằm ở `.env` máy chủ, giao diện không biết; giữ "Vùng nguy hiểm" hiện có.
- 2026-11-21T17:34:14+07:00 — claude-agent: thêm `tokens.css` vào phạm vi (giữ quy tắc màu thô chỉ ở tokens). Đóng task
  sau khi verification đạt và review `approved`.
