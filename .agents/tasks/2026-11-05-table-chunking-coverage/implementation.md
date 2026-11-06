# Implementation: 2026-11-05-table-chunking-coverage

## Tổng quan triển khai

Nhánh `feat/table-chunking-coverage` (tách từ `dev` tại `14c4eb6`, đúng quy ước;
phiên lập kế hoạch ở `feat/fix-chunk-pagination` đã được người dùng đồng ý rời đi,
2 commit frontend của nhánh cũ giữ nguyên tại đó). S-01…S-07 hoàn tất trên nhánh mới;
D-01 hoãn sang task tiếp theo, D-02 đã duyệt và thực hiện. Toàn bộ test backend xanh
(782 passed, 1 skipped).

## Nhật ký theo nhiệm vụ

### Điều tra trước khi lập kế hoạch — claude-code-agent

- Cập nhật lúc: `2026-11-05T22:30:22+07:00`.
- Đã làm: đo chunker hiện tại (`split_parent_child` với cấu hình local `CHUNK_SIZE=2048`, `CHILD_CHUNK_SIZE=1024`, `MIN_CHILD_CHUNK_CHARS=120`) trên dữ liệu tổng hợp và trên file Sổ tay D26 đã parse bằng LlamaParse. Không sửa file nào trong repo; script đo đặt ở scratchpad phiên.
- Kết quả dữ liệu tổng hợp (120 hàng/bảng):

  | Trường hợp | Hàng mất trong child |
  |---|---|
  | Bảng Markdown dài `---` | 0 |
  | Bảng ngắt trang không header / lặp header | 0 (nhưng phần sau mất header) |
  | Hàng rất dài | 0 |
  | HTML nhiều `<tbody>` | 90/120 |
  | HTML `<tr>` thiếu `</tr>` | 120/120 |
  | HTML có `<tfoot>` | 1/1 hàng tfoot |
  | Bảng ngay sau "MỤC LỤC" | 120/120 (cleaner bỏ) |

- Kết quả D26 (`data/datasets/*/Sổ tay sinh viên D26 _1_ _1_.md`, 584.982 ký tự, 3.734 dòng `|` không phải dòng phân cách; 85 dòng cleaner bỏ, các dòng đã xem đều thuộc bảng mục lục):

  | Chỉ số | Hiện tại | Vá tạm `:?-+:?` |
  |---|---|---|
  | Khối bảng nhận diện | 0 | 424 |
  | Mảnh `|…|` xử lý như văn xuôi | 421 | 0 |
  | Số child | 1.002 | 1.013 |
  | Dòng hàng bị cắt dở trong child | 32 | 0 |
  | Hàng không nguyên vẹn trong child nào (/3.653) | 2 | 0 |
  | Độ dài child p50 / p95 / max | 585 / 995 / 1.024 | 569 / 999 / 1.824 |

- Nguyên nhân gốc: `compact_markdown_tables: True` (`backend/app/parsers/llamaparse.py:170`) sinh `|-|-|`; `_starts_markdown_table` (`backend/app/ingestion/chunker.py:530`) đòi ≥ 3 gạch.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: xem `plan.md`.
- Kiểm tra đã chạy: chỉ script đo ở trên; chưa chạy pytest.
- Còn lại/blocker: chờ người dùng duyệt plan và D-01/D-02.

### S-01 — claude-code-agent

- Cập nhật lúc: `2026-11-05T23:42:51+07:00`.
- Đã làm: `_starts_markdown_table` chấp nhận `:?-+:?`; fixture mới
  `chunker-tables-llamaparse-compact.md` (trích nguyên văn bảng liên hệ Khoa Cơ bản 1
  và bảng điểm rèn luyện Tiêu chí 4–5 có hàng 5.1); 3 test mới trong `test_chunker.py`
  (nhận diện bảng compact, tách theo hàng + lặp header, dòng `|-|` lạc không thành bảng).
- Kết quả D26: khối bảng nhận diện 0→424, mảnh văn xuôi chứa `|` 424→0, child 1.002→1.013,
  hàng vỡ 32→0, hàng mất 2→0, child max 1.024→1.824 (khớp cột "vá tạm" lúc điều tra).
- Kiểm tra: test chunker xanh.

### S-02 — claude-code-agent

- Đã làm: API nội bộ `TableCoverageIssue(kind, child_index, excerpt)` +
  `find_table_coverage_issues(cleaned_text, chunks)` trong `chunker.py` (kiểm tra
  missing/broken/missing_header cho cả Markdown và HTML; `_html_table_rows` tách dùng
  chung cho splitter và checker); `test_chunker_table_coverage.py` mới (6 case tham số
  hoá + excerpt bound + test D26 skip-khi-thiếu-data).
