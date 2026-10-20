# Review: 2026-10-21-tests-off-data-corpus

- Reviewer: `agent-opencode`.
- Hình thức: `self_review` (chỉ một agent làm việc trong phiên).
- Trạng thái: `approved`.
- Bản được review: nhánh `refactor/tests-off-data-corpus`, working tree tại
  `2026-10-21T00:06:03+07:00` — diff gồm `backend/pyproject.toml`,
  `backend/tests/test_ptit_faq.py`, `backend/tests/test_chunker_tables_benchmark.py`,
  `backend/tests/fixtures/ptit_faq.json`, 2 fixture mới trong
  `backend/tests/fixtures/corpus/`.
- Cập nhật lúc: `2026-10-21T00:06:03+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 → AC-04; nhiệm vụ S-01, S-02.
- File/thay đổi cần đọc: toàn bộ diff của task.
- Bằng chứng kiểm chứng: V-01 → V-04 trong `verification.md` (đã đọc, đủ cho các AC).
- Điểm cần đánh giá: tính đúng đắn của logic skip, tính trung thực của fixture
  D26, rủi ro dữ liệu cá nhân, khả năng bảo trì.

## Nhận xét

Đã review toàn bộ diff trên bản mới nhất. Không có nhận xét bắt buộc. Hai ghi
chú không bắt buộc (informational, không cần hành động):

### R-01 — Biến thể full-corpus không kiểm tra thứ hạng BM25

- Vị trí: `backend/tests/test_ptit_faq.py`
  (`test_common_ptit_question_retrieves_expected_evidence_from_full_corpus`).
- Liên quan: AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open` (informational).
- Vấn đề và tác động: biến thể corpus chỉ khẳng định bằng chứng tồn tại trong
  kho (quét toàn bộ chunk), không khẳng định BM25 top-50 trả được nó trên kho
  đầy đủ. Là quyết định có chủ ý (đã ghi trong implementation/verification):
  trên kho 955 KB, các đoạn cùng chủ đề lấn át kết quả đúng khiến việc khẳng
  định thứ hạng trở nên giòn và không phản ánh chất lượng retrieval thật (vì
  retrieval thật dùng hybrid + reranker).
- Đề nghị xử lý: theo dõi khi nâng cấp BM25/hybrid; nếu muốn đo chất lượng
  xếp hạng trên kho đầy đủ, dùng `scripts/evaluate.py` thay vì unit test.
- Người xử lý: `agent-opencode`.
- Nếu deferred: lý do — ngoài phạm vi task; hướng theo dõi — eval định kỳ.

### R-02 — Fixture benchmark là bản dựng lại, không phải bản gốc

- Vị trí: `backend/tests/fixtures/corpus/chunker-tables-benchmark.md`.
- Liên quan: AC-01, AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open` (informational).
- Vấn đề và tác động: file `data/test_chunker_tables _1_.md` gốc không còn
  (gitignore, không có trong git history). Fixture tổng hợp được dựng từ chính
  các bất biến trong test, nên không thể đối chiếu trực tiếp với dữ liệu gốc.
- Đề nghị xử lý: nếu ai còn giữ file gốc, đặt lại vào `data/test_chunker_tables _1_.md`
  — test corpus sẽ tự chạy đối chiếu; không cần sửa code.
- Người xử lý: không phân công.

## Lịch sử các vòng review

- `2026-10-21T00:06:03+07:00` — `agent-opencode` — working tree
  `refactor/tests-off-data-corpus` — kết luận `approved`; không có nhận xét
  bắt buộc; R-01, R-02 informational.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01 (deferred — ngoài phạm vi), R-02 (informational).
- Phần chưa review / giới hạn: reviewer và implementer là cùng một agent
  (self_review); không review độc lập.
- Bước tiếp theo: coordinator đối chiếu AC và đóng task.
