# Implementation: 2026-10-25-rag15-llamaparse-parser

## Tổng quan triển khai

S-01…S-05, S-07 xong trên working tree nhánh `feat/rag15-llamaparse-parser` (tách từ `dev` tại `af2d2b7`, **chưa commit**). RAG-06 đã nằm trong `dev` (`87e5510`…`1048398`), nhánh `feat/rag06-article-clause-chunking` không có commit nào ngoài `dev`, nên S-04 sửa `pipeline.py` không xung đột. S-06 làm xong phần Docling (đo PDF D26 bằng Docling + khôi phục index); phần LlamaParse đang chờ `LLAMA_CLOUD_API_KEY` trong `.env` local.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.
- Đã làm: tải wheel `llama-cloud` 2.19.0 (bản mới nhất trên PyPI) vào scratchpad, đọc mã nguồn (`resources/parsing.py`, `types/parsing_get_response.py`, `types/parsing_create_params.py`, `_client.py`, `_exceptions.py`, `_polling.py`). Gói `llama-parse` cũ đã deprecated (hết hỗ trợ 2026-05-01).
- Kết quả chốt:
  - Client: `llama_cloud.LlamaCloud(api_key=, base_url=, timeout=, max_retries=)`; dùng được làm context manager. SDK tự retry 408/409/429/5xx và lỗi kết nối (`max_retries`, mặc định của SDK là 5; task dùng `LLAMAPARSE_MAX_RETRIES=2`). Timeout request mặc định của SDK là 60 giây — quá ngắn để upload PDF D26 (37 MB), nên client dùng chung `LLAMAPARSE_TIMEOUT_SECONDS`.
  - Gọi một lần: `client.parsing.parse(tier=, version=, upload_file=(name, handle), expand=["markdown"], processing_options={"ocr_parameters": {"languages": ["vi"]}}, output_options={"markdown": {"tables": {"output_tables_as_markdown": True, "compact_markdown_tables": True}}}, client_name=, timeout=<giây chờ poll>)` → `ParsingGetResponse`. Hàm này = `create` + `wait_for_completion` + `get`.
  - Tier: `fast | cost_effective | agentic | agentic_plus`; `version="latest"` hoặc ngày cố định.
  - Kết quả: `result.markdown.pages[]` gồm `page_number`, `success`, `markdown` (header/footer trả riêng ở `header`/`footer`) hoặc trang lỗi (`success=False`, `error`). `result.job.usage.credits` cho biết số credit đã dùng.
  - Lỗi: `PollingTimeoutError`, `PollingError` (job FAILED/CANCELLED), `APIStatusError` (có `status_code`; con: `AuthenticationError` 401, `RateLimitError` 429…), `APIConnectionError` (con: `APITimeoutError`). Đều export ở `llama_cloud`.
  - Giá (trang pricing LlamaParse v2): fast 1, cost_effective 3, agentic 10, agentic_plus 45 credit/trang; parse lại cùng file trong 48 giờ được miễn phí.
- Quyết định: mặc định `LLAMAPARSE_TIER=cost_effective` vì ngân sách người dùng duyệt là 1000 credit: PDF D26 268 trang × 3 = 804 credit; `agentic` sẽ cần 2680. Pin `llama-cloud>=2.19.0,<3`.
- Kiểm tra: sau khi cài SDK vào `.venv`, `inspect.signature(...).bind(...)` xác nhận các kwargs của `LlamaCloud(...)` và `parsing.parse(...)` trong `llamaparse.py` khớp SDK 2.19.0; khởi tạo client với key giả không lỗi (không gọi mạng).

### S-02 — claude-code

- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.
- Đã làm: `config.py` thêm `LLAMAPARSE_ENABLED`, `LLAMA_CLOUD_API_KEY`, `LLAMAPARSE_BASE_URL`, `LLAMAPARSE_TIER` (cost_effective), `LLAMAPARSE_VERSION` (latest), `LLAMAPARSE_LANGUAGE` (vi), `LLAMAPARSE_TIMEOUT_SECONDS` (900), `LLAMAPARSE_MAX_RETRIES` (2). `parsers/llamaparse.py` mới: `LlamaParseParser`, `llamaparse_available()`, `convert_with_llamaparse()`, `_parse_remote()` (import SDK lười, map lỗi sang `DocumentParseError` tiếng Việt, không đưa body response vào thông báo), `_markdown_from_result()` (nối trang theo `page_number`, bỏ header/footer; trang lỗi → bỏ qua + cảnh báo, mọi trang lỗi → lỗi), `_postprocess_markdown()` (bỏ tham chiếu ảnh, gộp dòng trống), cache `converted/llamaparse/<sha256(_CONVERTER_VERSION|tier|LLAMAPARSE_VERSION|language|file bytes)>.md`.
- File thay đổi: `backend/app/core/config.py`, `backend/app/parsers/llamaparse.py` (mới), `backend/tests/test_llamaparse_parser.py` (mới, 15 test, SDK giả qua `sys.modules`).
- Quyết định lệch plan: (1) không tự viết retry/backoff — dùng retry có sẵn của SDK qua `max_retries`; (2) bỏ lock tuần tự hóa: dịch vụ cloud không tranh tài nguyên máy như Docling, còn nạp lại toàn kho vốn đã chạy tuần tự; (3) trang lỗi riêng lẻ được bỏ qua kèm cảnh báo thay vì làm hỏng cả tài liệu, vì lỗi một trang trên sổ tay 268 trang sẽ chặn cả tài liệu.
- Kiểm tra: V-02, V-03.

### S-03 — claude-code

- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.
- Đã làm: `parsers/__init__.py` dựng registry qua `build_registry()` (Text, Docling, rồi LlamaParse khi `llamaparse_available()`), thêm `get_parser_name()` và `resolve_parser_name()`; extra `llamaparse = ["llama-cloud>=2.19.0,<3"]`; Dockerfile cài `".[docling,llamaparse]"`; `.env.example` thêm khối cấu hình (mặc định tắt, key trống).
- File thay đổi: `backend/app/parsers/__init__.py`, `backend/pyproject.toml`, `backend/Dockerfile`, `.env.example`, `backend/tests/test_parsers.py`.
- Kiểm tra: V-01, V-05.

### S-04 — claude-code

- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.
- Đã làm:
  - `SourceDocument.parser_name` (mặc định `None`); `_records_for_document` ghi `documents.metadata["parser"]`.
  - `ingest_upload` ghi parser mặc định; `ingest_path` ghi parser được chọn.
  - `load_documents(data_dir, parser_for=None)`: `parser_for(path)` trả parser đã lưu; `resolve_parser_name` fallback về mặc định + cảnh báo nếu parser không còn đăng ký.
  - `build_chunks()` đọc map `source_path → parser` bằng `repositories.get_document_parsers()` rồi truyền `parser_for`.
  - `routes.get_document` và `uploads.read_preview(..., parser_name=)` đọc bằng parser đã lưu (`convert=False`).
- File thay đổi: `backend/app/ingestion/{loaders,pipeline,uploads}.py`, `backend/app/api/routes.py`, `backend/app/db/repositories.py`, `backend/tests/{test_document_pipeline,test_document_api,test_parsers}.py` (2 lambda `read_preview` trong `test_document_api.py` nhận thêm `**_`).
- Giới hạn đã biết: map parser khóa theo `source_path` lưu trong DB; nếu file bị di chuyển trước khi nạp lại toàn kho, tài liệu đó dùng parser mặc định (giống cách ID đang phụ thuộc đường dẫn). Endpoint parse không truyền `parser_name` vẫn dùng mặc định như trước.
- Kiểm tra: V-04.

### S-05 — claude-code

- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.
- Đã làm: `PARSER_DETAILS.llamaparse` (tiêu đề, mô tả có ghi chú gửi file lên LlamaCloud + tốn credit) và badge "Cloud" dùng lại class `.parser-badge`.
- File thay đổi: `frontend/src/components/ParserSelectionModal.jsx`.
- Kiểm tra: V-06 (build). Chưa xem trực quan modal trên trình duyệt.

