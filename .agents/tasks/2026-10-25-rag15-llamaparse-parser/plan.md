# Plan: 2026-10-25-rag15-llamaparse-parser

## Phân công

### S-01 — Spike: chốt API SDK `llama-cloud`

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: đọc tài liệu chính thức và mã nguồn SDK `llama-cloud` (bản ổn định mới nhất trên PyPI, ghi rõ phiên bản), chốt: cách khởi tạo client (key, base URL cho region), hàm upload + parse (sync hay poll job), tên tier/preset cho Markdown (lưu ý `fast` không trả Markdown), tham số ngôn ngữ tiếng Việt, cách lấy Markdown từng trang và nối trang, loại exception khi timeout/401/402/429/5xx, hỗ trợ `.docx` trực tiếp hay không. Ghi kết quả vào `implementation.md` mục S-01 rồi cập nhật "Hợp đồng dùng chung" nếu khác dự kiến. Không cần API key. Phục vụ `AC-02`, `AC-03`.
- Phạm vi file được sửa: chỉ `implementation.md` (và `plan.md` nếu hợp đồng đổi).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: ghi chú API + phiên bản pin cho extra `[llamaparse]`.
- Người nhận: `claude-code` (S-02).

### S-02 — Cấu hình + `LlamaParseParser` + cache + test

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu:
  - `config.py`: thêm các trường trong "Hợp đồng dùng chung".
  - `parsers/llamaparse.py`: lớp `LlamaParseParser`; import SDK lười trong hàm (thiếu SDK → `DocumentParseError` hướng dẫn `pip install -e ".[llamaparse]"`); tách lời gọi mạng vào một hàm `_parse_remote(path) -> str` để test mock; cache Markdown thô; `convert=False` chỉ đọc cache; hậu xử lý tối thiểu riêng cho LlamaParse (bỏ placeholder ảnh, gộp dòng trống), còn heading do `normalize_markdown` xử lý ở facade; retry có giới hạn cho lỗi tạm thời (429/5xx/timeout mạng), không retry 401/402; serialize lời gọi bằng lock như Docling để không bắn song song khi nạp lại toàn kho.
  - Log chỉ tên file, thời gian, số trang; không log key hay nội dung response lỗi chứa header.
  - Test mới `tests/test_llamaparse_parser.py` theo `AC-02`, `AC-03` (mock `_parse_remote`, `tmp_path` cho cache, `monkeypatch` settings).
- Phạm vi file được sửa: `backend/app/core/config.py`, `backend/app/parsers/llamaparse.py` (mới), `backend/tests/test_llamaparse_parser.py` (mới).
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: parser + test xanh, chưa đăng ký vào registry.
- Người nhận: `claude-code` (S-03).

### S-03 — Đăng ký có điều kiện + đóng gói

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `parsers/__init__.py` dựng registry qua hàm `build_registry()` (Text, Docling, rồi LlamaParse nếu `llamaparse_available()`); Docling đăng ký trước nên vẫn là mặc định cho `.pdf/.docx`. Thêm extra `llamaparse = ["llama-cloud>=<bản chốt ở S-01>"]` trong `pyproject.toml`; Dockerfile cài `".[docling,llamaparse]"`; `.env.example` thêm khối cấu hình (mặc định `LLAMAPARSE_ENABLED=false`, key để trống). Test registry: bật/tắt/thiếu key, `list_parsers` đúng `is_default`. Phục vụ `AC-01`, `AC-05`.
- Phạm vi file được sửa: `backend/app/parsers/__init__.py`, `backend/pyproject.toml`, `backend/Dockerfile`, `.env.example`, `backend/tests/test_parsers.py`.
- Phụ thuộc: S-02.
- Đầu ra/bàn giao: `GET /documents/{id}/parsers` trả `llamaparse` khi cấu hình đủ.
- Người nhận: `claude-code` (S-04).

### S-04 — Lưu và dùng lại parser theo tài liệu

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu:
  - `pipeline.py`: `_records_for_document` ghi `metadata["parser"]` = tên parser thực tế (parser được chọn hoặc mặc định của đuôi file). Cần `SourceDocument` mang thêm `parser_name: str | None = None` (field có default để không vỡ chỗ tạo hiện có).
  - `loaders.py`: `load_documents(data_dir, parser_names: Mapping[str, str] | None = None)` — khóa là `source_path` dạng lưu trong DB; parser không còn đăng ký thì dùng mặc định + `logger.warning`.
  - `pipeline.build_chunks()`: đọc map `source_path → metadata.parser` từ DB trước khi gọi `load_documents`.
  - `uploads.read_preview()` và `routes.get_document()`: đọc text với parser đã lưu (`convert=False`), fallback như trên. Thêm helper chung (ví dụ `parsers.resolve_parser_name(path, stored)`) để không lặp logic fallback.
  - Test: parse bằng parser thay thế → metadata lưu đúng; preview/detail/nạp lại toàn kho dùng parser đã lưu; parser đã lưu biến mất → fallback, không lỗi. Phục vụ `AC-04`.
