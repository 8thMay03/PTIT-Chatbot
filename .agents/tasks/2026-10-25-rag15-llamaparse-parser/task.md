# Task: RAG-15 · Tích hợp LlamaParse làm thêm một phương pháp parse PDF/DOCX (bên cạnh Docling)

- ID: `2026-10-25-rag15-llamaparse-parser`
- Trạng thái: `in_progress`
- Coordinator: `claude-code`
- Người yêu cầu: người dùng (phiên Claude Code 2026-10-25; nguồn: trang Notion "RAG-15")
- Tạo lúc: `2026-10-25T11:29:49+07:00`
- Cập nhật lúc: `2026-10-25T12:15:34+07:00`

## Yêu cầu và kết quả mong muốn

Bổ sung LlamaParse (dịch vụ cloud của LlamaIndex) như **một phương pháp parse nữa** cho PDF/DOCX để người quản trị chọn theo từng tài liệu. **Không thay thế Docling**: Docling giữ nguyên hành vi và tiếp tục là parser mặc định.

Hiện trạng (đã đọc mã trên nhánh `dev`, `af2d2b7`):

- `backend/app/parsers/__init__.py` đăng ký `TextParser` và `DoclingParser`; `ParserRegistry` đã hỗ trợ nhiều parser cho cùng đuôi file, `list_parsers()` và `get_parser(parser_name=...)`.
- API `GET /documents/{id}/parsers` và `POST /documents/{id}/parse?parser_name=...`; frontend `ParserSelectionModal.jsx` hiển thị danh sách parser theo `PARSER_DETAILS`.
- **Lựa chọn parser không được lưu lại**: `ingest_path(parser_name=...)` dùng parser được chọn, nhưng `GET /documents/{id}` (`routes.py:184`), `read_preview()` (`uploads.py:155`) và nạp lại toàn kho (`load_documents()` → `read_document_text(path)`) luôn dùng parser mặc định. Khi có parser thứ hai cho PDF/DOCX, nạp lại toàn kho sẽ âm thầm quay về Docling và màn xem tài liệu hiển thị nội dung Docling. Task này phải xử lý điểm đó, nếu không LlamaParse không dùng được ổn định.

Kết quả cần có:

1. `LlamaParseParser` (`name = "llamaparse"`, `.pdf`, `.docx`) theo contract `DocumentParser`, gọi SDK chính thức `llama-cloud` (gói `llama-parse` cũ đã deprecated, chỉ duy trì tới 2026-05-01), xuất Markdown, cache theo hash file.
2. Chỉ đăng ký khi bật và có API key; Docling vẫn là mặc định.
3. Parser đã chọn được lưu cho từng tài liệu và được dùng lại khi xem chi tiết, preview và nạp lại toàn kho.
4. Frontend hiển thị lựa chọn LlamaParse kèm ghi chú file được gửi ra dịch vụ bên ngoài.
5. Báo cáo so sánh Docling vs LlamaParse và khuyến nghị chọn parser theo nhóm tài liệu.

## Phạm vi

- Bao gồm: `backend/app/parsers/llamaparse.py` (mới), `backend/app/parsers/__init__.py`, `backend/app/core/config.py`, `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/loaders.py`, `backend/app/ingestion/uploads.py`, `backend/app/api/routes.py` (chỉ chỗ đọc text theo parser đã lưu), `backend/pyproject.toml`, `backend/Dockerfile`, `.env.example`, `frontend/src/components/ParserSelectionModal.jsx`, tests (`test_parsers.py`, `test_llamaparse_parser.py` mới, `test_document_pipeline.py`, `test_document_api.py`), `README.md`, báo cáo `documents/rag-eval/rag-15/`, năm file task này.
- Ngoài phạm vi: thay đổi `DoclingParser`, `normalize_markdown`, chunker, retrieval; đổi parser mặc định; hỗ trợ thêm định dạng mới (`.doc`, ảnh, `.pptx`); job nền/tiến độ parse (FE-07); sửa dữ liệu trong `data/`.
- Ràng buộc:
  - Không ghi API key vào log, cache, response API, test fixture hay năm file task. `.env.example` chỉ chứa placeholder.
  - Toàn bộ test chạy được khi **không** cài extra `[llamaparse]` và không có mạng/key (client được mock).
  - Không thêm migration: lưu parser trong cột JSON `documents.metadata` đã có.
  - Gọi API thật tốn credit và gửi tài liệu nội bộ ra ngoài: chỉ chạy S-06 sau khi người dùng xác nhận chính sách dữ liệu và ước lượng chi phí.
  - Không ghi đè báo cáo eval cũ trong `documents/rag-eval/` (baseline, `rag-05/`, `rag-06/`). Sau khi đo xong, khôi phục index local về trạng thái Docling như trước task.

## Tiêu chí nghiệm thu

