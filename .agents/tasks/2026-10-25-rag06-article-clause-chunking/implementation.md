# Implementation: 2026-10-25-rag06-article-clause-chunking

## Tổng quan triển khai

S-01…S-05 đã tích hợp trên working tree nhánh `feat/rag06-article-clause-chunking` (tách từ `feat/rag05-heading-hierarchy`, nền `f3e95ed`, **chưa commit**). Index local đã re-ingest lại bản D26 processed với chunking Điều/Khoản + `search_text` (1203 chunk / 749 parent, fingerprint `620d26fd0e0c…`). Migration Alembic `0003_chunk_search_text` đã chạy trên PostgreSQL local.

Kết quả eval cuối (chi tiết ở `verification.md`): hybrid ngang bằng RAG-05 (hit@4 0.850 = 0.850, MRR 0.778 vs 0.780), BM25 tăng (hit@4 0.830 → 0.850), nhóm thủ tục giảm nhẹ (hit@4 0.667 → 0.611). **AC-05 không đạt hoàn toàn** — đã ghi rõ, chờ người dùng quyết định hướng tiếp.

## Nhật ký theo nhiệm vụ

### S-01 — Cleaner lọc nhiễu

- Cập nhật lúc: `2026-10-25T10:40:00+07:00`.
- Đã làm:
  - `clean_text` giờ đi qua `_drop_noise_lines` bỏ: dòng mục lục chấm dẫn (4+ chấm, `…`, 2 chấm + số trang), heading/dòng đậm dính số trang in đậm, số trang trơn (`- 3 -`, `12`), quốc hiệu (kèm/bẵng tiêu ngữ trên cùng dòng), dòng địa điểm-ngày-tháng-năm, vai trò người ký, `(đã ký)` + tên người ký kế tiếp (tối đa 2 dòng), "Nơi nhận" + danh sách phân phát (`(b/c)`, `(t/h)`, `Lưu VT`), watermark `lOMoARcPSD|…`.
  - Bỏ **toàn bộ section "MỤC LỤC"** (kể cả bảng bên trong): thoát khi gặp heading khác hoặc dòng không còn giống entry mục lục (nội dung thật theo sau không có heading vẫn giữ được).
  - Dòng form nhiều ô trống (`Họ và tên: …… Nam (Nữ): ……` — ≥ 2 cụm chấm) được giữ; chỉ dòng có đúng 1 cụm chấm dẫn ở cuối bị coi là entry mục lục/ô trống.
  - Bảng Markdown/HTML và code fence không bao giờ bị đụng.
  - Thêm `is_noise_line(line)` công khai cho script kiểm tra.
- File thay đổi: `backend/app/ingestion/cleaner.py`, `backend/tests/test_chunker.py` (13 test cleaner mới).
- Quyết định/giao diện: `clean_text` giữ chữ ký `(text) -> str` — consumer cũ không đổi.
- Kiểm tra: dry-run toàn `data/` qua `check_chunks --data` — 9 tài liệu sạch (xem V-04); đã soát từng dòng bị bỏ trên 4 tài liệu thật (TB hoàn thiện thủ tục, TB nội trú, D26, D21): chỉ dòng nhiễu bị bỏ, form miễn giảm học phí giữ nguyên các ô.

### S-02 — Chunker theo Điều/Khoản

