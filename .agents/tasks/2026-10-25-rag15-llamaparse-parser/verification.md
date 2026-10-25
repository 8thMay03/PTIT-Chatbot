# Verification: 2026-10-25-rag15-llamaparse-parser

- Verifier: `claude-code`.
- Trạng thái tổng: `blocked` — AC-01…AC-06 đạt phần tự động; AC-07 và phần thủ công của AC-01/AC-04 chờ `LLAMA_CLOUD_API_KEY`; AC-08 mới rà soát một phần.
- Bản được kiểm tra: working tree nhánh `feat/rag15-llamaparse-parser` trên nền `af2d2b7` (`dev`) (chưa commit), lúc `2026-10-25T12:15:34+07:00`.
- Môi trường: Windows 11, `backend/.venv` Python 3.11.5, pytest 9.1.x; PostgreSQL local (pgvector); frontend Vite 5; embedding OpenAI `text-embedding-3-small`; `.env` local có `CHUNK_SIZE=2048/CHILD_CHUNK_SIZE=1024`, `HYBRID_VECTOR_WEIGHT=0.80`.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (đăng ký có điều kiện, Docling mặc định)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:15:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_parsers.py` (`test_llamaparse_is_an_opt_in_alternative_to_docling`, 4 tham số: bật + key; tắt; thiếu key; key toàn khoảng trắng). Test Docling hiện có (`test_document_converters.py`) không sửa.
- Kỳ vọng: bật + key → `[docling (mặc định), llamaparse]` cho `.pdf`/`.DOCX`; các trường hợp khác chỉ `docling`; `.md` chỉ `text`.
- Kết quả thực tế: pass; test Docling pass nguyên trạng.
- Trạng thái: `passed` (phần tự động). Phần thủ công `GET /api/documents/{id}/parsers` trên app thật: `not_run` — chờ key.
- Bằng chứng: kết quả suite ở V-05.

### V-02 — AC-02 (hành vi parser với client mock)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:15:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q tests/test_llamaparse_parser.py` (SDK giả qua `sys.modules["llama_cloud"]`).
- Kỳ vọng: pass các ca thành công (tham số gửi SDK, nối trang đúng thứ tự, `normalize_markdown`), cache hit, `convert=False`, timeout poll, job FAILED, lỗi kết nối, HTTP 401/402/429/500, kết quả rỗng, trang lỗi lẻ/toàn bộ, thiếu SDK, chưa cấu hình key.
- Kết quả thực tế: 15 test pass. Các ca lỗi xác nhận thông báo không chứa body response giả ("secrets") và không ghi cache.
- Trạng thái: `passed`.
- Bằng chứng: suite ở V-05.

### V-03 — AC-03 (cache tách biệt, khóa theo cấu hình)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:15:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `test_cache_is_separate_from_docling_and_keyed_by_options`, `test_changed_file_is_parsed_again`.
- Kỳ vọng: cache nằm ở `converted/llamaparse/`, khác đường dẫn cache Docling, không chứa key; đổi tier hoặc ngôn ngữ → cache miss; đổi nội dung file → parse lại.
- Kết quả thực tế: pass.
- Trạng thái: `passed`.
- Bằng chứng: suite ở V-05.

### V-04 — AC-04 (lưu và dùng lại parser theo tài liệu)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:15:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `test_parser_choice_is_stored_and_kept_by_preview_and_full_reload` (`test_document_pipeline.py`, SQLite in-memory: upload 2 PDF → parse lại 1 file bằng `llamaparse` → kiểm metadata, preview, `ingest_documents()`), `test_get_document_reads_text_with_stored_parser` (`test_document_api.py`), `test_loader_uses_stored_parser_choice_per_document`, `test_resolve_parser_name_falls_back_when_stored_parser_is_unavailable` (`test_parsers.py`).
- Kỳ vọng: `metadata.parser` = `llamaparse`/`docling` đúng từng file và giữ nguyên sau nạp lại toàn kho; chunk của file đã chọn có nội dung LlamaParse, file kia không; chỉ 1 lần gọi remote (preview + nạp lại đọc cache); chi tiết tài liệu đọc bằng parser đã lưu; parser biến mất → mặc định + cảnh báo.
- Kết quả thực tế: pass.
- Trạng thái: `passed` (phần tự động). Kiểm thủ công trên app thật với LlamaParse: `not_run` — chờ key.
- Bằng chứng: suite ở V-05.

### V-05 — AC-05 (toàn bộ test không cần extra/mạng)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:15:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác:
  1. Trước task: `.venv/Scripts/python -m pytest -q` → `324 passed, 1 skipped`.
  2. Sau thay đổi, chưa cài `llama-cloud`: `.venv/Scripts/python -m pytest -q` → `347 passed, 1 skipped`.
  3. Bản cuối (sau khi cài `llama-cloud` 2.19.0 cho S-06), chặn SDK: `.venv/Scripts/python -c "import sys; sys.modules['llama_cloud']=None; import pytest; sys.exit(pytest.main(['-q','-p','no:cacheprovider']))"` → `347 passed, 1 skipped`; chạy thường `.venv/Scripts/python -m pytest -q` → `347 passed, 1 skipped`.
