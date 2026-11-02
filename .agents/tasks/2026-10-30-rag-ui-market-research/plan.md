# Plan: 2026-10-30-rag-ui-market-research

## Phân công

### S-01 — Khảo sát hiện trạng giao diện chat

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: liệt kê điểm mạnh và vấn đề `H-*` có bằng chứng; phục vụ `AC-01`.
- Phạm vi file được sửa: `docs/design/assets/current-*.png` (ảnh mới).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: §2 của tài liệu.
- Người nhận: `claude-agent`.

### S-02 — Khảo sát sản phẩm RAG trên thị trường

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: bảng so sánh mẫu thiết kế, ghi chú từng sản phẩm, nguồn; phục vụ `AC-02`.
- Phạm vi file được sửa: `docs/design/RAG-UI-Market-Research.md` §3–§4, §10.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: §3, §4, §10.
- Người nhận: `claude-agent`.

### S-03 — Đề xuất, mockup, lộ trình

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: đề xuất `D-*`, thay đổi API, lộ trình, phối hợp, câu hỏi mở, mockup; phục vụ `AC-03`, `AC-04`, `AC-05`.
- Phạm vi file được sửa: `docs/design/RAG-UI-Market-Research.md` §0, §5–§9; `docs/design/mockups/chat-proposed.html`;
  `docs/design/assets/proposed-chat-desktop.png`.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: tài liệu hoàn chỉnh.
- Người nhận: người dùng.

## Hợp đồng dùng chung

- Không áp dụng (chỉ tài liệu). Đề xuất API ở §6 tài liệu là đề xuất, chưa phải hợp đồng đã chốt.
- Lượt ghi năm file task: `claude-agent` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: `AC-01` … `AC-05`.
- Reviewer: `claude-agent`; phạm vi: toàn bộ file trong phạm vi task.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 và S-02 làm song song.
2. S-03 sau khi có S-01, S-02.
3. Verifier đối chiếu tài liệu với mã nguồn và ảnh.
4. Self-review, sửa nhận xét nếu có.
5. Coordinator chuyển `in_review` chờ người dùng; `done` sau khi người dùng chấp nhận tài liệu.

## Rủi ro và điều chỉnh kế hoạch

- Một số trang (arxiv.org, aiuxplayground.com) bị chặn trong môi trường → dùng trích đoạn kết quả tìm kiếm, ghi
  rõ trong §1 tài liệu.
- D-08 trùng file với task `2026-10-28-landing-user-auth` → đã ghi trong §8, triển khai sau khi task đó merge.
