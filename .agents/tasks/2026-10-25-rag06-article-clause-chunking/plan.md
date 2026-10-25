# Plan: 2026-10-25-rag06-article-clause-chunking

## Phân công

### S-01 — Cleaner lọc nhiễu

- Agent: `zcode-agent`
- Trạng thái: `done`
- Mục tiêu: `clean_text` bỏ dòng mục lục (chấm dẫn + số trang, heading/dòng đậm có số trang dính), quốc hiệu + tiêu ngữ + dòng ngày tháng năm, số trang tự do, khối chữ ký (vai trò, "(đã ký)", tên người, "Nơi nhận" kèm mục phân phát); không chạm dòng trong bảng Markdown/HTML và code fence. Phục vụ `AC-03`.
- Phạm vi file được sửa: `backend/app/ingestion/cleaner.py`, `backend/tests/test_chunker.py` (hoặc file test cleaner riêng).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: cleaner + test xanh.

### S-02 — Chunker theo Điều/Khoản + cắt theo câu + gộp ngắn

- Agent: `zcode-agent`
- Trạng thái: `done`
- Mục tiêu: `split_parent_child` dựng parent theo section (một Điều/mục; Điều dài thì nhóm các Khoản/đoạn liên tiếp), child = Khoản/đoạn trong parent; `_split_long_block` cắt theo ranh giới câu và không bao giờ bắt đầu giữa từ; gộp/phia chuyển块 ngắn (< 120 ký tự, cấu hình) vào chunk liền kề cùng section. Phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/ingestion/chunker.py`, `backend/app/core/config.py`, `backend/tests/test_chunker.py`.
- Phụ thuộc: S-01 (cleaner chạy trước chunker trong `split_text`).
- Đầu ra/bàn giao: chunker + config + test xanh.

### S-03 — Trường `search_text` (model, migration, pipeline, retrieval)

- Agent: `zcode-agent`
- Trạng thái: `done`
- Mục tiêu: cột `chunks.search_text` + migration Alembic 0003 (backfill tạm bằng `text` cho bản chưa re-ingest); `compose_search_text(title, section_path, text)`; pipeline build `search_text`, embed theo `search_text`; BM25 tokenize `search_text`; pgvector context lộ `search_text`. Phục vụ `AC-04`.
- Phạm vi file được sửa: `backend/app/db/models.py`, `backend/alembic/versions/0003_add_chunk_search_text.py` (mới), `backend/app/db/repositories.py`, `backend/app/ingestion/pipeline.py`, `backend/app/retrieval/bm25.py`, `backend/app/vectordb/pgvector_store.py`, `backend/scripts/eval_retrieval.py` (CONFIG_FIELDS), tests liên quan.
- Phụ thuộc: S-02 (chunk shape ổn định).
- Hợp đồng dùng chung: `Chunk.search_text: str NOT NULL DEFAULT ''`; BM25/embedding dùng `search_text or text` khi thiếu; `chunks_payload` có khóa `search_text`.

### S-04 — Script kiểm tra toàn kho

- Agent: `zcode-agent`
- Trạng thái: `done`
- Mục tiêu: `python -m scripts.check_chunks` quét DB (`--db`) hoặc dry-run trên thư mục data (`--data`): parent không chứa 2 Điều, không chunk bắt đầu giữa từ, chunk < 120 chỉ khi section ngắn, không chunk nhiễu (mục lục/quốc hiệu/chữ ký/số trang), `search_text` đủ tên tài liệu + section_path. `--strict` trả 1 khi vi phạm. Phục vụ `AC-01`…`AC-04`.
- Phạm vi file được sửa: `backend/scripts/check_chunks.py` (mới), test cho script.
- Phụ thuộc: S-01…S-03.

### S-05 — Re-ingest, ước lượng chi phí, eval trước/sau

- Agent: `zcode-agent`
- Trạng thái: `done`
- Mục tiêu: dry-run toàn `data/` bằng check_chunks; ước lượng token/chi phí embed text-embedding-3-small trước khi chạy; re-ingest D26 processed (script tạm thay `load_documents`, không đụng file nguồn); eval hybrid + bm25, so với `rag-05/processed_hybrid.json`; đo nhóm câu thủ tục theo danh sách ID; ghi báo cáo `documents/rag-eval/rag-06/`. Phục vụ `AC-05`.
- Phạm vi file được sửa: `documents/rag-eval/rag-06/*.json`, `documents/rag-eval/README.md`, trang task.
- Phụ thuộc: S-01…S-04.

## Hợp đồng dùng chung

- `compose_search_text(document_title, section_path, text) -> str`: `"{title} > {section_path}\n{text}"` (bỏ phần rỗng) — đặt trong `app.ingestion.chunker` để unit test trực tiếp.
- `MIN_CHILD_CHUNK_CHARS` (mặc định 120) truyền vào `split_parent_child(..., min_child_size=...)`; children/parents đều áp dụng gộp ngắn trong cùng section.
- Chunk DB: `search_text` NOT NULL DEFAULT ''; mọi consumer đọc `search_text or text`.
- Index local = 1 tài liệu D26 processed (fingerprint đổi sau re-ingest); eval so cùng dataset `ptit_ragas_100.json`.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `zcode-agent`; phạm vi: AC-01…AC-06.
- Reviewer: `zcode-agent`; phạm vi: toàn bộ diff; hình thức `self_review` (một agent).
- Người xử lý nhận xét: `zcode-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → S-02 → S-03 (chunk shape ổn định trước khi lưu search_text).
2. S-04 dùng thành quả S-01…S-03.
3. Full pytest sau S-03, lại sau S-04.
4. S-05: ước lượng chi phí → re-ingest → eval → so sánh → ghi verification.
5. Self-review, sửa nhận xét bắt buộc, chạy lại kiểm tra bị ảnh hưởng.

## Rủi ro và điều chỉnh kế hoạch

- Regex lọc nhiễu có thể ăn nhầm nội dung thật (dòng kết thúc bằng số, tên riêng): chỉ dùng mẫu hẹp (chấm dẫn ≥4, số trang `^\d{1,3}$`/`- n -`, dòng vai trò/chữ ký exact-match); dry-run trên toàn `data/` liệt kê từng dòng bị bỏ để soát.
- Gộp chunk ngắn có thể tạo child vượt `child_size` ở tail bảng: bảng đã có `_merge_short_table_tail` riêng, giữ nguyên.
- Embedding thay đổi (search_text) làm đổi toàn bộ vector → chi phí embed lại toàn kho; ước lượng trước khi chạy (dự kiến ~1.3k chunk, chi phí không đáng kể với text-embedding-3-small).
- Eval có thể không tăng nếu noise filter bỏ nội dung nằm trong expected_terms — kiểm tra từng câu thua mới so với baseline.
