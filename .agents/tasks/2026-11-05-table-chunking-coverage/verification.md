# Verification: 2026-11-05-table-chunking-coverage

- Verifier: `claude-code-agent`.
- Trạng thái tổng: `passed` cho V-01…V-06, V-08; V-07 `failed` ở vế cải thiện bảng (ghi rõ dưới).
- Bản được kiểm tra: nhánh `feat/table-chunking-coverage` (sau S-01…S-07), commit đang làm việc ngày `2026-11-05`.
- Môi trường: Windows 11, Python 3.11 (`backend/.venv`), chạy từ `backend/`.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: test tự động + đo trên D26.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `python -m pytest tests/test_chunker.py -q -k "compact or stray or delimiter"`; script đo khối bảng trên D26.
- Kỳ vọng: test bảng compact xanh; D26 ≥ 400 khối bảng, 0 mảnh `|…|` không header xử lý như văn xuôi.
- Kết quả thực tế: 3 test mới xanh; D26 có 424 khối compact, gộp ngắt trang còn 400 khối bảng, 0 mảnh văn xuôi chứa `|`.
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_chunker.py::test_compact_delimiter_tables_are_recognized_as_tables` (+2); số liệu đo ghi trong `implementation.md` (S-01).

### V-02 — AC-02

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `python -m pytest tests/test_chunker_table_coverage.py -q`.
- Kỳ vọng: 0 hàng thiếu, 0 hàng cắt dở trên mọi fixture và trên D26.
- Kết quả thực tế: 8 passed — 6 fixture (benchmark, compact, bảng dài, hàng rất dài, ngắt trang lặp header, HTML) + D26 (chạy thật trên file data/) đều 0 vi phạm; test D26 trên bản parse Docling PDF cũng 0 vi phạm (probe ngoài).
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_chunker_table_coverage.py` (gồm test hồi quy xé hàng
  `test_short_tail_after_table_does_not_steal_table_row` đã xác minh rớt trên mã cũ).

### V-03 — AC-03

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: cùng file test V-02 (kiểm `missing_header`).
- Kỳ vọng: mọi child chứa hàng dữ liệu bảng có header của bảng đó.
- Kết quả thực tế: 0 `missing_header` trên mọi fixture và D26 (cả `.md` và `.pdf`).
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_chunker_table_coverage.py`; `check_chunks --data/--db` không có `table_chunk_missing_header`.

### V-04 — AC-04

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: test ghép bảng ngắt trang trong `tests/test_chunker.py`.
- Kỳ vọng: bảng 2 trang cùng header / trang sau không header được gộp; hai bảng khác header hoặc khác số cột không bị gộp.
- Kết quả thực tế: 6 test gộp/không-gộp xanh; mảnh bảng cuối < 3 hàng gộp trong hard limit (test `check_chunks` liên quan xanh).
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_chunker.py` (khối S-03).

