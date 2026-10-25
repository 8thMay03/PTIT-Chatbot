# Verification: 2026-10-25-rag06-article-clause-chunking

- Verifier: `zcode-agent`.
- Trạng thái tổng: `failed` (AC-05 chưa đạt; AC-01…AC-04, AC-06 đạt).
- Bản được kiểm tra: working tree nhánh `feat/rag06-article-clause-chunking` (tách từ `feat/rag05-heading-hierarchy`, nền `f3e95ed`, chưa commit).
- Môi trường: Windows 11, `backend/.venv` (Python 3.11), PostgreSQL pgvector local (DATABASE_URL `…:5433/ptit_chatbot`), embedding OpenAI `text-embedding-3-small`, `.env` gốc với `CHUNK_SIZE=2048 / CHUNK_OVERLAP=256 / CHILD_CHUNK_SIZE=1024 / CHILD_CHUNK_OVERLAP=128` (đúng "cấu hình local 2048/1024" của đề bài), dataset `backend/tests/fixtures/ptit_ragas_100.json` (100 câu, cache embedding 0 miss).
- Index được kiểm tra: 1 tài liệu D26 processed, 1203 chunk / 749 parent, fingerprint `620d26fd0e0c…`, Alembic head `0003_chunk_search_text`.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (không parent nào chứa 2 Điều)

- Người thực hiện / thời gian: `zcode-agent` / `2026-10-25T10:50+07:00`.
- Loại: script kiểm tra + unit test.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv/Scripts/python -m scripts.check_chunks --db --strict`; `--data ../data` (dry-run 9 tài liệu); `pytest tests/test_chunker.py -k "parent_is_one_article or groups_consecutive"`.
- Kỳ vọng: 0 `parent_spans_articles` trên DB và dry-run.
- Kết quả thực tế: DB `OK: không phát hiện vi phạm` (1203 chunk, 749 parent); dry-run 9 tài liệu / 2904 chunk / 1833 parent sạch. Test Điều dài vượt parent nhóm Khoản liên tiếp không trộn Điều: pass.
- Trạng thái: `passed`.

### V-02 — AC-02 (không cắt giữa từ; chunk ngắn chỉ khi section ngắn)

- Người thực hiện / thời gian: `zcode-agent` / `2026-10-25T10:50+07:00`.
- Lệnh / thao tác: như V-01 (mã `chunk_starts_mid_word`, `chunk_too_short`); `pytest tests/test_chunker.py -k "sentence_boundaries or word_boundary or short_tail or short_section or note_after_table"`.
- Kỳ vọng: 0 chunk bắt đầu chữ thường; 0 chunk < 120 ký tự khi parent thân đủ dài.
- Kết quả thực tế: DB và dry-run đều 0 vi phạm (trước thay đổi: 143 chunk cắt giữa từ, 59 chunk ngắn trên index cũ — số liệu đề bài). Test cắt theo câu/word-boundary: pass.
- Trạng thái: `passed`.

### V-03 — AC-03 (không chunk mục lục/quốc hiệu/chữ ký)

- Người thực hiện / thời gian: `zcode-agent` / `2026-10-25T10:50+07:00`.
- Lệnh / thao tác: như V-01 (mã `noise_chunk`); so thủ công từng dòng bị cleaner bỏ trên 4 tài liệu thật (`TB hoan thien thu tuc dau khoa hoc.pdf`, `1. Thông báo … nội trú.docx`, D26 processed, D21).
- Kỳ vọng: 0 `noise_chunk`; các dòng bị bỏ chỉ là mục lục/quốc hiệu/chữ ký/số trang/watermark.
- Kết quả thực tế: DB 0 vi phạm (index RAG-05 trước đó có 4 chunk "MỤC LỤC" còn sót — được checker mới bắt trước khi re-ingest). Dòng bị bỏ trên tài liệu thật: đúng nhóm nhiễu; form "Hộ khẩu thường trú: ……" (1 ô trống) bị bỏ, form nhiều ô ("Họ và tên: … Nam (Nữ): …") được giữ; text "Thư ký hội đồng thông qua danh sách…" (câu nội dung) được giữ sau khi sửa regex vai trò ký.
- Trạng thái: `passed`.

### V-04 — AC-04 (`search_text` chứa tên tài liệu + section_path; embedding/BM25 dùng nó)

- Người thực hiện / thời gian: `zcode-agent` / `2026-10-25T10:55+07:00`.
- Loại: unit test + script kiểm tra.
- Lệnh / thao tác: `pytest tests/test_search_text.py` (6 test); `pytest tests/test_check_chunks.py`; `check_chunks --db` (mã `search_text_missing_context`).
- Kỳ vọng: mọi chunk `search_text` bắt đầu `"<tên tài liệu> > <section_path>\n"`; test xác nhận BM25 rank theo `search_text` (term chỉ có ở search_text của chunk đúng vẫn thắng, chunk có term trong `text` hiển thị nhưng không có trong `search_text` thì bị loại); pipeline embed đúng trường cấu hình.
- Kết quả thực tế: DB 0 vi phạm; test BM25 + pgvector + pipeline (parametrize `text`/`search_text`) đều pass. Lưu ý: `EMBEDDING_INPUT_FIELD` mặc định `text` (xem V-05 và quyết định trong implementation.md) — test xác nhận khi chọn `search_text` thì embedding dùng đúng trường đó.
- Trạng thái: `passed`.

### V-05 — AC-05 (hit@4, MRR hybrid tăng; nhóm thủ tục không giảm)

- Người thực hiện / thời gian: `zcode-agent` / `2026-10-25T11:00+07:00`.
- Loại: eval retrieval + so sánh per-case.
- Lệnh / thao tác: `python -m scripts.eval_retrieval --mode hybrid --output documents/rag-eval/rag-06/hybrid.json` (tương tự bm25/vector); so với `documents/rag-eval/rag-05/processed_hybrid.json`; nhóm thủ tục = 18 câu ID liệt kê trong script đo (absence_request_deadline, exam_grade_complaint, … one_stop_hours_afternoon — vì dataset chưa có `question_type`).
- Kỳ vọng: hit@4 và MRR hybrid > 0.850/0.780; nhóm thủ tục không giảm.
- Kết quả thực tế:

  | hybrid | hit@1 | hit@4 | hit@10 | MRR | cov@4 |
  |---|---:|---:|---:|---:|---:|
  | RAG-05 | 0.720 | 0.850 | 0.900 | 0.780 | 0.807 |
  | RAG-06 (embed `text`) | 0.720 | **0.850** | 0.890 | **0.778** | 0.804 |
  | RAG-06 (embed `search_text`) | 0.660 | 0.820 | 0.900 | 0.738 | 0.766 |

  - BM25 (dùng `search_text`): hit@4 0.830 → **0.850**, MRR 0.762 → 0.770, hit@10 0.890 → 0.910.
  - Vector: hit@4 0.800 → 0.770, MRR 0.688 → 0.700.
  - Nhóm thủ tục (18 câu): hit@4 0.667 → **0.611** (-0.056), MRR 0.500 → 0.491. 3 câu đổi: student_card_return 4→6, student_card_validity 10→rớt, student_card_initial_deadline 7→6 — đều thuộc guide "HƯỚNG DẪN THỦ TỤC HÀNH CHÍNH…" mà parent theo mục làm evidence phân mảnh.
  - section_dominance max: 0.150 → 0.160 ("Điều 25" → các Điều quy định đào tạo theo tín chỉ).
  - Per-case overall: 9 câu tăng rank, 5 câu giảm.
- Trạng thái: **`failed`** — hit@4/MRR hybrid ngang bằng (không "tăng" như tiêu chí; chênh −0.001…−0.002 MRR nằm trong sai số đo đã ghi nhận ở RAG-05 V-08) và nhóm thủ tục giảm 5.6 điểm hit@4. Cấu hình embed `search_text` (đúng chữ đề bài) tụt rõ hơn (0.820/0.738) nên đã chọn cấu hình `EMBEDDING_INPUT_FIELD=text`.
- Bằng chứng: `documents/rag-eval/rag-06/{hybrid,bm25,vector}.json`, thí nghiệm A/B ở `rag-06/experiments/`.

### V-06 — AC-06 (test chunker cập nhật, pass)

- Người thực hiện / thời gian: `zcode-agent` / `2026-10-25T10:58+07:00`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q`.
- Kỳ vọng: toàn bộ suite pass, không hồi quy.
- Kết quả thực tế: **324 passed, 1 skipped** (test corpus benchmark skip khi thiếu data thật). Test mới: 13 cleaner + 10 chunker + 8 check_chunks + 6 search_text; cập nhật `_assert_parent_child_section_paths` của benchmark bảng (parent theo section thay vì ánh xạ `split_text`).
- Trạng thái: `passed`.

