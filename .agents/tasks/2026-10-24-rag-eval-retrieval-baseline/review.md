# Review

- Task: `2026-10-24-rag-eval-retrieval-baseline`
- Người review: `zcode-agent` — **self_review** (một agent tự triển khai và tự rà; không phải review độc lập).
- Trạng thái: `approved` trên bản bàn giao cuối (xem mục Kết luận).
- Cập nhật lúc: `2026-10-25T00:07:00+07:00`

## Phạm vi review

Toàn bộ diff: `backend/scripts/eval_retrieval.py`, `backend/tests/test_eval_retrieval.py`, `documents/rag-eval/*`, trang task này. Đối chiếu yêu cầu trong `task.md`, bằng chứng trong `verification.md`.

## Nhận xét

### R-01 — medium, không bắt buộc — Đã xử lý (resolved)

- Vị trí: `eval_retrieval.py::normalize_text` ban đầu.
- Vấn đề: yêu cầu là "bỏ thẻ HTML" nhưng HTML entity (`&nbsp;`, `&amp;`) không được giải mã, có thể làm lệch khớp term trên chunk chứa entity.
- Xử lý: thêm `html.unescape` sau khi lọc thẻ; test `test_normalize_text_strips_html_and_folds_case` phủ case `&nbsp;`.
- Xác nhận: test đạt.

### R-02 — low, không bắt buộc — Đã xử lý (resolved)

- Vị trí: `compare_reports`.
- Vấn đề: file báo cáo thiếu/sai format làm traceback thô; nhóm `overall` in cuối bảng.
- Xử lý: bắt `OSError/JSONDecodeError`, in lỗi ra stderr và trả exit code 2; sắp xếp `overall` lên đầu bảng. Đã chạy lại cả hai nhánh (thiếu file → exit 2; đủ file → bảng đúng thứ tự).

### R-03 — low, không bắt buộc — Trì hoãn (deferred)

- Vấn đề: `--output`/`--embedding-cache` truyền đường dẫn tương đối được giải theo gốc repo (output) hoặc cwd (cache) — nhất quán nhưng dễ gây nhầm như lần chạy smoke rơi vào `storage/` ngoài gốc.
- Hướng theo dõi: nếu có agent khác dùng script, cân nhắc thống nhất giải theo gốc repo cho cả hai và ghi rõ trong `--help`.

### R-04 — low, không bắt buộc — Trì hoãn (deferred)

- Vấn đề: chế độ `full` chỉ được đo với multi-query/reranker TẮT (theo cấu hình hiện tại); nhánh bật (đặc biệt cross-encoder cần tải model sentence-transformers) chưa có bằng chứng chạy.
- Hướng theo dõi: khi bật reranker/multi-query để tối ưu, chạy lại `--mode full` và đối chiếu `--compare` với baseline trong repo này.

## Đánh giá tính đúng đắn

- Chấm điểm độc lập với chunk ID (chỉ so `expected_terms` trên text chuẩn hóa) — đúng yêu cầu nhãn bền vững khi đổi chunking.
- Tái dùng nguyên component retrieval của app (`Retriever`, `BM25Search`, pgvector, fuse, rerank) nên số liệu phản ánh hành vi thật, không phải bản mô phỏng song song.
- Không ghi key/secret vào báo cáo (snapshot config chỉ gồm 22 trường cấu hình RAG); cache embedding nằm trong vùng gitignore.
- Xác suất tất định: các hàm xếp hạng đều có khóa phụ (BM25 theo index; sqlite fallback theo chunk_index; pgvector lệ thuộc thứ tự Postgres trả về nhưng thực nghiệm 2 lần chạy giống hệt 100/100 câu — bằng chứng AC-02).

## Kết luận

- `approved`: mọi AC-01…AC-06 có bằng chứng `passed` trong `verification.md`; hai nhận xét bắt buộc không có; R-03/R-04 là low, không bắt buộc, có hướng theo dõi rõ.

## Bổ sung review vòng 2 (mở rộng coverage@k, 2026-10-25)

- Phạm vi: diff coverage@k trong `eval_retrieval.py` + test + baseline chạy lại.
- Kiểm tra: thuật toán coverage dùng đúng chuẩn hóa chung (không Copy code lệch đường phân tích; term trùng sau chuẩn hóa khử trùng); câu thiếu coverage bỏ khỏi trung bình thay vì kéo bằng 0; `--compare` chéo v1/v2 in `—` thay vì 0 giả — hợp lý.
- Không nhận xét bắt buộc mới. R-03 (đường dẫn tương đối) vẫn mở và đã tự gặp lại một lần khi smoke (file rơi ra ngoài repo) — tiếp tục theo dõi, chưa đổi để giữ tương thích.
- Kết luận: giữ `approved` trên bản có coverage (self_review).