### V-05 — AC-05

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: test tự động + chạy script.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `python -m pytest tests/test_check_chunks.py -q`; `python -m scripts.check_chunks --data ..\data --strict`.
- Kỳ vọng: mã lỗi mới được phát hiện trên dữ liệu lỗi cố ý; `data/` không có vi phạm bảng; test cảnh báo pipeline xanh.
- Kết quả thực tế: 5 test mã lỗi mới + 3 test cảnh báo pipeline xanh; `--data` 0 vi phạm bảng (trước sửa có 6 missing + 4 broken trên parse Docling); còn 1 finding cũ `chunk_starts_mid_word` (`logo: PTIT`) nên `--strict` trả 1 — đúng hành vi (có lỗi thì trả 1), không phải vi phạm bảng.
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_check_chunks.py`, `tests/test_document_pipeline.py`, output `check_chunks` ghi trong `implementation.md` (S-06).

### V-06 — AC-06

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: test tự động + dry-run D26.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: test cleaner; đếm dòng `|` bị cleaner bỏ trên D26.
- Kỳ vọng: bảng dữ liệu sau "MỤC LỤC" được giữ; bảng mục lục D26 vẫn bị bỏ (85 dòng như trước, chênh lệch phải giải thích).
- Kết quả thực tế: 3 test cleaner mới xanh (bảng mục lục compact bị lọc, bảng dữ liệu sau mục lục được giữ + kết thúc section, bảng HTML mục lục/dữ liệu); D26 bỏ đúng 87 dòng `|` (85 theo cách đếm nội dung duy nhất + 2 dòng `|-|-|` trùng nội dung với bảng phần khác), tất cả trong dòng 39–126.
- Trạng thái: `passed`.
- Bằng chứng: `tests/test_chunker.py::test_clean_text_drops_same_pipe_count_on_d26_toc` (+2).

### V-07 — AC-07

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: đo retrieval.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `python -m scripts.eval_retrieval --mode hybrid` (và `--mode bm25`) với `--dataset tests/fixtures/ptit_ragas_100.json` và `--dataset tests/fixtures/table_questions.json`, trước và sau khi chunk lại.
- Kỳ vọng: golden set không giảm hit@4/MRR hybrid; bộ câu hỏi bảng tăng hit@4.
- Kết quả thực tế: golden bm25 giống hệt (0.830/0.768); golden hybrid 0.830→0.820,
  MRR −0.0005 (1 câu `student_card_validity` 4→5 — cùng tập parent cùng thứ tự, nhiễu
  ngưỡng cụm từ chung chung); bảng bm25 0.857→0.857, hybrid 0.786→0.786 (các câu hụt/
  tụt hạng do chunk chứa hàng không vào top-k — cần D-01). Chi tiết xem
  `documents/rag-eval/table-chunking/README.md` (+ 8 JSON).
- Trạng thái: `failed` (vế cải thiện bảng chưa đạt; vế không thụt lùi đạt về thực chất).
- Bằng chứng: `documents/rag-eval/table-chunking/before_*.json`, `after_*.json`, `README.md`.

### V-08 — AC-08

- Người thực hiện / thời gian: `claude-code-agent` / `2026-11-05T23:42:51+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `python -m pytest -q -p no:cacheprovider`.
- Kỳ vọng: toàn bộ xanh; ghi số passed/skipped thực tế.
- Kết quả thực tế: 782 passed, 1 skipped (corpus benchmark thiếu file thật — skip theo thiết kế).
- Trạng thái: `passed`.
- Bằng chứng: output pytest full suite.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Đã chạy lại toàn bộ pytest sau mọi thay đổi (780 passed, 1 skipped); `git stash`
  từng dùng để đối chiếu mã cũ đã gây conflict với stash lạ có sẵn — đã khôi phục đầy
  đủ, không mất thay đổi; từ đó chỉ đối chiếu bằng `git show HEAD:...` và file backup.
- V-07 vế cải thiện hit@4 bảng chưa đạt (xem V-07): cần task tiếp theo (D-01).

## Kiểm chứng lại — vòng 2 (`2026-11-06T21:17:16+07:00`, `claude-code-agent`)

Bản kiểm tra: working tree chưa commit trên `feat/table-chunking-coverage`
(HEAD = `dev` = `14c4eb6`; toàn bộ thay đổi S-01…S-07 vẫn chưa commit). Chạy từ `backend/`.