### V-07 — Ước lượng chi phí + re-ingest

- Người thực hiện / thời gian: `zcode-agent` / `2026-10-25T10:59+07:00`.
- Lệnh / thao tác: script đếm ký tự search_text trước khi ingest; `python documents/rag-eval/rag-06/experiments/reingest_single_document.py`; `check_chunks --db --strict` sau ingest.
- Kết quả thực tế: ~1.16M ký tự search_text ≈ 290–332k tokens ≈ **$0.006–0.007** (text-embedding-3-small, $0.02/1M). Re-ingest 1203 chunk; embed theo text (cùng chi phí bậc). Index sạch sau ingest.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Chưa chạy Ragas / eval có sinh câu trả lời (ngoài phạm vi).
- Hit@10 hybrid giảm 0.900 → 0.890 (1 câu: student_card_validity — evidence nằm trong guide, parent mục mới không vào top-10).
- Sai số đo: RAG-05 đã ghi nhận hai lần ingest cùng fingerprint lệch nhau ở rank 5–10 (cov@10 0.850 vs 0.8525); các chênh lệch ≤ 0.003 của RAG-06 so với RAG-05 nằm trong dải này.
- `chunk_too_short` dùng parent_text làm proxy cho "cả section" — parent-piece của một Điều dài không đại diện toàn section; chấp nhận vì piece là đơn vị gộp thực tế.

## Kết luận

- Tiêu chí đạt: AC-01, AC-02, AC-03, AC-04, AC-06.
- Tiêu chí chưa đạt: **AC-05** — hybrid ngang bằng (không tăng), nhóm thủ tục giảm 5.6 điểm hit@4.
- Đề xuất: người dùng quyết một trong: (a) chấp nhận kết quả (ngữ liệu sạch, BM25 +2 điểm, hybrid không thụt lùi đáng kể) và ghi AC-05 thành "không thụt lùi"; (b) làm tiếp một task riêng tối ưu retrieval cho tài liệu hướng dẫn (vd. parent lớn hơn cho guide, hoặc hybrid weight); (c) contextual embedding bằng LLM. Trước khi quyết có thể xem diff và chạy lại eval.
