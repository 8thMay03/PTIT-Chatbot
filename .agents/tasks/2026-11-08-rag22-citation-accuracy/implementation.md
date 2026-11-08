# Implementation: 2026-11-08-rag22-citation-accuracy

## Tổng quan triển khai

Nhánh `feat/rag22-citation-accuracy` tách từ `dev` tại `e6981f1` (`git diff HEAD --stat` rỗng trước khi tạo nhánh; các file `M` trên `dev` chỉ là stat/CRLF). Một agent (`agent-claude`) làm tuần tự S-05a → S-01 → S-02 → S-03 → S-04 → S-05b → S-06 → S-07. Đã tích hợp đủ S-01…S-07 trên nhánh; index local đã backfill.

| Commit | Nhiệm vụ | Nội dung |
|---|---|---|
| `4ce8bad` | S-05a | script `dump_citation_locators` + bản chụp locator "trước" |
| `439f6cd` | S-01 | `refusal.py`, bỏ tự gắn `[n]`, câu từ chối không kèm `sources`, prompt nêu câu từ chối |
| `8cc5c4a` | S-02 | `legal_units.extract_legal_units`; `citations.py` dùng làm đường dự phòng |
| `46bb3d4` | S-03 | `legal_*` trong `Chunk`/`ParentChildChunk`, metadata chunk, vector, BM25, parent-child, citation |
| `e7a5134` | S-04 | `refresh_legal_metadata` (dry-run/`--apply`), tách `rechunk_matching_db` dùng chung |
| `e3356c0` | S-06 | nhãn "Nguồn trích dẫn"/"Nguồn liên quan" |
| `bdc6d0f` | S-04 | in báo cáo backfill bằng UTF-8 (console Windows cp1252 khi pipe) |
| `c4bcd78` | S-02/S-05 | Khoản giữa dòng + đánh số bắt đầu lại (sửa kế thừa sai phát hiện ở S-05b) |
| `4977e1f` | S-07 | báo cáo `documents/rag-eval/rag-22/`, mục RAG-22 trong README, năm file task |

## Nhật ký theo nhiệm vụ

### S-05a — agent-claude

- Cập nhật lúc: `2026-11-08T10:49:29+07:00` (commit `4ce8bad`).
- Đã làm: `backend/scripts/dump_citation_locators.py` tái dùng `build_retrieval_fn("full")`, `CachedEmbeddingModel`, `warm_cache_texts`, `snapshot_corpus/config`, `git_info`, `load_dataset`, `dataset_sha256` của `eval_retrieval` bằng import (không sửa `eval_retrieval.py`). Locator lấy qua `numbered_contexts` của commit đang checkout. Top-k mặc định 10 (nhiều chunk hơn top-4 của chat để phủ rộng). Chụp `locators_before_rag_300.json`, `locators_before_ragas_100.json` ở `e6981f1` với index chưa backfill.
- Kiểm tra: chạy lại `ragas_100` vào thư mục tạm rồi `--diff` với bản đã lưu: 1000/1000 `unchanged`, 0 đổi thứ tự → bản chụp lặp lại được. `pytest tests/test_dump_citation_locators.py` xanh.

### S-01 — agent-claude

- Cập nhật lúc: `2026-11-08T10:53:57+07:00` (commit `439f6cd`).
- Đã làm:
  - `app/generation/refusal.py`: `NO_CONTEXT_ANSWER`, `REFUSAL_CORES` = `"chưa tìm thấy thông tin này"`, `"không tìm thấy thông tin này"`, `"chỉ hỗ trợ các câu hỏi liên quan đến ptit"`; `normalize_refusal_text`; `is_refusal(answer, valid_ids=None)` — bỏ `*_\``, tách câu, gộp phần chỉ có `[n]` vào câu trước ("… tài liệu. [2]"), câu đầu chứa lõi và phần sau câu đầu không có `[n]` hợp lệ. `valid_ids=None` = mọi `[n]` coi là hợp lệ (dùng sau khi đã chuẩn hóa).
  - `_normalize_answer_citations`: không bao giờ thêm `[n]`; từ chối thì bỏ mọi `[n]`, còn lại bỏ `[n]` không hợp lệ (kèm khoảng trắng/tab ngay trước để không còn "tài liệu ."). Giữ tên/chữ ký.
  - `rag_chain.answer`: `sources = [] if is_refusal(answer) else public_citations(...)`; `NO_CONTEXT_ANSWER` import lại từ `refusal` (đường import cũ vẫn chạy). `answer_with_llm`/stream khi không có context dùng `NO_CONTEXT_ANSWER` thay câu "Mình chưa tìm thấy thông tin phù hợp…".
  - `routes.py` (`_iter_chat_stream_events`): literal thay bằng hằng số; chuẩn hóa câu trả lời trước khi dựng `assistant_metadata`, câu từ chối thì `sources = []` cho cả event `done`, metadata lưu và `state.sources`; `stream_error`/ngắt giữa chừng giữ hành vi cũ. `contexts`/`retrieval_debug` vẫn lưu.
  - `build_context_prompt`: thêm dòng "Câu từ chối khi ngữ cảnh không có thông tin để trả lời: …".
