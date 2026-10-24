# Task: Chuẩn bị bối cảnh hệ thống cho redesign toàn hệ thống PTIT Chatbot

- ID: `2026-10-21-uiux-redesign-context`
- Trạng thái: `done`
- Coordinator: `opencode-primary`
- Người yêu cầu: chủ repo (kế hoạch redesign UI/UX toàn hệ thống, cần context để đưa cho Claude Design)
- Tạo lúc: `2026-10-21T00:00:00+07:00`
- Cập nhật lúc: `2026-10-21T00:00:00+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng cần redesign lại UI/UX của toàn bộ hệ thống PTIT RAG Chatbot và cần một tài liệu bối cảnh đủ đầy đủ để đưa (paste) cho Claude Design làm đầu vào thiết kế.

**Bổ sung (vòng 2):** bản v1.0 mô tả quá chi tiết giao diện hiện tại (bố cục, class, token, lỗi CSS kèm số dòng) → Claude Design chỉ "sửa lại" giao diện cũ thay vì thiết kế mới. Người dùng yêu cầu: *"tôi chỉ cần context của hệ thống thôi"*.

Kết quả mong muốn sau vòng 2: một tài liệu **chỉ mô tả hệ thống** (sản phẩm, người dùng, phạm vi chức năng, mô hình dữ liệu, trạng thái, hợp đồng API, ràng buộc), **không** mô tả giao diện hiện tại, để Claude Design thiết kế từ đầu.

## Đầu ra

| File | Vai trò | Đưa cho ai |
|---|---|---|
| `docs/design/PTIT-Chatbot-System-Context.md` | **Bối cảnh hệ thống** — đầu vào cho Claude Design | Claude Design |
| `docs/design/PTIT-Chatbot-UI-UX-Current-State-Audit.md` | Rà soát hiện trạng giao diện (v1.0) — tài liệu tham chiếu khi implement | Agent implement redesign |

## Phạm vi

- Bao gồm: khảo sát toàn bộ frontend (`src/*.jsx`, `src/components/`, `src/lib/`, `src/styles/`) và API backend (`backend/app/api/`), tổng hợp thành 2 tài liệu tại `docs/design/`.
- Ngoài phạm vi: không sửa mã nguồn ứng dụng; không implement redesign; không đổi backend; không viết test.
- Ràng buộc: tài liệu phải trung thực với trạng thái mã nguồn — mọi khẳng định về hạn chế phải kèm đường dẫn file/số dòng; không bịa số liệu hay trạng thái.

## Quyết định đã chốt với người dùng

| Quyết định | Lựa chọn |
|---|---|
| Phạm vi redesign | Cả hai: thiết kế UI trước, backend sau (có mục API mở rộng + hành vi fallback khi API chưa có) |
| Hướng thị giác | "Học vụ hiện đại" — nền trung tính, sidebar sáng thay panel maroon, màu nhấn dùng cho hành động chính, giữ maroon làm màu nhận diện |
| Trọng tâm & độ sâu | Cân bằng, brief đầy đủ, tiếng Việt, giữ nguyên chuỗi UI tiếng Việt làm ví dụ |
| **Mức độ mô tả giao diện cũ** | **Vòng 2: bỏ hẳn.** Tài liệu dùng cho Claude Design chỉ mô tả hệ thống; mô tả giao diện cũ tách sang tài liệu tham chiếu riêng |

## Tiêu chí nghiệm thu

- [x] AC-01: Brief bao phủ đủ 12 mục: sản phẩm, kiến trúc → hệ quả UI, người dùng, ràng buộc, bản đồ màn hình, đặc tả từng màn, design system hiện tại, nợ UI có bằng chứng, hướng thị giác, a11y, giọng văn, API, đầu ra mong muốn. *(v1.0 — đã thay bằng AC-06…AC-09 ở vòng 2)*
- [x] AC-02: Mọi phát biểu về hạn chế kỹ thuật có bằng chứng cụ thể (đường dẫn file + số dòng hoặc số liệu đếm được).
- [x] AC-03: Brief tự đủ — người đọc không cần mở repo để hiểu yêu cầu thiết kế.
- [x] AC-04: Tôn trọng ràng buộc kỹ thuật đã xác nhận (không thêm dependency, CSS thuần, hash routing, light/dark/system, không phá API).
- [x] AC-05: Nêu rõ 3 trạng thái thiết kế song song cho các tính năng chỉ tồn tại trong phiên (API chưa có) — đúng quyết định "thiết kế UI trước, backend sau".
- [x] AC-06: Tài liệu context **không mô tả giao diện hiện tại** — không có wireframe, không có bố cục màn, không có class/component/token của bản cũ, không có danh sách bug CSS.
- [x] AC-07: Tài liệu context vẫn đủ để thiết kế: đủ thông tin về sản phẩm, người dùng, phạm vi chức năng, mô hình dữ liệu, trạng thái, hợp đồng API, ràng buộc.
- [x] AC-08: Có câu lệnh tường minh yêu cầu thiết kế **mới từ đầu**, không kế thừa bố cục cũ.
- [x] AC-09: Tách 2 vai trò rõ ràng — tài liệu đưa cho Claude Design vs tài liệu tham chiếu khi implement.

## Tài liệu phụ thuộc

- Không có tài liệu/issue/task liên quan tồn tại.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng kiểm chứng trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: v1.0 (audit hiện trạng, 870 dòng) → v2.0 (context hệ thống, 689 dòng) là tài liệu chính để đưa cho Claude Design; v1.0 được đổi tên thành tài liệu tham chiếu khi implement.
- Blocker: không có.
- Bước tiếp theo: người dùng đưa `docs/design/PTIT-Chatbot-System-Context.md` cho Claude Design; sau khi có đầu ra thiết kế thì lập task implement riêng.

## Lịch sử quyết định phạm vi/trạng thái

- `2026-10-21T00:00:00+07:00` — `opencode-primary`: khảo sát mã nguồn frontend (10 file JSX + 12 file CSS) và API backend (`routes.py`, `schemas.py`), đọc `README.md`, `prompts.py`, `guardrails/patterns.py`.
- `2026-10-21T00:00:00+07:00` — `opencode-primary`: hỏi và chốt 3 quyết định về phạm vi, hướng thị giác, trọng tâm (xem bảng ở trên).
- `2026-10-21T00:00:00+07:00` — `opencode-primary`: tạo v1.0 `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md`.
- `2026-10-21T00:00:00+07:00` — `opencode-primary`: kiểm chứng + đính chính 5 số liệu sai ở §7.2 (31 màu / 15 bo góc / 19 shadow / 85% spacing / 19 token chết), review `approved`.
- `2026-10-21T00:00:00+07:00` — `opencode-primary`: người dùng phản hồi v1.0 quá mô tả giao diện cũ → tạo v2.0 `docs/design/PTIT-Chatbot-System-Context.md` (context hệ thống thuần), đổi tên v1.0 thành `PTIT-Chatbot-UI-UX-Current-State-Audit.md` (tham chiếu khi implement).
