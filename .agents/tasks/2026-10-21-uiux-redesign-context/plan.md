# Plan: 2026-10-21-uiux-redesign-context

## Phân công

### S-01 — Khảo sát mã nguồn frontend và backend

- Agent: `opencode-primary`
- Trạng thái: `done`
- Mục tiêu: lập bản đồ đầy đủ các màn hình, component, token, API để làm căn cứ cho brief; phục vụ `AC-01`, `AC-02`.
- Phạm vi file đọc: `frontend/src/**`, `frontend/package.json`, `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/generation/prompts.py`, `backend/app/guardrails/patterns.py`, `README.md`, `data/`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: bản đồ UI/UX 11 file JSX + audit CSS 12 file + bảng endpoint 22 route (ghi trong `implementation.md`).
- Người nhận: `opencode-primary`.

### S-02 — Viết design brief cho Claude Design

- Agent: `opencode-primary`
- Trạng thái: `done`
- Mục tiêu: viết tài liệu brief tự đủ, bám sát mã nguồn, đúng 3 quyết định đã chốt; phục vụ `AC-01`, `AC-03`, `AC-04`, `AC-05`.
- Phạm vi file sửa: `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` (file mới).
- Phụ thuộc: `S-01`.
- Đầu ra/bàn giao: brief 12 mục + 2 phụ lục.
- Người nhận: `opencode-primary`.

### S-03 — Tự review & bàn giao

- Agent: `opencode-primary`
- Trạng thái: `done`
- Mục tiêu: đối chiếu brief với mã nguồn, kiểm tra tính chính xác của mọi khẳng định có số liệu; phục vụ `AC-02`, `AC-03`.
- Phạm vi file sửa: `verification.md`, `review.md`, và chỉnh sửa brief nếu phát hiện sai.
- Phụ thuộc: `S-02`.
- Đầu ra/bàn giao: kết luận `verification.md` + `review.md`.
- Người nhận: `opencode-primary`.

### S-04 — Viết lại tài liệu context hệ thống (v2.0)

- Agent: `opencode-primary`
- Trạng thái: `done`
- Mục tiêu: viết tài liệu **chỉ mô tả hệ thống**, bỏ toàn bộ mô tả giao diện hiện tại, để Claude Design thiết kế mới từ đầu; phục vụ `AC-06`…`AC-09`.
- Phạm vi file sửa: `docs/design/PTIT-Chatbot-System-Context.md` (file mới), đổi tên `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` → `docs/design/PTIT-Chatbot-UI-UX-Current-State-Audit.md`.
- Phụ thuộc: phản hồi của người dùng sau `S-02`; nội dung dùng lại từ v1.0 nhưng đã bỏ phần mô tả UI.
- Đầu ra/bàn giao: context hệ thống 689 dòng, 10 mục + phụ lục.
- Người nhận: `opencode-primary`.

## Hợp đồng dùng chung

- Không có API/schema/interface nào được thay đổi. Đây là task tài liệu thuần, không đụng mã nguồn ứng dụng.
- File nguồn dùng chung nào được sửa: không có.
- Lượt ghi nội bộ file task: một agent duy nhất (`opencode-primary`) giữ toàn bộ 5 file.

## Phân công kiểm chứng và review

- Verifier: `opencode-primary`; phạm vi kiểm chứng: `AC-01` … `AC-09`.
- Reviewer: `opencode-primary`; phạm vi review: toàn bộ nội dung 2 tài liệu.
- Hình thức review: `self_review` (một agent duy nhất thực hiện toàn bộ).
- Người xử lý phản hồi: `opencode-primary`.

## Thứ tự thực hiện và kiểm chứng

1. `S-01` khảo sát mã nguồn → xong.
2. `S-02` viết brief → xong.
3. `S-03` đối chiếu từng khẳng định có số liệu với mã nguồn, ghi `verification.md`, tự review ghi `review.md`.
4. Coordinator kết luận task khi `review.md` kết luận `approved`.

## Rủi ro và giảm thiểu

- Rủi ro: brief khẳng định sai số liệu/số dòng → giảm thiểu bằng `AC-02` bắt buộc mọi khẳng định có đường dẫn + số dòng, và kiểm chứng lại từng mục ở `S-03`.
- Rủi ro: brief quá dài, Claude Design không đọc hết → giảm thiểu bằng cấu trúc 12 mục + mục "Cách dùng tài liệu này" ở đầu chỉ dẫn rõ thứ tự đọc theo vai trò.
- Rủi ro: đề xuất API mở rộng bị hiểu là bắt buộc implement ngay → brief ghi rõ đây là phần "thiết kế UI trước, backend sau", kèm cột fallback UI.