- Cập nhật lúc: `2026-10-25T10:40:00+07:00`.
- Đã làm:
  - Viết lại `split_parent_child`: duyệt section một lần, parent = section (một Điều/mục); section vượt `parent_size` thì cắt thành nhiều parent-piece, mỗi piece nhóm các block (Khoản/đoạn) liên tiếp, cắt lại tại ranh giới block → không parent nào chứa 2 Điều (AC-01).
  - Child = pack các block của parent-piece tới `child_size`; `min_child_size` (cấu hình `MIN_CHILD_CHUNK_CHARS`, mặc định 120) gộp piece ngắn vào piece kế/trước **cùng section** qua `_merge_short_pieces` + `_steal_trailing_unit`/`_steal_leading_units` (di chuyển block/câu, không cắt giữa từ); piece ngắn chỉ còn khi cả section ngắn. Ghi chú cuối bảng ("Chi tiết xem tại …") dính vào chunk bảng thay vì thành chunk 113 ký tự.
  - `_split_long_block` mới: cắt theo câu (`.` `;` `!` `?` + xuống dòng), pack đơn vị câu; đơn vị vượt hạn mức cắt tại khoảng trắng (`_split_oversized_unit`); overlap câu áp theo ranh giới từ (`_tail_at_word_boundary`) — hết 143 chunk bắt đầu giữa từ (AC-02).
  - `split_text` nhận thêm `min_chunk_len` (mặc định 0 — hành vi cũ cho đường không parent-child).
  - Thêm `compose_search_text(document_title, section_path, text)` (hợp đồng dùng chung, S-03 dùng).
- File thay đổi: `backend/app/ingestion/chunker.py`, `backend/app/core/config.py` (`min_child_chunk_chars`), `backend/tests/test_chunker.py` (10 test chunker mới), `backend/tests/test_chunker_tables_benchmark.py` (assert section-path theo nhóm parent thay vì ánh xạ index với `split_text`).
- Quyết định/giao diện: `split_parent_child` thêm keyword-only param `min_child_size: int | None` — caller cũ không vỡ; pipeline truyền `settings.min_child_chunk_chars`.
- Kiểm tra: pytest `test_chunker.py` 36 pass; V-01, V-02.

### S-03 — Trường `search_text`

- Cập nhật lúc: `2026-10-25T10:40:00+07:00`.
- Đã làm:
  - `Chunk.search_text` (Text NOT NULL, `server_default=""`) + migration `0003_add_chunk_search_text` (backfill `search_text = text` cho bản chưa re-ingest; đã chạy trên DB local, revision head `0003_chunk_search_text`).
  - `ChunkRecord.search_text` (mặc định `""`); `replace_knowledge_base`/`upsert_document` lưu `search_text or text`.
  - Pipeline: `_records_for_document` compose `search_text` một lần (dùng cho cả DB record lẫn payload); embed input theo `settings.embedding_input_field` (`_embedding_input`).
  - BM25 `_ensure_index` tokenize `search_text` (fallback `text` cho snapshot thiếu trường); pgvector `_format_chunk_context` lộ `search_text` (fallback `text`).
  - `eval_retrieval.CONFIG_FIELDS` thêm `min_child_chunk_chars`.
  - Cấu hình `EMBEDDING_INPUT_FIELD` mặc định **`text`** — xem "Quyết định thiết kế có đo lường" dưới đây.
- File thay đổi: `backend/app/db/models.py`, `backend/alembic/versions/0003_add_chunk_search_text.py` (mới), `backend/app/db/repositories.py`, `backend/app/ingestion/pipeline.py`, `backend/app/retrieval/bm25.py`, `backend/app/vectordb/pgvector_store.py`, `backend/app/core/config.py`, `backend/scripts/eval_retrieval.py`, `backend/tests/test_search_text.py` (mới).
- Kiểm tra: pytest `test_search_text.py` 6 pass (BM25 rank theo `search_text` không phải `text` hiển thị; pgvector lộ `search_text`; pipeline embed đúng trường theo config).

### S-04 — Script kiểm tra `check_chunks`

- Cập nhật lúc: `2026-10-25T10:40:00+07:00`.
- Đã làm: `python -m scripts.check_chunks` quét DB (`--db`, mặc định) hoặc dry-run parser+chunker trên thư mục (`--data <dir>`, không ghi DB); 5 mã lỗi: `parent_spans_articles`, `chunk_starts_mid_word`, `chunk_too_short` (parent thân ≥ ngưỡng mới báo), `noise_chunk` (dòng khớp mẫu nhiễu **hoặc** cleaner sẽ cắt bớt dòng — bắt được section MỤC LỤC còn sót), `search_text_missing_context` (thiếu tên tài liệu/section_path). `--strict` trả 1 khi có lỗi; in tối đa 20 phát hiện/mã.
- File thay đổi: `backend/scripts/check_chunks.py` (mới), `backend/tests/test_check_chunks.py` (mới, 8 test).
- Kiểm tra: V-01…V-04, V-06.

