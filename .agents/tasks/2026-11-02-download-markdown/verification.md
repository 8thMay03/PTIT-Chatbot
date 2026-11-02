# Verification: 2026-11-02-download-markdown

- Verifier: `opencode`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree trên branch `feat/download-markdown` (backend `routes.py`, frontend `documents.js`/`DatasetView.jsx`/`DocumentView.jsx`).
- Môi trường: Windows, Python 3.11 `.venv`, Node/npm (Vite build + vitest).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: opencode / 2026-11-02T10:20:00+07:00.
- Loại: test tự động + script thủ công (TestClient).
- Thư mục chạy: `backend`.
- Lệnh / thao tác:
  - `.venv\Scripts\python -m pytest tests/test_document_api.py -q`
  - script login admin rồi `GET /api/documents/doc-md/markdown/download` (mock `get_document_with_chunk_count`), `GET .../missing/...`, `GET .../legacy/...` (parsed_text None)
  - `.venv\Scripts\python -m pytest tests/test_admin_auth.py::test_every_api_route_is_public_or_requires_admin tests/test_admin_auth.py::test_public_api_routes_all_exist -q`
- Kỳ vọng: endpoint 200 với đúng `parsed_text`, header attachment `.md` + `text/markdown; charset=utf-8`; 404 thiếu doc; 409 chưa có Markdown; route có `require_admin`; test cũ pass.
- Kết quả thực tế: `test_document_api.py` 25 passed; script: 200 `policy.md` (`attachment; filename="policy.md"; filename*=UTF-8''policy.md`, `text/markdown; charset=utf-8`, `nosniff`, body `# Chinh sach...`), missing 404, legacy 409; admin route scan 2 passed.
- Trạng thái: `passed`.
- Bằng chứng: log pytest + output script trong implementation S-01.

### V-02 — AC-02

- Người thực hiện / thời gian: opencode / 2026-11-02T10:28:00+07:00.
- Loại: kiểm tra tĩnh + build/test tự động.
- Thư mục chạy: `frontend`.
- Lệnh / thao tác:
  - đọc `DatasetView.jsx` (nút `FileDown`, `downloadMarkdown`, disabled `rowBusy || !canEditMarkdown`, toast `NO_MARKDOWN_HINT`/lỗi)
  - đọc `DocumentView.jsx` (nút "Tải Markdown", state `downloadingMarkdown`, disabled tương tự)
  - đọc `api/documents.js` (`markdownFile` dùng `responseType: blob`, `markdownFileUrl`)
  - `npm run build`, `npm test -- --run`
- Kỳ vọng: có nút tải Markdown riêng, chỉ bật khi có Markdown; tải gốc giữ nguyên; build/test pass.
- Kết quả thực tế: nút `FileDown` trong bảng trước nút `Download` gốc (title "Tải xuống bản Markdown..." vs "Tải xuống file gốc..."); màn chi tiết có nút "Tải Markdown"; `npm run build` pass (~2.2s); `npm test` 22 files / 168 tests passed.
- Trạng thái: `passed`.
- Bằng chứng: diff `git diff --stat -w` (124 insertions), log build/test.

### V-03 — AC-03

- Người thực hiện / thời gian: opencode / 2026-11-02T10:28:00+07:00.
- Loại: test hồi quy.
- Thư mục chạy: `backend`, `frontend`.
- Lệnh / thao tác: `pytest tests/test_document_api.py -q`; `pytest test_admin_auth... -q`; `npm test -- --run`; `npm run build`.
- Kỳ vọng: không vỡ API cũ, không vỡ UI cũ.
- Kết quả thực tế: backend 25 passed + admin scan 2 passed; frontend 168 passed + build pass.
- Trạng thái: `passed`.
- Bằng chứng: log như V-01/V-02.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Không có lỗi. Chưa chạy E2E thủ công trên trình duyệt với backend thật + file thật (chỉ TestClient mock và build/test); lý do: môi trường không có dữ liệu seed sẵn, logic download đã được kiểm tra ở mức API + client.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03 (có bằng chứng).
- Tiêu chí chưa đạt/chưa xác minh: không có (E2E trình duyệt là phần bổ sung, không bắt buộc).
- Đề xuất: chuyển reviewer self_review rồi đóng task; commit branch `feat/download-markdown` sau khi review approved.