- Sửa lỗi checker trong lúc làm: hàng `<thead>` bị gắn cờ `broken` oan → tách tập
  `allowed_html_rows` (body + thead + tfoot + caption).
- Kiểm tra: 8 passed (D26 chạy thật, 0 vi phạm).

### S-03 — claude-code-agent

- Đã làm: `_merge_page_break_tables` trong `_split_blocks` (gộp khối bảng liền kề
  cùng header sau chuẩn hoá khoảng trắng/`<br/>`, hoặc khối tiếp theo toàn dòng `|…|`
  không delim cùng số cột; khối văn bản thật xen giữa thì không gộp); 6 test mới
  (gộp cùng header / tiếp nối không header / không gộp khi khác header, khác số cột,
  có văn xuôi xen giữa, mảnh header-only không thành child riêng).
- D26 sau S-03: 424→400 khối bảng (24 mảnh ngắt trang được gộp); 2 header biến thể
  (khác `<br/>`, cùng chuẩn hoá) được thay bằng 1 header — checker bất biến vẫn 0
  (header không thuộc bất biến hàng dữ liệu AC-02).
- Kiểm tra: test chunker xanh.

### S-04 — claude-code-agent

- Đã làm: viết lại `_split_long_html_table` trên `_split_html_table_parts`
  (hàng tách theo thẻ `<tr>` mở → chịu `</tr>` thiếu; lấy hàng từ mọi `<tbody>`;
  giữ `<caption>` mọi mảnh, `<tfoot>` mảnh cuối; không tách được hàng nào thì giữ
  nguyên bảng); checker cập nhật (tách vùng thead/tbody/tfoot riêng, bỏ kiểm tra
  đếm `<tr` vì thiếu thẻ đóng giờ là hợp lệ); 4 test mới trong `test_chunker.py`.
- Đối chiếu mã cũ (checkout tạm `HEAD:chunker.py`): thiếu `</tr>` giữ nguyên 1 child
  quá khổ (không mất hàng nhưng không tách được); nhiều `<tbody>` mất 80/120 hàng;
  `<tfoot>`/`<caption>` mất khi tách — test mới rớt đúng trên mã cũ (trừ case thiếu
  `</tr>` cần thêm assert tách thành nhiều child để khỏi rỗng).
- Kiểm tra: 65 passed trên các file chunker.

### S-05 — claude-code-agent

- Đã làm: viết lại `_drop_noise_lines` sang vòng lặp index để nhìn trước khối bảng
  trong section "MỤC LỤC": bảng chỉ bị bỏ khi phần lớn (> 0.5) hàng dữ liệu có ô cuối
  là số trang (`_is_toc_like_table`; bỏ qua dòng tiêu đề khi có dòng phân cách, hỗ trợ
  cả bảng HTML); gặp bảng dữ liệu thì kết thúc section mục lục và giữ bảng.
- D26: vẫn bỏ đúng 87 dòng `|` (báo cáo điều tra ghi 85 vì đếm theo nội dung duy nhất —
  2 dòng `|-|-|` trùng với bảng phần khác), tất cả trong dòng 39–126 (vùng mục lục).
- Kiểm tra: 3 test cleaner mới + toàn bộ test cleaner cũ xanh.

### S-06 — claude-code-agent

- Đã làm: `check_chunks.py` thêm 3 mã lỗi (`table_row_broken`, `table_row_missing`,
  `table_chunk_missing_header`), `TableDocGroup` + `check_table_documents`
  (cả `--db` — cần `parsed_text`, và `--data`), cập nhật docstring; `pipeline.py`
  thêm `_log_table_coverage` gọi từ `_chunk_records` (≥ 5 dòng `|` mà 0 bảng được
  nhận diện, hoặc bất biến S-02 báo vi phạm → `logger.warning`, không chặn ingest);
  `count_recognized_tables` public trong `chunker.py`.
- `check_chunks --data ../data`: 0 vi phạm bảng (trước sửa: 6 missing + 4 broken trên
  bản parse Docling — do lỗi xé hàng của `_merge_short_pieces` đã sửa trong S-02/S-03
  mở rộng); còn 1 finding cũ `chunk_starts_mid_word` (`logo: PTIT`).
- Test: 5 test `check_chunks` mới + 3 test cảnh báo pipeline mới.
- Phát hiện thêm ngoài plan (đã sửa, có test hồi quy
  `test_short_tail_after_table_does_not_steal_table_row`, xác minh rớt trên mã cũ với
  đúng hình dính `| 10 |…|HK8 | | 1 | Java…|`): xem mục Trao đổi (1).

### S-07 — claude-code-agent