| Kiểm tra | Lệnh / thao tác | Kết quả thực tế | Trạng thái |
|---|---|---|---|
| R2-1 full suite (AC-08) | `python -m pytest -q -p no:cacheprovider` | 781 passed, 1 failed, 1 skipped. Test rớt: `tests/test_dataset_api.py::test_dataset_chunk_parse_validation` — gọi OpenAI embedding thật qua `/api/retrieval/test`, lỗi `httpx.ConnectError: CERTIFICATE_VERIFY_FAILED self-signed certificate` (mạng máy hiện tại); file test và đường gọi (`rag_chain` → embedding) không thuộc diff. Skip: `test_chunker_tables_benchmark.py` (thiếu file benchmark thật, theo thiết kế). | `passed` có ghi chú (lỗi môi trường, không phải hồi quy) |
| R2-2 test bảng (AC-01…AC-06) | `pytest tests/test_chunker_table_coverage.py tests/test_chunker.py tests/test_check_chunks.py tests/test_document_pipeline.py -q -rs` | 111 passed, 0 skipped — test D26 `test_data_file_d26_has_no_table_coverage_issues` chạy thật trên `data/`. | `passed` |
| R2-3 `check_chunks --data` (AC-02/03/05) | `python -m scripts.check_chunks --data ../data --strict` | 10 tài liệu, 3.697 chunk; 0 `table_row_*`/`table_chunk_missing_header`; còn 1 `chunk_starts_mid_word` (`logo: PTIT`) có từ trước; exit 1 (đúng hành vi `--strict`). Khớp V-05. | `passed` |
| R2-4 `check_chunks --db` (AC-02/03) | `python -m scripts.check_chunks --db --strict` | DB hiện có **2 tài liệu / 2.020 chunk** (README S-07 ghi 1 tài liệu / 1.010 chunk — tài liệu `7b99bad5` đã được chunk sau lần đo); 0 vi phạm bảng; 2 `chunk_starts_mid_word` (`logo: PTIT`, mỗi tài liệu 1). | `passed` |
| R2-5 fuzz bất biến (AC-02/03/04) | script scratchpad `fuzz_tables.py` (không thuộc repo): 300 tài liệu ngẫu nhiên — bảng `---` và `\|-\|`, ô trống, hàng dài, ngắt trang lặp/không lặp header, HTML thiếu `</tr>`, nhiều `<tbody>`, `<tfoot>`, văn xuôi xen giữa; `split_parent_child(2048,256,1024,128,120)`; kiểm tra **độc lập** (mỗi hàng sinh ra nằm nguyên trên một dòng của child có header) + `find_table_coverage_issues` | 0/300 seed vi phạm ở cả hai cách kiểm tra. | `passed` |
| R2-6 số liệu eval (AC-07) | đọc `documents/rag-eval/table-chunking/*.json` | Khớp README: golden bm25 0.83/0.767762 = trước; hybrid 0.83→0.82, MRR 0.734611→0.734111; bảng bm25 0.857143 giữ nguyên, hybrid 0.785714 giữ nguyên, MRR 0.783333→0.776984. Không chạy lại eval (cần OpenAI API, mạng hiện tại lỗi SSL; index cũng đã đổi so với lúc đo). | `failed` (giữ nguyên kết luận V-07) |

Ghi chú cho người đọc sau:

- Số test trong nhật ký không nhất quán (`780` ở vài chỗ, `782` ở chỗ khác). Thực tế vòng 2:
  783 test thu thập = 781 passed + 1 failed (môi trường) + 1 skipped ⇒ con số `782 passed,
  1 skipped` đúng khi có mạng tới OpenAI.
- Index local đã thay đổi sau S-07 (1.010 → 2.020 chunk) nên `after_*.json` không còn là
  baseline "cùng index" cho task `2026-11-05-table-search-context`; task đó phải đo lại
  baseline trên index hiện tại trước khi sửa.
- Thay đổi chưa commit: cần commit trên nhánh trước khi mở PR.

## Kết luận

- Vòng 2 xác nhận lại AC-01…AC-06 và AC-08 (AC-08 với 1 lỗi môi trường đã giải thích); AC-07 vẫn chưa đạt.
- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-04, AC-05, AC-06, AC-08.
- Tiêu chí chưa đạt/chưa xác minh: AC-07 (vế tăng hit@4 bảng; vế golden không thụt lùi đạt về thực chất).
- Đề xuất: self-review diff; mở task tiếp theo D-01 (`2026-11-05-table-search-context`); task này giữ `in_review`, chưa `done`.