- Kỳ vọng: toàn bộ pass, không gọi mạng LlamaCloud.
- Kết quả thực tế: như trên (+23 test so với trước task). 1 warning có sẵn (Starlette TestClient deprecation).
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest như trên.
- Ghi chú: `test_database_postgres.py` chạy Alembic `fileConfig` làm disable các logger đã tạo trước đó; 2 test kiểm log (`caplog`) phải bật lại logger (`monkeypatch.setattr(logger, "disabled", False)`).

### V-06 — AC-06 (frontend)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:15:34+07:00`.
- Loại: build.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm run build`.
- Kỳ vọng: build thành công.
- Kết quả thực tế: `✓ built in 1.70s` (index ~346.5 kB JS).
- Trạng thái: `passed` (build). Xem trực quan modal với backend bật LlamaParse: `not_run` — làm cùng V-01 thủ công khi có key.
- Bằng chứng: đầu ra Vite.

### V-07 — AC-07 (so sánh Docling vs LlamaParse)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:12+07:00` (phần Docling).
- Loại: đo lường.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác (phần Docling, đã chạy):
  1. `python ../documents/rag-eval/rag-15/experiments/reingest_documents.py "../data/Sổ tay sinh viên D26 _1_.pdf" --parser docling` → 977 chunk / 638 parent.
  2. `python -m scripts.eval_retrieval --mode hybrid|bm25 --output documents/rag-eval/rag-15/docling_pdf_<mode>.json`.
  3. `python -m scripts.check_chunks --db` → không vi phạm; `python -m scripts.check_structure "../data/Sổ tay sinh viên D26 _1_.pdf" --parser docling` → 566 heading, 0 lỗi, 15 cảnh báo.
  4. `python ../documents/rag-eval/rag-15/experiments/restore_index.py` → 2 tài liệu, 1203 + 977 chunk, đúng ID gốc.
- Kết quả thực tế (golden set 100 câu, so với index RAG-06 = D26 processed `.md`):

  | Bản D26 | Chế độ | hit@1 | hit@4 | hit@10 | MRR | cov@4 |
  |---|---|---:|---:|---:|---:|---:|
  | processed `.md` (RAG-06, `rag-06/*.json`) | hybrid | 0.720 | 0.850 | 0.890 | 0.778 | 0.804 |
  | PDF + Docling | hybrid | 0.690 | 0.820 | 0.890 | 0.756 | 0.769 |
  | processed `.md` (RAG-06) | bm25 | 0.710 | 0.850 | 0.910 | 0.770 | 0.797 |
  | PDF + Docling | bm25 | 0.720 | 0.850 | 0.910 | 0.785 | 0.813 |

- Kỳ vọng: báo cáo đủ hai parser + khuyến nghị.
- Trạng thái: `blocked` — phần LlamaParse chờ `LLAMA_CLOUD_API_KEY` trong `.env` local.
- Bằng chứng: `documents/rag-eval/rag-15/docling_pdf_hybrid.json`, `docling_pdf_bm25.json`.

### V-08 — AC-08 (không lộ secret, tài liệu cấu hình)

- Người thực hiện / thời gian: `claude-code` / `2026-10-25T12:15:34+07:00`.
- Loại: rà soát mã + test.
- Thư mục chạy: gốc repo.
- Lệnh / thao tác: đọc mã — key chỉ đọc từ `settings.llama_cloud_api_key` và truyền vào client SDK; log chỉ có tên file, tier, số trang, credit, thời gian; thông báo lỗi không gồm body response (test ở V-02); cache không chứa key (test ở V-03); `/api/config` dựng response từ các trường chỉ định, không dump toàn bộ settings; `.env.example` key để trống; `README.md` có mục cấu hình.
- Kỳ vọng: không lộ key; có hướng dẫn.
- Kết quả thực tế: đạt ở mức mã/test.
- Trạng thái: `not_run` cho phần rà soát log/cache thật sau khi chạy API thật (làm sau S-06).
- Bằng chứng: như trên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy full suite đầu sau khi thêm test: 2 test `caplog` fail do logger bị Alembic `fileConfig` disable (pass khi chạy riêng file). Đã sửa trong test; chạy lại pass (V-05).
- Lần khôi phục index đầu tiên dùng đường dẫn tương đối → `source_path` thành `../data/...`, ID PDF đổi. Đã sửa (`reingest_documents.py` resolve đường dẫn tuyệt đối; `restore_index.py` tái hiện đúng cách RAG-06 + upload đã tạo ID) và khôi phục lại, xác nhận đúng ID gốc.
- Chưa chạy: mọi lời gọi LlamaCloud thật; xem trực quan modal; rà soát log/cache thật.

## Kết luận

- Tiêu chí đã đạt: AC-02, AC-03, AC-05; AC-01, AC-04, AC-06 đạt phần tự động/build.
- Tiêu chí chưa đạt/chưa xác minh: AC-07 (chờ key), phần thủ công AC-01/AC-04/AC-06, AC-08 phần log thật.
- Đề xuất: người dùng thêm `LLAMAPARSE_ENABLED=true` và `LLAMA_CLOUD_API_KEY` vào `.env` local, khởi động lại backend; sau đó chạy phần còn lại của S-06.