- [ ] AC-01: Khi `LLAMAPARSE_ENABLED=true` và có `LLAMA_CLOUD_API_KEY`, `GET /documents/{id}/parsers` của PDF/DOCX trả về `docling` (`is_default: true`) và `llamaparse` (`is_default: false`); khi tắt hoặc thiếu key thì không có `llamaparse`. Hành vi Docling không đổi (test hiện có của Docling pass nguyên trạng).
- [x] AC-02: Unit test với client LlamaParse được mock bao phủ: parse thành công ra Markdown (qua `normalize_markdown`), lần hai đọc cache không gọi API, `convert=False` không gọi API, timeout, lỗi API/hết quota, kết quả rỗng, thiếu SDK — mọi lỗi là `DocumentParseError` thông báo tiếng Việt.
- [x] AC-03: Cache LlamaParse tách khỏi cache Docling (không cùng file), khóa cache gồm hash file + phiên bản cấu hình (tier, ngôn ngữ); đổi cấu hình thì không đọc nhầm cache cũ.
- [ ] AC-04: Parse một tài liệu bằng `parser_name=llamaparse` lưu `metadata.parser = "llamaparse"`; sau đó `GET /documents/{id}`, preview và nạp lại toàn kho đều dùng LlamaParse (đọc cache) cho tài liệu đó, tài liệu khác vẫn dùng Docling. Parser đã lưu không còn khả dụng thì dùng mặc định và log cảnh báo, không làm hỏng nạp lại toàn kho.
- [x] AC-05: Toàn bộ `backend/tests` pass trong môi trường không cài `[llamaparse]`, không mạng.
- [ ] AC-06: Modal chọn parser hiển thị "LlamaParse" với mô tả và ghi chú dịch vụ cloud; `npm run build` của frontend thành công.
- [ ] AC-07: Có báo cáo `documents/rag-eval/rag-15/` so sánh Docling vs LlamaParse trên cùng tài liệu và golden set (hit@4, MRR theo `eval_retrieval`, số chunk, kết quả `check_structure`/`check_chunks`, thời gian, credit tiêu tốn) kèm khuyến nghị chọn parser theo nhóm tài liệu.
- [ ] AC-08: Rà soát log, cache, response `/config`/`/documents` và năm file task không chứa API key; `.env.example` và `README.md` có hướng dẫn cấu hình.

## Tài liệu và phụ thuộc

- Trang Notion RAG-15: https://app.notion.com/p/404334d296eb8157aa8aff41d1acb342
- Phụ thuộc: RAG-05 (`normalize_markdown`, done), RAG-01 (`scripts/eval_retrieval.py`, golden set `backend/tests/fixtures/ptit_ragas_100.json`). RAG-06 (`2026-10-25-rag06-article-clause-chunking`) đang `in_progress` trên `chunker.py`/`pipeline.py`: S-04 của task này sửa `pipeline.py` nên phải đồng bộ với bản RAG-06 mới nhất trước khi sửa.
- Liên quan: RAG-04 (nội dung mất do watermark/ảnh), RAG-07 (bảng biểu) — kết quả so sánh của task này là đầu vào cho hai task đó.
- Tài liệu LlamaParse: https://developers.llamaindex.ai/llamaparse/ (quickstart Python SDK `llama-cloud`), thông báo Parse API v2: https://www.llamaindex.ai/blog/announcing-new-llamacloud-sdks-and-parse-api-v2

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01…S-05, S-07 xong trên working tree nhánh `feat/rag15-llamaparse-parser` (tách từ `dev` tại `af2d2b7`, chưa commit); suite backend 347 passed / 1 skipped (trước task 324 / 1), frontend build pass. AC-02, AC-03, AC-05 đạt; AC-01, AC-04, AC-06 đạt phần tự động. S-06: đã đo PDF D26 bằng Docling (hybrid hit@4 0.820 / MRR 0.756; bm25 0.850 / 0.785) và khôi phục index local đúng 2 tài liệu như trước.
- Blocker: S-06 phần LlamaParse — `.env` local chưa có `LLAMA_CLOUD_API_KEY` (người dùng đã đồng ý cung cấp). Cần: thêm `LLAMAPARSE_ENABLED=true` + `LLAMA_CLOUD_API_KEY=...`, khởi động lại backend.
- Bước tiếp theo: `claude-code` chạy phần còn lại của S-06 trong ngân sách 1000 credit (dự kiến ~810: smoke 2 trang + PDF D26 268 trang ở tier `cost_effective`), viết báo cáo, review vòng 2.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-25T11:29:49+07:00` — `claude-code`: tạo task từ trang Notion RAG-15. Chốt theo yêu cầu người dùng: LlamaParse là phương pháp parse bổ sung, không thay Docling, Docling vẫn mặc định. Đưa việc lưu parser theo tài liệu (AC-04) vào phạm vi vì thiếu nó thì nạp lại toàn kho và màn xem tài liệu sẽ bỏ qua lựa chọn LlamaParse. Dùng SDK `llama-cloud` thay `llama-parse` (deprecated).
- `2026-10-25T12:15:34+07:00` — `claude-code`: người dùng xác nhận (1) được gửi tài liệu lên LlamaCloud, (2) sẽ cung cấp key, (3) ngân sách 1000 credit. Theo ngân sách, mặc định `LLAMAPARSE_TIER=cost_effective` (3 credit/trang; PDF D26 = 804 credit) và S-06 không parse D21. Dùng retry sẵn có của SDK thay vì tự viết; bỏ lock tuần tự hóa. Chuyển trạng thái `in_progress`.