### S-05 — Re-ingest, chi phí, eval

- Cập nhật lúc: `2026-10-25T11:05:00+07:00`.
- Đã làm:
  - Ước lượng trước khi chạy: 1203 chunk, search_text ~1.16M ký tự ≈ 290–332k tokens ≈ **$0.006–0.007** với text-embedding-3-small ($0.02/1M).
  - Re-ingest bằng script tạm `documents/rag-eval/rag-06/experiments/reingest_single_document.py` (thay `load_documents` bằng đúng 1 tài liệu D26 processed, không đụng file nguồn — cách làm của RAG-05). Lưu ý `.env` gốc có `CHUNK_SIZE=2048 / CHILD_CHUNK_SIZE=1024 / overlap 256/128` — đúng "cấu hình local 2048/1024" trong đề bài; cả index RAG-05 lẫn index mới đều dùng cấu hình này nên so sánh công bằng.
  - Eval 3 chế độ vào `documents/rag-eval/rag-06/{hybrid,bm25,vector}.json`; 4 thí nghiệm A/B lưu ở `experiments/`.
- File thay đổi: `documents/rag-eval/rag-06/*`, trang task, `documents/rag-eval/README.md`.
- Kiểm tra: V-05, V-07.

## Quyết định thiết kế có đo lường (quan trọng)

1. **Embedding input = `text`, không phải `search_text`** (cấu hình `EMBEDDING_INPUT_FIELD`, mặc định `text`).
   - Thí nghiệm A (embed `search_text` — đúng chữ đề bài): hybrid hit@4 **0.820**, MRR 0.738 — tụt so với RAG-05 (0.850/0.780). Header tĩnh dài, nhiều chữ HOA làm vector text-embedding-3-small lệch.
   - Thí nghiệm B/C (embed `text`, BM25 vẫn tokenize `search_text` trong DB): hybrid **0.850/0.778** — ngang RAG-05.
   - BM25 thì header **tăng** (hit@4 0.830 → 0.850) vì "BHYT" v.v. giờ nằm trong text được tokenize.
   - Do đó: `search_text` vẫn được lưu đầy đủ và BM25 dùng nó; embedding đọc trường theo config để cho phép bật lại `search_text` khi đổi model embedding (vd. model hỗ trợ instruction/context) mà không sửa code.
2. **Parent-piece không chồng lấn overlap** (khác char-split cũ): cắt tại ranh giới block theo spec "nhóm các Khoản liên tiếp"; overlap ký tự cũ tạo bản sao evidence không kiểm soát được.
3. **Lọc section MỤC LỤC** thay vì chỉ từng dòng: các entry dạng bảng và dòng kết thúc `.. 145` né được luật theo dòng; nguyên tắc thoát section giữ nội dung thật theo sau.

## Blocker / bàn giao

- Blocker: không có.
- AC-05 không đạt hoàn toàn (overall ngang bằng trong sai số, nhóm thủ tục giảm 5.6 điểm hit@4 do parent theo mục làm evidence trong guide "HƯỚNG DẪN THỦ TỤC HÀNH CHÍNH" phân mảnh). Hướng đề xuất cho người dùng: (a) chấp nhận trade-off (ngữ liệu sạch + BM25 tăng), (b) tune `HYBRID_VECTOR_WEIGHT` (vector đang yếu hơn BM25 trên corpus này), (c) contextual embedding bằng LLM cho header (RAG tiếp theo).
- Việc còn lại: người dùng xem diff, quyết định commit; RAG-03 có thể tham chiếu quyết định `EMBEDDING_INPUT_FIELD`.