- Phạm vi file được sửa: `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/loaders.py`, `backend/app/ingestion/uploads.py`, `backend/app/api/routes.py` (chỉ `get_document`), `backend/app/parsers/__init__.py`, `backend/app/db/repositories.py` (nếu cần hàm đọc map parser), `backend/tests/test_document_pipeline.py`, `backend/tests/test_document_api.py`, `backend/tests/test_parsers.py`.
- Phụ thuộc: S-03. Trước khi sửa `pipeline.py`, đọc lại trạng thái RAG-06 và working tree; nếu RAG-06 chưa merge vào `dev` thì báo coordinator để chọn nhánh nền.
- Đầu ra/bàn giao: lựa chọn parser bền vững qua các đường đọc.
- Người nhận: `claude-code` (S-05).

### S-05 — Frontend

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: thêm `llamaparse` vào `PARSER_DETAILS` (tiêu đề "LlamaParse", mô tả: parse bằng dịch vụ cloud LlamaParse, phù hợp file scan/bảng phức tạp; ghi chú file được gửi lên LlamaCloud và tốn credit). Không đổi luồng modal. `npm run build` pass. Phục vụ `AC-06`.
- Phạm vi file được sửa: `frontend/src/components/ParserSelectionModal.jsx` (và `frontend/src/styles/parser-selection.css` nếu cần kiểu cho ghi chú).
- Phụ thuộc: S-03 (tên parser `llamaparse` đã chốt). Có thể làm song song với S-04 vì khác file.
- Đầu ra/bàn giao: giao diện chọn parser có LlamaParse.
- Người nhận: `claude-code` (verifier).

### S-06 — Chạy thật và so sánh Docling vs LlamaParse

- Agent: `claude-code`
- Trạng thái: `blocked` — phần Docling xong; phần LlamaParse chờ `LLAMA_CLOUD_API_KEY` trong `.env` local (người dùng đã duyệt chính sách dữ liệu và ngân sách 1000 credit).
- Mục tiêu:
  1. Đếm số trang các tài liệu định đo, ước lượng credit theo tier đã chốt, gửi người dùng duyệt.
  2. Parse bằng LlamaParse qua API `POST /documents/{id}/parse?parser_name=llamaparse` (kiểm thủ công AC-01/AC-04 trên app thật), lần hai xác nhận đọc cache.
  3. So sánh trên cùng tài liệu D26 processed đang dùng cho eval: `scripts.check_structure`, `scripts.check_chunks --db --strict`, `scripts.eval_retrieval --mode hybrid` và `--mode bm25` với golden set, số chunk/parent, thời gian parse, credit. Chọn thêm 1–2 PDF có bảng/watermark/scan trong `data/` để so định tính (dry-run, không index).
  4. Ghi `documents/rag-eval/rag-15/` (JSON kết quả + `README.md` khuyến nghị) và khôi phục index local bằng Docling, xác nhận fingerprint như trước.
- Phạm vi file được sửa: `documents/rag-eval/rag-15/*`, `documents/rag-eval/README.md`, năm file task.
- Phụ thuộc: S-04, quyết định của người dùng.
- Đầu ra/bàn giao: báo cáo so sánh + khuyến nghị. Phục vụ `AC-07`.
- Người nhận: `claude-code` (verifier/reviewer).

### S-07 — Tài liệu

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `README.md` thêm mục LlamaParse (cài extra, biến môi trường, chọn parser trong modal, cache, lưu ý dữ liệu gửi ra ngoài và chi phí); cập nhật dòng mô tả `parsers/`. Phục vụ `AC-08`.
- Phạm vi file được sửa: `README.md`.
- Phụ thuộc: S-03 (tên biến cấu hình đã chốt).

## Hợp đồng dùng chung

