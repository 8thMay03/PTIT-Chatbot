# Implementation: 2026-10-21-uiux-redesign-context

## Tổng quan triển khai

Task tài liệu thuần: **không sửa mã nguồn ứng dụng**. Đầu ra duy nhất là một design brief tại `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md`, dùng làm đầu vào cho Claude Design.

## Nhiệm vụ theo kế hoạch

### S-01 — Khảo sát mã nguồn frontend và backend — `opencode-primary`

- Cập nhật lúc: `2026-10-21T00:00:00+07:00`.
- Đã làm: đọc trực tiếp `frontend/src/App.jsx`, `ChatView.jsx`, `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `frontend/src/styles/tokens.css`, `README.md`, `backend/app/generation/prompts.py`, `backend/app/guardrails/patterns.py`; dùng 2 subagent `explore` để map 11 file JSX còn lại (DatasetView, DocumentView, ConfigView, ModelsView, SettingsView, 4 component, lib/format.js, lib/theme.js) và audit 12 file CSS.
- File thay đổi: không có (chỉ đọc).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: phát hiện 2 điểm ảnh hưởng trực tiếp tới thiết kế → đưa vào brief:
  1. `ConfigView` và `ModelsView` cùng `PUT /api/config` nhưng có 2 luồng lưu độc lập → brief yêu cầu thiết kế thống nhất trạng thái cấu hình.
  2. Backend **không** có `PATCH /documents/{id}` và không có endpoint bật/tắt chunk → brief yêu cầu thiết kế 2 trạng thái song song (có API / fallback phiên).
- Kiểm tra đã chạy: không có kiểm thử tự động (task tài liệu); kiểm chứng thực tế ở `S-03`.
- Cần lỗi/blocker: không có.

### S-02 — Viết design brief — `opencode-primary`

- Cập nhật lúc: `2026-10-21T00:00:00+07:00`.
- Đã làm: viết `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md`.
- File thay đổi: `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` (file mới).
- Cấu trúc brief (12 mục + 2 phụ lục):
  - §0 Cách dùng tài liệu này (chỉ dẫn thứ tự đọc theo vai trò)
  - §1 Tổng quan sản phẩm + kiến trúc RAG → bảng hệ quả UI + tech stack + kho tài liệu thực tế
  - §2 Người dùng (2 nhóm) + hành trình then chốt
  - §3 Ràng buộc bắt buộc (10 điều)
  - §4 Kiến trúc thông tin: khung app ASCII, bảng route, bản đồ 7 màn chi tiết, component inventory
  - §5 Đặc tả từng màn S-1…S-7 (mục tiêu · bắt buộc có · vấn đề hiện tại · hướng thiết kế gợi ý)
  - §6 Design system hiện tại (2 tầng token, bảng màu, thang đo, breakpoint, danh mục class)
  - §7 Nợ UI chia 3 nhóm: A (12 lỗi hiển thị/a11y) · B (14 nợ token/CSS) · C (18 nợ logic/hành vi)
  - §8 Hướng thị giác "học vụ hiện đại" (nguyên tắc, bảng màu, typography, bo góc, spacing, chuyển động, mật độ, bố cục, 9 component mới)
  - §9 Accessibility (WCAG 2.2 AA)
  - §10 Giọng văn (của trợ lý / của UI / chuỗi cố định do backend / mẫu thông báo lỗi)
  - §11 API (22 endpoint + 22 hợp đồng tương thích + 8 endpoint đề xuất)
  - §12 Đầu ra mong muốn từ Claude Design (bắt buộc / nên / không cần)
  - Phụ lục A: bảng màn hình ↔ file JSX/CSS/API
  - Phụ lục B: chuỗi UI tiếng Việt quan trọng theo từng màn
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: áp dụng 3 quyết định đã chốt (thiết kế UI trước backend sau; hướng "học vụ hiện đại"; brief cân bằng đầy đủ, tiếng Việt).
- Kiểm tra đã chạy: xem `verification.md`.
- Cần lỗi/blocker: không có.

### S-03 — Tự review & bàn giao — `opencode-primary`

- Cập nhật lúc: `2026-10-21T00:00:00+07:00`.
- Đã làm: đối chiếu từng khẳng định có số dòng/số liệu trong brief với mã nguồn; đo lại các thống kê bằng script đếm trực tiếp trên `frontend/src/styles/*.css`.
- File thay đổi: `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` (đính chính số liệu ở §7.1, §7.2), `verification.md`, `review.md`.
- **Đính chính sau kiểm chứng:**
  - `rgba()` hard-code ngoài `tokens.css`: 37 → **31** (đo trực tiếp; hex thô = 0).
  - Shadow hard-code: 13 → **19 giá trị raw** trong 43 khai báo `box-shadow`.
  - Bo góc ad-hoc: 14 → **15 giá trị raw** (22 giá trị distinct gồm cả 6 dạng dùng token).
  - Spacing: 270/311 (87%) → **241/282 (85%)**.
  - Token chết: 22 → **19** (đo bằng regex có lookahead để tránh `--space-1` khớp `--space-10`).
  - Bổ sung selector trùng chưa liệt kê: `.td-chunks` ×2, `.chunk-card-item.selected` ×2.
  - Bổ sung `chat.css:515` vào danh sách gradient hard-code (6 chỗ, không phải 5).
  - Bổ sung số dòng cụ thể cho `.toast-close` (`components.css:164-169`) và bảng→card (`responsive.css:167-181`).
- Kiểm tra đã chạy: xem `verification.md`.
- Cần lỗi/blocker: không có.

### S-04 — Viết lại tài liệu context hệ thống (v2.0) — `opencode-primary`

- Cập nhật lúc: `2026-10-21T00:00:00+07:00`.
- Đã làm: viết lại tài liệu theo phản hồi của người dùng — bỏ toàn bộ mô tả giao diện hiện tại, chỉ giữ lại **context hệ thống**.
- File thay đổi:
  - `docs/design/PTIT-Chatbot-System-Context.md` (file mới, 689 dòng) — tài liệu đưa cho Claude Design.
  - `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` → đổi tên thành `docs/design/PTIT-Chatbot-UI-UX-Current-State-Audit.md` (không nội dung đổi, 870 dòng) — tài liệu tham chiếu khi implement.
- **Đã bỏ khỏi tài liệu context** (vốn là nguyên nhân Claude Design chỉ "sửa lại" giao diện cũ):
  - §4.1 sơ đồ ASCII khung ứng dụng; §4.3 bản đồ 7 màn chi tiết với nhãn/class hiện tại; §4.4 component inventory theo file.
  - §5 "Vấn đề hiện tại cần giải quyết" của từng màn (7 nhóm, ~40 mục).
  - §6.2–6.5 toàn bộ design system hiện tại: bảng màu, thang đo, breakpoint, danh mục class CSS.
  - §7.1–7.2 bảng lỗi a11y/CSS kèm đường dẫn file + số dòng và số liệu thống kê.
  - Phụ lục A (bảng màn hình ↔ file) và danh sách chuỗi UI hiện tại.
- **Đã viết lại thành** (cùng ý, nhưng ở góc nhìn hệ thống):
  - §1.1 ba nguyên tắc sản phẩm + hệ quả bắt buộc cho giao diện (thay cho mục "vấn đề UI").
  - §1.2 bảng "trạng thái hệ thống → giao diện cần biểu diễn" (thay cho "hệ quả trực tiếp tới UI").
  - §2.3 bảng "nhu cầu người dùng → khả năng hệ thống → giao diện phải làm được".
  - §3 **phạm vi chức năng** (8 nhóm năng lực) — ghi rõ đây là phạm vi chức năng, không phải màn hình.
  - §4 mô hình dữ liệu đầy đủ (`Document`, `Chunk`, `Conversation`, `Message`, `Source`, `FullConfigResponse`).
  - §5 trạng thái hệ thống phải biểu diễn (vòng đời câu hỏi, trạng thái nền, trạng thái danh sách, trạng thái thao tác).
  - §6 hợp đồng API + hợp đồng streaming NDJSON + ràng buộc dữ liệu.
  - §7 giới hạn đã biết của sản phẩm (đóng vai trò "bối cảnh để thiết kế hợp lý", không phải danh sách bug).
  - §8 hướng thiết kế + §8.3 danh sách những gì Claude Design **tự do** quyết định.
  - §9 a11y, giọng trợ lý, giọng giao diện, mẫu lỗi.
  - §10 đầu ra mong muốn, trong đó ưu tiên #1 là **kiến trúc thông tin mới**.
- Thêm câu lệnh tường minh ở đầu tài liệu: *"Tài liệu này mô tả HỆ THỐNG, không mô tả giao diện hiện tại… Bạn hoàn toàn tự do đề xuất kiến trúc thông tin, bố cục và hệ thống giao diện."*
- Kiểm tra đã chạy: xem `verification.md` V-06.
- Cần lỗi/blocker: không có.

## Trao đổi giữa agents

Không có agent nào khác; một mình thực hiện toàn bộ. Không phát sinh trao đổi.

### HANDOFF-opencode-primary-002 — S-04

- Từ / đến: `opencode-primary` → người dùng → Claude Design.
- Phần việc hoàn tất: viết lại tài liệu thành **context hệ thống thuần**, tách mô tả giao diện cũ sang tài liệu tham chiếu riêng.
- File/branch/commit/patch: `docs/design/PTIT-Chatbot-System-Context.md` (mới); `docs/design/PTIT-Chatbot-UI-UX-Current-State-Audit.md` (đổi tên từ v1.0).
- Kiểm chứng: xem `verification.md` V-06.
- Review: xem `review.md` (vòng 2 — kết luận `approved` trên bản v2.0).
- Hạn chế / cần lỗi:
  - Tài liệu context **cố ý không** mô tả giao diện cũ → khi implement sẽ phải đọc thêm `Current-State-Audit.md` để biết class/file hiện tại.
  - `§3` là phạm vi chức năng, không phải danh sách màn hình → khi implement phải tự quyết định bố cục theo thiết kế Claude Design trả về.
- Bước tiếp theo: người dùng dán `docs/design/PTIT-Chatbot-System-Context.md` vào Claude Design.
- Phần hỏi người nhận: nếu Claude Design đề xuất thêm endpoint ngoài §6.5 hoặc đổi hệ màu nhận diện PTIT, cần xác nhận trước khi implement.

## Bàn giao

### HANDOFF-opencode-primary-001 — S-01, S-02, S-03

- Từ / đến: `opencode-primary` / người dùng (kế hoạch redesign) và Claude Design (công cụ nhận brief).
- Phần việc hoàn tất: khảo sát toàn bộ frontend + API; viết design brief 12 mục + 2 phụ lục; kiểm chứng và đính chính toàn bộ số liệu trong brief.
- File/branch/commit/patch: `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` (file mới, chưa commit).
- Kiểm chứng: xem `verification.md` (V-01 … V-05, tất cả `passed`).
- Review: xem `review.md` (kết luận `approved`, self_review).
- Hạn chế / cần lỗi:
  - Brief **không** thay thế việc đọc mã nguồn khi implement; nếu Claude Design đề xuất token mới, cần đối chiếu §6.2 trước khi ghi đè.
  - §11.3 (API đề xuất) là **đề xuất**, chưa phải hợp đồng đã duyệt — backend chưa implement.
  - Số liệu đếm được trong §7.2 phản ánh trạng thái tại thời điểm 2026-10-21; cần đo lại nếu mã nguồn CSS thay đổi trước khi triển khai.
- Bước tiếp theo: người dùng dán nội dung `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` vào Claude Design; sau đó chốt đầu ra thiết kế và lập task implement theo `.agents/README.md`.
- Phần hỏi người nhận: nếu Claude Design đề xuất thêm endpoint ngoài §11.3 hoặc đổi hệ màu nhận diện PTIT, cần xác nhận trước khi implement.
