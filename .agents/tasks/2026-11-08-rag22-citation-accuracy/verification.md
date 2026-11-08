# Verification: 2026-11-08-rag22-citation-accuracy

- Verifier: `agent-claude` (cũng là người triển khai).
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `feat/rag22-citation-accuracy` tại `c4bcd78` (mã); báo cáo `documents/rag-eval/rag-22/*` chụp ở `c4bcd78`; working tree chỉ thêm các file stat/CRLF có sẵn trên `dev` (không đổi nội dung).
- Môi trường: Windows 11, Python 3.11.5 (`backend/.venv`), Node v24.14.0, Postgres + pgvector local (1 tài liệu Sổ tay D26 LlamaParse, 1010 chunk, fingerprint `d33ac7329944…`), LLM `OpenAICompatibleProvider` đã cấu hình trong `.env` local.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (không tự gắn citation)

- Người thực hiện / thời gian: agent-claude / `2026-11-08T11:13:19+07:00` (lần chạy toàn bộ gần nhất trên mã `c4bcd78`).
- Loại: test tự động + chạy thật với LLM.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `python -m pytest tests/test_prompts.py tests/test_refusal.py tests/test_rag_chain.py tests/test_chat_stream_errors.py -q`; script tạm gọi `rag_chain.answer` cho 10 câu đầu `ptit_ragas_100` + 1 câu trả lời một phần + 1 câu không có trong tài liệu.
- Kỳ vọng: câu không có `[n]` (kể cả "Tài liệu chưa đề cập …") trả nguyên, không thêm `[n]`; `[n]` không hợp lệ bị xóa, hợp lệ giữ nguyên; `sources` vẫn trả với câu không phải từ chối; đúng ở `answer_with_llm`/`/chat` (`rag_chain.answer`) và `/chat/stream` (event `done` + metadata lưu).
- Kết quả thực tế: `test_answer_citations_are_limited_to_provided_sources` (đổi: `"Thông tin học phí [9]."` → `"Thông tin học phí."`), `test_valid_citations_are_kept_and_none_are_added`, `test_rag_chain_keeps_uncited_answer_and_sources_without_adding_citation`, `test_stream_done_keeps_uncited_answer_and_sources` (event `done` và `assistant.metadata.sources` đều có 1 nguồn, câu trả lời không có `[n]` thêm) đều xanh. LLM thật: 10/10 câu có nội dung chứa `[n]` hợp lệ, không câu nào bị gắn thêm; câu trả lời một phần ("cảnh báo học tập … mức phạt tiền") giữ `[1]` và 4 `sources`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest; output script tạm trong phiên (không lưu vào repo).

### V-02 — AC-02 (nhận diện câu từ chối)

- Người thực hiện / thời gian: agent-claude / `2026-11-08T11:13:19+07:00`.
- Loại: test tự động + review mã + LLM thật.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `python -m pytest tests/test_refusal.py tests/test_prompts.py tests/test_chat_stream_errors.py -q`; `rg "Chưa tìm thấy thông tin" backend/app` (chỉ còn trong `refusal.py`).
- Kỳ vọng: một hằng số dùng ở `llm.py`, `rag_chain.py`, `routes.py`, có nguyên văn trong `build_context_prompt`; các biến thể (thêm chữ trước/sau, hoa/thường, dấu câu, `**`, `[n]` dính kèm, từ chối ngoài phạm vi có biến thể) → không `[n]`, `sources` rỗng; câu mở đầu bằng cụm từ chối rồi có nội dung kèm `[n]` hợp lệ là trả lời một phần.
- Kết quả thực tế: 13 biến thể trong `test_refusal_variants_lose_citations_and_are_recognized` xanh; `test_partial_answer_with_valid_citation_after_refusal_phrase_is_not_refusal` xanh; `test_context_prompt_states_both_refusal_sentences` xanh; `test_rag_chain_llm_refusal_has_no_citation_and_no_sources` và `test_stream_refusal_has_no_citation_and_no_sources` (event `done` + metadata lưu `sources == []`) xanh. Literal chỉ còn ở `refusal.py`. LLM thật: câu "hồ bơi khuôn viên Hà Đông" qua gate (4 context), LLM trả đúng `NO_CONTEXT_ANSWER`, `sources == []`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest; `rg` trong phiên.