- Quyết định: thêm lõi "không tìm thấy thông tin này" (biến thể LLM hay dùng). Không đổi `SYSTEM_PROMPT`.
- Kiểm tra: `test_refusal.py` (13 biến thể từ chối, trả lời một phần, `[n]` không hợp lệ sau cụm từ chối), `test_prompts.py`, `test_rag_chain.py`, `test_chat_stream_errors.py` (event `done` + metadata lưu); toàn bộ backend 1303 passed lúc đó.

### S-02 — agent-claude

- Cập nhật lúc: `2026-11-08T10:57:17+07:00` (commit `8cc5c4a`; sửa thêm ở `c4bcd78`, xem S-05b).
- Đã làm: `app/ingestion/legal_units.py` — `extract_article` (giữ nguyên quy tắc cũ), `extract_legal_units(heading, section_path, text, open_clause=None) -> LegalUnits(article, clauses, points, last_clause)`, `clean_legal_text`. Không có Điều → không Khoản/Điểm. Bỏ heading markdown, dòng bảng `|…` và khối `<table>…</table>`. Dòng "Điều N" (không phải heading) trong thân đóng Khoản đang mở. `citations.py` bỏ regex cũ, gọi hàm này.
- Số đo trên index local (quyết định theo hợp đồng): trong Điều có 434 dòng `N.`, 0 dòng `N)`; ngoài Điều 25 dòng `N.`, 2 dòng `N)`; Điểm `a)` 463 trong Điều. → bỏ dạng `N)` khỏi Khoản. 387 chunk có Điều đều có Điều ở heading; 0 chunk có `<table>`.
- Kiểm tra: `test_legal_units.py`, `test_citations.py` (Điều 33/Điều 12 cũ vẫn xanh, thêm danh sách ngoài Điều và bảng). Diff locator tạm thời sau S-02 (chưa metadata): chỉ `removed_non_article` (56 + 8 cặp), 0 vi phạm.

### S-03 — agent-claude

- Cập nhật lúc: `2026-11-08T11:01:55+07:00` (commit `46bb3d4`).
- Đã làm: `Chunk`/`ParentChildChunk` thêm `legal_article`, `legal_clauses: tuple`, `legal_points: tuple` (mặc định rỗng). `split_parent_child` mang `open_clause` qua mọi child của section (cả khi nhiều parent); `_split_section` (đường `split_text`) cũng vậy. `legal_units.legal_metadata`/`copy_legal_metadata`/`LEGAL_METADATA_KEYS`; `_chunk_records` ghi khóa; `_format_chunk_context` và snapshot BM25 chép khóa nếu có; `collapse_parent_results` thay khóa cùng `evidence_text` (xóa khóa cũ nếu child mới không có). RRF/multi-query/reranker chép nguyên dict nên không phải sửa. `citations._citation_metadata` dùng metadata khi có khóa `legal_clauses`, ngược lại gọi `extract_legal_units` không có `open_clause`.
- Kiểm tra văn bản chunk không đổi: so `split_parent_child` (2048/256/1024/128/120 và 400/0/200/40/60) và `split_text` (1024/128/0 và 300/50/60) của chunker ở `e6981f1` với bản mới trên mọi `tests/fixtures/**/*.md` và `parsed_text` của index local: 6 đầu vào, 10146 chunk, 0 lần chạy lệch (so `text`, `index`, heading, `section_path`, parent fields). Backfill dry-run cũng khớp id/`text` 1010/1010 chunk DB.
- Test: `test_legal_metadata.py` (child giữa Khoản, mục không phải Điều, `split_text`, `_chunk_records`, vector, BM25 `_load_chunks` với session giả, parent-child, citation ưu tiên metadata).

### S-04 — agent-claude