- Parser: `LlamaParseParser.name = "llamaparse"`, `extensions = frozenset({".pdf", ".docx"})`, `parse(path, *, convert=True) -> str | None` — trả Markdown thô đã hậu xử lý riêng; facade `read_document_text` áp `normalize_markdown` như mọi parser.
- Cấu hình (`Settings`, alias env), tên có thể chỉnh sau S-01 nếu SDK khác:
  - `llamaparse_enabled: bool = False` — `LLAMAPARSE_ENABLED`
  - `llama_cloud_api_key: str | None = None` — `LLAMA_CLOUD_API_KEY` (cùng kiểu với các key khác trong `config.py`)
  - `llamaparse_base_url: str | None = None` — `LLAMAPARSE_BASE_URL` (để trống dùng mặc định của SDK; đặt khi dùng region EU)
  - `llamaparse_tier: str = "cost_effective"` — `LLAMAPARSE_TIER` (chốt ở S-01 theo ngân sách)
  - `llamaparse_version: str = "latest"` — `LLAMAPARSE_VERSION` (thêm ở S-01: SDK yêu cầu version theo tier)
  - `llamaparse_language: str = "vi"` — `LLAMAPARSE_LANGUAGE`
  - `llamaparse_timeout_seconds: float = 900` — `LLAMAPARSE_TIMEOUT_SECONDS` (dùng cho cả request lẫn chờ poll)
  - `llamaparse_max_retries: int = 2` — `LLAMAPARSE_MAX_RETRIES`
- `llamaparse_available() -> bool`: `enabled and bool(api_key)`.
- Cache: `settings.converted_documents_path / "llamaparse" / f"{sha256(_CONVERTER_VERSION | tier | version | language | file bytes)}.md"`; `_CONVERTER_VERSION = "llamaparse-v1"`. Cache Docling giữ nguyên tại gốc `converted_documents_path`.
- Lỗi: mọi lỗi SDK/mạng/rỗng → `DocumentParseError` (API trả 422 như hiện tại). Thông báo dự kiến: thiếu SDK, chưa cấu hình key, key sai (401), hết credit (402), quá hạn mức (429), timeout, file không có nội dung.
- Metadata tài liệu: `documents.metadata["parser"]: str` — tên parser đã tạo text đang index. Bản ghi cũ không có khóa này được coi là parser mặc định.
- File mã nguồn dùng chung: `pipeline.py` (RAG-06 cũng sửa) — chỉ sửa ở S-04 sau khi đồng bộ với RAG-06; `parsers/__init__.py` sửa ở S-03 rồi S-04, tuần tự.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01…AC-08.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff của task.
- Hình thức review: `self_review` (một agent). Người dùng có thể chỉ định reviewer độc lập trước khi đóng task.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 (spike) → S-02 → S-03; chạy `pytest` toàn bộ sau S-03 (AC-01, AC-02, AC-03, AC-05).
2. S-04 sau khi đồng bộ `pipeline.py` với RAG-06; S-05 song song với S-04. Chạy lại `pytest` toàn bộ + `npm run build` (AC-04, AC-05, AC-06).
3. S-07 tài liệu; rà soát secret (AC-08).
4. S-06 khi người dùng gỡ blocker: ước lượng → chạy thật → báo cáo → khôi phục index (AC-07).
5. Self-review, sửa nhận xét bắt buộc, verifier chạy lại phần bị ảnh hưởng; coordinator đóng task khi đủ điều kiện. Nếu S-06 còn bị chặn, có thể bàn giao phần mã để review trước nhưng task chưa `done`.

## Rủi ro và điều chỉnh kế hoạch

- API SDK `llama-cloud` đổi nhanh (v1 → v2, Parse API v2): S-01 chốt phiên bản và pin cận trên trong extra; toàn bộ lời gọi SDK gói trong `_parse_remote` để đổi SDK chỉ sửa một hàm.
- Gửi tài liệu nội bộ ra dịch vụ bên thứ ba: parser mặc định tắt, chỉ chạy khi người quản trị chọn; ghi chú trong UI và README; S-06 chờ người dùng xác nhận.
- Chi phí credit khi nạp lại toàn kho: cache theo hash file đảm bảo chỉ parse lại khi file đổi; nạp lại toàn kho chỉ gọi LlamaParse cho tài liệu đã chọn parser này.
- Request parse đồng bộ có thể chạy vài phút với file lớn: giữ timeout cấu hình được; job nền thuộc FE-07, ngoài phạm vi. Ghi thời gian thực tế ở S-06 để FE-07 tham khảo.
- Markdown của LlamaParse khác Docling (heading, bảng, header/footer từng trang) có thể làm `section_path` và chunk khác: đo bằng `check_structure`/`check_chunks` ở S-06; nếu cần chuẩn hóa thêm thì ghi đề xuất cho task sau, không sửa `normalize_markdown` trong task này.
- Xung đột với RAG-06 trên `pipeline.py`: S-04 đọc lại working tree/nhánh RAG-06 trước khi sửa và báo coordinator nếu chưa merge.
- `2026-10-25T12:15:34+07:00` — điều chỉnh sau S-01: dùng retry của SDK (`max_retries`) thay vì tự viết; không dùng lock tuần tự hóa; thêm `LLAMAPARSE_VERSION`; timeout 900 giây áp cho cả request upload. Script đo đặt tại `documents/rag-eval/rag-15/experiments/` (`reingest_documents.py`, `restore_index.py`).