- Baseline (trước sửa mã, trên index hiện tại 1.013 chunk): `before_bm25.json`
  (hit@4 0.830/MRR 0.768), `before_hybrid.json` (0.830/0.735) trên `ptit_ragas_100.json`;
  fixture mới `table_questions.json` (14 câu, kèm dòng nguồn D26) + baseline
  `before_table_questions_{bm25,hybrid}.json` (bm25 hit@4 0.857, hybrid 0.786).
- Chunk lại (sau D-02 duyệt): `chunk_documents(dataset_id="default")` → 1.010 chunk
  (ước lượng trước: ~1.010 chunk/~117K từ), embed lại toàn bộ, không parse lại.
  `check_chunks --db`: 0 vi phạm bảng (còn 1 `chunk_starts_mid_word` cũ).
- Đo sau: `after_*.json` (4 file). Golden bm25 giống hệt; golden hybrid −1 câu
  (student_card_validity 4→5, cùng nội dung/trật tự — nhiễu ngưỡng cụm từ chung chung
  `thời gian học tập`); bảng bm25/hybrid giữ nguyên hit@4. Kết luận: toàn vẹn hàng đạt,
  không thụt lùi golden về thực chất, nhưng hit@4 bảng chưa tăng (hàng nguyên vẹn
  nhưng chunk chứa hàng không vào top-k) → AC-07 chưa đạt, D-01 là lever tiếp theo.
- Báo cáo: `documents/rag-eval/table-chunking/README.md` (+ 8 JSON, không chạm
  `baseline_*.json` hay `rag-05/06/15/` theo ràng buộc).

## Trao đổi giữa agents

- `2026-11-05T23:42:51+07:00` — `claude-code-agent` (coordinator): người dùng duyệt
  tạo nhánh từ `dev`, hoãn D-01 có điều kiện (mở task tiếp theo nếu hit@4 bảng vẫn
  hụt), đồng ý D-02 (chunk lại + đo retrieval local).
- Trong lúc triển khai phát hiện và xử lý thêm (ngoài dự kiến plan, đều có test):
  1. `_merge_short_pieces` xé hàng bảng: `_steal_trailing_unit` lấy câu cuối của
     mảnh prose+bảng (nối bằng dấu cách) vá vào đầu mảnh bảng kế tiếp → hàng dính
     đôi (`| 10 |…|HK8 | | 1 | Java…|`), hàng gốc mất khỏi index (10 vi phạm trên
     bản parse Docling PDF). Sửa: `_split_units` trả nguyên mảnh khi chứa bảng.
  2. Ô nhiễm log toàn suite: `test_alembic_upgrade_check_and_downgrade_cycle` chạy
     `alembic/env.py` → `fileConfig` disable mọi logger hiện có → 2 test caplog của
     S-06 rớt khi chạy full suite. Sửa gốc: `alembic/env.py` tôn trọng
     `configure_logger=False`; test alembic đặt attribute này (production không đổi).
  3. Hai sự cố thao tác Git (pop nhầm stash lạ của phiên khác gây conflict;
     checkout nhầm đường dẫn) — đã khôi phục đầy đủ, không mất thay đổi, stash của
     người khác giữ nguyên. Rút kinh nghiệm: không dùng `git stash` trong repo này.

## Bàn giao

- Nhiệm vụ đã làm: S-01…S-07 (xem nhật ký dưới), self-review, full pytest xanh (782 passed, 1 skipped).
- File/commit liên quan: nhánh `feat/table-chunking-coverage`; sửa
  `backend/app/ingestion/{chunker,cleaner,pipeline}.py`,
  `backend/scripts/check_chunks.py`, `backend/alembic/env.py`,
  `backend/tests/{test_chunker,test_check_chunks,test_document_pipeline,test_database_postgres}.py`;
  mới `backend/tests/{test_chunker_table_coverage.py,fixtures/corpus/chunker-tables-llamaparse-compact.md,fixtures/table_questions.json}`,
  `documents/rag-eval/table-chunking/` (4 before + 4 after + README).
- Quyết định ảnh hưởng agent khác: D-01 hoãn → task `2026-11-05-table-search-context`
  đã mở sẵn (task + plan); AC-07 chưa đạt vế cải thiện bảng nên task này ở `in_review`.
- Kiểm tra đã chạy: full pytest 780 passed/1 skipped; `check_chunks --data ../data`
  và `--db` đều 0 vi phạm bảng; 8 báo cáo eval trước/sau.
- Còn lại: xử lý nhận xét review (nếu có), chạy lại kiểm tra bị ảnh hưởng, chờ
  coordinator kết luận sau khi D-01 (task tiếp theo) xử lý nốt AC-07.