- Cập nhật lúc: `2026-11-08T11:06:12+07:00` (commits `e7a5134`, `bdc6d0f`).
- Đã làm: `scripts/refresh_legal_metadata.py` (dry-run mặc định, `--apply`; trả 1 nếu có tài liệu bị bỏ qua). Tách `rechunk_matching_db(document, rows)` trong `refresh_search_text.py` để hai script dùng chung đúng một điều kiện khớp (id + `text`) — lý do: tránh hai bản sao logic khớp DB lệch nhau; `test_refresh_search_text.py` vẫn xanh. Ghi bằng cách gán dict mới (cột JSON không theo dõi thay đổi tại chỗ), chỉ gộp 3 khóa.
- Index local: sao lưu `chunk_metadata` (1010 dòng) vào thư mục tạm của phiên trước khi ghi. Lần 1 (`e7a5134`): 1010 chunk cần ghi, 0 bỏ qua; ghi 1010. Lần 2 (sau sửa Khoản giữa dòng, chưa commit → commit `c4bcd78`): 118 chunk đổi; lần 3 (đánh số lại): 7 chunk đổi. Kết quả cuối: 493 chunk có Điều, 328 có Khoản; dry-run lại: 0 cần ghi. Fingerprint kho không đổi (`d33ac7329944…`).
- Vận hành: backend đang chạy phải khởi động lại để BM25 đọc metadata mới; môi trường khác chạy `refresh_legal_metadata --apply`.

### S-05b — agent-claude

- Cập nhật lúc: `2026-11-08T11:13:19+07:00` (commit `c4bcd78`).
- Lượt 1 (sau S-04, `e7a5134`): 0 vi phạm AC-05, `other` 0, nhưng kiểm tay 15 mẫu thấy Khoản kế thừa sai: bản LlamaParse gộp Khoản 2–5 vào một đoạn ("… Hội đồng. 5. Hai tuần …"), chunk sau nhận "Khoản 1". Đo: 170 dấu `N.` giữa dòng (sau dấu kết câu, trước chữ hoa) trong các chunk thuộc Điều.
- Sửa (`c4bcd78`): nhận Khoản giữa dòng khi đúng số kế tiếp Khoản đang mở; số khác → Khoản đang mở thành không rõ (`None`, không kế thừa tiếp). Kế thừa khi có nội dung (đoạn văn hoặc Điểm) trước dấu Khoản đầu tiên — mở rộng hợp đồng cũ ("dấu mốc đầu là Điểm hoặc không có Khoản"), vì đoạn tiếp nối đứng trước dấu Khoản cũng thuộc Khoản đang mở. Lượt 2 lộ 1 `other`: chunk mở đầu bằng dòng tiêu đề không phải heading rồi đánh số lại từ 1 → thêm quy tắc: dấu Khoản đầu tiên ≤ Khoản kế thừa thì bỏ Khoản kế thừa. Thêm nhóm phân loại `added_inline_clause` trong script diff.
- Kết quả cuối (`c4bcd78`, index đã backfill): xem bảng trong `documents/rag-eval/README.md` mục RAG-22; 0 vi phạm AC-05, `other` 0 ở cả hai bộ. 1 câu (`d26_g3_051`) đổi chỗ 2 context trùng nội dung (`parent-186`/`parent-191`: cùng text, search_text, embedding) — Postgres phá hòa theo thứ tự vật lý, đổi sau `UPDATE`; ghép theo `chunk_id` nên không ảnh hưởng.

### S-06 — agent-claude

- Cập nhật lúc: `2026-11-08T11:06:12+07:00` (commit `e3356c0`).
- Đã làm: `frontend/src/lib/citations.js` (`hasCitedSource`, `sourcesLabel`), `ChatView.jsx` dùng `sourcesLabel(message.content, message.sources)`. Không đặt trong `lib/markdown.js` vì module đó được tải lazy cùng `MarkdownView` (`check:bundle`); hàm bỏ `[n]` trong code block/inline code giống plugin chip.
- Kiểm tra: `citations.test.js`, 3 test mới trong `ChatView.test.jsx`; toàn bộ vitest 217 passed; `npm run check:bundle` đạt (chat 83.56 kB gzip).

### S-07 — agent-claude

- Cập nhật lúc: `2026-11-08T11:15:39+07:00`.
- Đã làm: `locators_after_*.json`, `locator_diff_*.json` chụp lại ở `c4bcd78`; mục "RAG-22" trong `documents/rag-eval/README.md`; cập nhật năm file task; chuyển task `in_review`.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-agent-claude-001 — S-01…S-07

- Từ / đến: `agent-claude` / reviewer (ưu tiên reviewer độc lập do người dùng chỉ định).
- Đã hoàn tất: S-01…S-07.
- File/branch/commit: nhánh `feat/rag22-citation-accuracy`, `4ce8bad..HEAD` (bảng ở trên); push và mở PR vào `dev` theo yêu cầu người dùng `2026-11-08`.
- Kiểm chứng: `verification.md` V-01…V-06 đều `passed`.
- Review: `review.md` — `self_review`, kết luận `approved`; chưa có review độc lập.
- Hạn chế / còn lại: giới hạn ghi trong README mục RAG-22 và `review.md`; môi trường khác cần chạy `refresh_legal_metadata --apply` và khởi động lại backend; thẻ Notion RAG-22 chưa cập nhật.
- Bước tiếp theo: người dùng xem lại, quyết định review độc lập, push và mở PR vào `dev`.