### S-06 — claude-code

- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.
- Quyết định người dùng (`2026-10-25`): (1) được phép gửi tài liệu lên LlamaCloud; (2) sẽ cung cấp key; (3) ngân sách 1000 credit.
- Trạng thái index trước khi đo (ghi lại để khôi phục): 2 tài liệu — `19a636282f29…` `data/processed/Sổ tay sinh viên D26 _1_ _1_.md` 1203 chunk (index RAG-06) và `e0997dd268c1…` `data/Sổ tay sinh viên D26 _1_.pdf` 977 chunk (người dùng upload lúc `2026-10-25T11:18+07:00`, Docling). Tổng 2180 chunk / 1387 parent.
- Đã làm (phần Docling):
  - Script `documents/rag-eval/rag-15/experiments/reingest_documents.py` (thay index bằng các file chỉ định, mỗi file một parser) và `restore_index.py` (khôi phục 2 tài liệu trên, giữ nguyên ID).
  - Re-ingest riêng PDF D26 bằng Docling (đọc cache, không chạy lại Docling): 977 chunk / 638 parent, `check_chunks --db` sạch, corpus fingerprint `deca865260bc…`. Eval → `documents/rag-eval/rag-15/docling_pdf_hybrid.json`, `docling_pdf_bm25.json`.
  - Khôi phục index bằng `restore_index.py`: ID, `source_path`, số chunk khớp trạng thái trước (1203 + 977). Khác biệt còn lại: `metadata.parser` có thêm ở cả hai bản ghi (khóa mới của task này); `content_hash` của bản PDF đổi `a7e90d15…` → `84b80c0a…` dù số chunk giống nhau — bản upload gốc nhiều khả năng do server chạy mã cũ hơn tạo ra; trường này chỉ dùng để phát hiện thay đổi.
- Còn lại (chờ key): smoke test PDF 2 trang (`TB hoan thien thu tuc dau khoa hoc.pdf`, ~6 credit) → parse PDF D26 bằng LlamaParse qua `POST /api/documents/e0997dd268c1…/parse?parser_name=llamaparse` (~804 credit; đồng thời kiểm thủ công AC-01/AC-04) → re-ingest riêng bản LlamaParse, đo hybrid/bm25, `check_structure`, `check_chunks` → `restore_index.py` → viết `documents/rag-eval/rag-15/README.md`. Dự kiến tổng ~810 credit, không parse D21 (201 trang) để giữ trong ngân sách.

### S-07 — claude-code

- Cập nhật lúc: `2026-10-25T12:15:34+07:00`.
- Đã làm: `README.md` thêm mục "LlamaParse (tùy chọn)" (cài extra, biến môi trường, chọn trong modal, cache, lỗi, region EU, giá tham khảo), sửa dòng mô tả `parsers/` và đoạn về chọn parser (thay câu cũ "giao diện upload vẫn dùng parser mặc định" bằng mô tả parse lại + lưu `metadata.parser`).
- File thay đổi: `README.md`.

## Trao đổi giữa agents

### MSG-claude-code-001

- Lúc: `2026-10-25T12:15:34+07:00`.
- Từ: `claude-code`; đến: coordinator task `2026-10-25-rag06-article-clause-chunking`.
- Nhiệm vụ: `S-04`.
- Loại: `update`.
- Tham chiếu: không có.
- Nội dung: `IngestionPipeline.build_chunks()` giờ gọi `load_documents(data_dir, parser_for=...)`. Script đã commit `documents/rag-eval/rag-06/experiments/reingest_single_document.py` thay `pipeline.load_documents` bằng `load_single(_data_dir)` (một tham số) nên sẽ lỗi `TypeError` nếu chạy lại. RAG-15 không sửa file của RAG-06; script tương đương của RAG-15 (`rag-15/experiments/reingest_documents.py`) nhận `**_kwargs`.
- Hành động mong muốn: nếu cần chạy lại script RAG-06, đổi chữ ký thành `load_single(_data_dir, **_kwargs)`.

## Bàn giao

Chưa có bàn giao.