### V-03 — AC-03 (Khoản/Điểm chỉ trong Điều)

- Người thực hiện / thời gian: agent-claude / `2026-11-08T11:13:19+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `python -m pytest tests/test_legal_units.py tests/test_citations.py -q`.
- Kỳ vọng: danh sách `1.`/`2)`/`a)`/`b.` ngoài Điều → `clauses == []`, `points == []`, `locator` = heading; dòng bảng không thành Khoản; test Điều 33/Điều 12 cũ xanh.
- Kết quả thực tế: xanh (`test_numbered_steps_outside_an_article_are_not_clauses_or_points`, `test_numbered_table_cells_are_not_clauses`, `test_numbered_lists_outside_an_article_are_not_clauses`, `test_numbered_lines_inside_tables_are_not_clauses`, Điều ở heading/section_path/dòng đậm đầu text, 4 test cũ). Golden set: Khoản/Điểm ngoài Điều 56 → 0 (`ptit_rag_300`) và 8 → 0 (`ptit_ragas_100`).
- Trạng thái: `passed`.
- Bằng chứng: output pytest; `documents/rag-eval/rag-22/locator_diff_*.json` (`summary_*.with_clauses_outside_article`).

### V-04 — AC-04 (metadata lúc chunking, đường đi, backfill)

- Người thực hiện / thời gian: agent-claude / `2026-11-08T11:13:19+07:00`.
- Loại: test tự động + chạy script trên index local + so sánh chunker cũ/mới.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `python -m pytest tests/test_legal_metadata.py tests/test_refresh_legal_metadata.py tests/test_refresh_search_text.py -q`; `python -m scripts.refresh_legal_metadata` rồi `--apply` rồi dry-run lại; script tạm so chunker `e6981f1` với bản mới.
- Kỳ vọng: child mới có `legal_article/clauses/points`; child giữa Khoản nhận Khoản đang mở; mục không phải Điều `legal_clauses == []`; metadata đi qua vector, BM25, parent-child (theo child bằng chứng); `public_citations` dùng metadata, dự phòng khi thiếu; backfill có dry-run/`--apply`, bỏ qua tài liệu lệch `text`; văn bản chunk không đổi.
- Kết quả thực tế: 9 test `test_legal_metadata.py` + 3 test backfill xanh (dry-run không ghi; `--apply` chỉ đổi 3 khóa, `text`/`search_text`/embedding/khóa khác giữ nguyên; tài liệu sửa `text` bị bỏ qua, exit 1). Index local: 0 tài liệu bỏ qua, 1010/1010 chunk khớp; dry-run sau cùng "0 chunk cần ghi". Chunker cũ vs mới: 6 đầu vào (fixture + `parsed_text` DB), 10146 chunk, 0 khác biệt.
- Trạng thái: `passed`.
- Bằng chứng: output pytest; output script (ghi trong `implementation.md` S-03, S-04).

### V-05 — AC-05 (locator golden set)

- Người thực hiện / thời gian: agent-claude / `2026-11-08T11:15:39+07:00`.
- Loại: script đánh giá + kiểm tay.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `python -m scripts.dump_citation_locators --dataset tests/fixtures/ptit_{rag_300,ragas_100}.json --out documents/rag-eval/rag-22/locators_{before,after}_*.json` (before ở `e6981f1` chưa backfill, after ở `c4bcd78` đã backfill), `--diff before after --out locator_diff_*.json`.
- Kỳ vọng: mọi citation có Điều ở bản trước giữ `article`, không mất Khoản; thay đổi được phân loại; `other` = 0 hoặc giải thích; ghi fingerprint, dataset sha256, commit.
- Kết quả thực tế: `ptit_rag_300` 3000 cặp: 2308 unchanged, 56 removed_non_article, 286 added_inherited_clause, 350 added_inline_clause, 0 other, 0 vi phạm, 0 unmatched, 1 câu đổi chỗ 2 context trùng nội dung (giải thích trong README). `ptit_ragas_100` 1000 cặp: 771 / 8 / 80 / 141 / 0, 0 vi phạm, 0 unmatched, 0 đổi thứ tự. Fingerprint `d33ac7329944…` cả hai lần; sha256 `af2a7a06d823…`, `fa9d2d64f404…`; embedding cache 0 miss. Kiểm tay: lượt 1 (15 mẫu) phát hiện kế thừa sai do Khoản giữa dòng → sửa ở `c4bcd78`, chụp lại; lượt 2 (12 mẫu, seed 22) đúng 12/12.
- Trạng thái: `passed`.
- Bằng chứng: `documents/rag-eval/rag-22/`, mục RAG-22 trong `documents/rag-eval/README.md`.

### V-06 — AC-06 (tương thích)

- Người thực hiện / thời gian: agent-claude / `2026-11-08T11:13:19+07:00`.
- Loại: test tự động + review mã.
- Thư mục chạy: `backend`, `frontend`.
- Lệnh / thao tác: `python -m pytest -q` (backend); `npx vitest run`; `npm run check:bundle`; `git diff e6981f1..HEAD -- backend/app/api/schemas.py frontend/src/lib/markdown.js`.
- Kỳ vọng: schema `Source` không đổi; pytest toàn bộ xanh; test `ChatView`/`markdown` xanh; nhãn "Nguồn liên quan" khi không có chip `[n]` hợp lệ, "Nguồn trích dẫn" khi có.
- Kết quả thực tế: backend `1335 passed, 24 skipped`; frontend `32 files, 217 tests passed`; `check:bundle đạt` (chat 83.56 kB gzip ≤ 128.41 kB); diff `schemas.py`, `markdown.js` rỗng. Test nhãn: `ChatView.test.jsx` "nhãn khối nguồn (RAG-22)" (3 test) + `lib/citations.test.js` (3 test) xanh. `test_chat_error_privacy.py` (monkeypatch `_normalize_answer_citations`) xanh.
- Trạng thái: `passed`.
- Bằng chứng: output pytest/vitest/check:bundle trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- S-05b lượt 1: kiểm tay phát hiện Khoản kế thừa sai (bản parse gộp Khoản vào một đoạn); lượt 2 lộ 1 `other` (đánh số bắt đầu lại). Đã sửa ở `c4bcd78`, chạy lại backfill, toàn bộ pytest và chụp lại locator "sau"; kết quả ở V-05 là lần chạy sau sửa.
- Kiểm tay `/chat/stream` qua HTTP với LLM thật: `not_run` (để không ghi hội thoại thử vào DB local). Luồng stream được kiểm bằng test với stream giả (V-01, V-02); phần sinh câu trả lời thật đã kiểm qua `rag_chain.answer` (cùng `answer_with_llm`, cùng `_normalize_answer_citations`/`is_refusal`).
- Tỉ lệ câu trả lời không có `[n]` sau khi bỏ tự gắn: đo trên mẫu nhỏ 10 câu (0/10); chưa đo trên toàn bộ golden set.

## Kết luận

- Tiêu chí đã đạt: AC-01…AC-06.
- Tiêu chí chưa đạt/chưa xác minh: không có; kiểm tay HTTP `/chat/stream` với LLM thật chưa chạy (ghi ở trên).
- Đề xuất: bàn giao reviewer; nếu người dùng muốn review độc lập thì chỉ định reviewer trước khi mở PR.
