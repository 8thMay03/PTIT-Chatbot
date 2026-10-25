# Task: RAG-06 · Chunking theo Điều/Khoản, header ngữ cảnh và lọc chunk nhiễu

- ID: `2026-10-25-rag06-article-clause-chunking`
- Trạng thái: `in_progress`
- Coordinator: `zcode-agent`
- Người yêu cầu: người dùng (phiên ZCode 2026-10-25; nguồn: trang Notion "RAG-06")
- Tạo lúc: `2026-10-25T09:30:19+07:00`
- Cập nhật lúc: `2026-10-25T09:30:19+07:00`

## Yêu cầu và kết quả mong muốn

- Text dùng để embedding và BM25 chỉ chứa heading lá; tên tài liệu và `section_path` chỉ nằm trong metadata (chunk BHYT không chắc chứa chữ "BHYT").
- Parent/child chia theo số ký tự (2048/1024 cấu hình local; mặc định mã 900/450) không bám Điều/Khoản: một Điều có thể bị cắt giữa hai parent hoặc gộp với Điều kế bên.
- 143 chunk bắt đầu giữa từ (ví dụ `"ụng ......40"`) do `_split_long_block` cắt cứng theo ký tự; 59 chunk ngắn dưới 120 ký tự (ví dụ `"PTIT"`).
- Mục lục (dòng chấm dẫn + số trang) được index như nội dung thật; thông báo PDF có chunk chỉ chứa quốc hiệu hoặc "TRƯỞNG PHÒNG (đã ký)".

Việc cần làm (theo đề bài):

1. Parent = một Điều (vượt giới hạn thì nhóm các Khoản liên tiếp); child = Khoản hoặc đoạn văn. Tài liệu hướng dẫn/thông báo: parent = mục, child = bước hoặc đoạn.
2. Tách hai trường: `text` (hiển thị + prompt) và `search_text` = header ngữ cảnh (tên tài liệu > section_path) + text; embedding và BM25 dùng `search_text`; có migration Alembic.
3. Cắt đoạn dài theo ranh giới câu (`.`, `;`, xuống dòng), không cắt giữa từ.
4. Gộp chunk quá ngắn vào chunk liền kề cùng section.
5. Lọc mục lục, quốc hiệu, khối chữ ký, số trang.
6. Re-embed toàn bộ kho; ước lượng chi phí trước khi chạy.

## Phạm vi

- Bao gồm: `backend/app/ingestion/chunker.py`, `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/cleaner.py`, `backend/app/db/models.py`, migration Alembic mới, `backend/app/db/repositories.py`, `backend/app/retrieval/bm25.py`, `backend/app/vectordb/pgvector_store.py`, `backend/app/core/config.py`, script kiểm tra chunk mới, tests (`test_chunker*.py` và liên quan), trang task này, báo cáo `documents/rag-eval/rag-06/`.
- Ngoài phạm vi: bảng HTML (RAG-07), manifest (RAG-03), thay đổi hybrid/rerank, sửa dữ liệu trong `data/`, golden set.
- Ràng buộc:
  - Không ghi đè `documents/rag-eval/baseline_*.json` và `documents/rag-eval/rag-05/*.json`.
  - Index local giữ 1 tài liệu D26 processed (như sau RAG-05) để so sánh eval cùng kho; script kiểm tra chạy dry-run trên toàn bộ `data/` để xác minh lọc nhiễu cho thông báo PDF.
  - Không dùng `delete_ingested_document` để re-index (hàm này xóa file nguồn).

## Tiêu chí nghiệm thu

- [x] AC-01: Không parent nào chứa nội dung của 2 Điều khác nhau (kiểm bằng script trên toàn kho). — đạt (V-01)
- [x] AC-02: Không chunk nào bắt đầu giữa từ; chunk dưới 120 ký tự chỉ được phép khi cả section chỉ ngắn như vậy. — đạt (V-02)
- [x] AC-03: Index không còn chunk mục lục, quốc hiệu hay khối chữ ký. — đạt (V-03)
- [x] AC-04: `search_text` của mọi chunk chứa tên tài liệu và section_path; có test xác nhận embedding và BM25 dùng trường này. — đạt; lưu ý mặc định `EMBEDDING_INPUT_FIELD=text` theo đo lường, BM25 luôn dùng `search_text` (V-04)
- [ ] AC-05: hit@4 và MRR hybrid trên golden set tăng so với kết quả sau RAG-05; nhóm câu hỏi thủ tục không giảm. — **chưa đạt**: hybrid ngang bằng (0.850/0.778 vs 0.850/0.780), nhóm thủ tục −5.6 điểm hit@4 (V-05, R-01)
- [x] AC-06: Các test chunker hiện có (`test_chunker*.py`) được cập nhật và đều pass. — đạt, 324 passed / 1 skipped (V-06)

## Tài liệu và phụ thuộc

- Phụ thuộc RAG-05 (done): `.agents/tasks/2026-10-25-rag05-heading-hierarchy/`; nhánh `feat/rag06-article-clause-chunking` tách từ `feat/rag05-heading-hierarchy` (f3e95ed).
- Baseline so sánh: `documents/rag-eval/rag-05/processed_hybrid.json` (hit@4 0.850, MRR 0.780).
- Dataset: `backend/tests/fixtures/ptit_ragas_100.json` (100 câu, chưa có `question_type`/`source`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01…S-05 xong trên working tree nhánh `feat/rag06-article-clause-chunking` (tách từ `feat/rag05-heading-hierarchy`, nền `f3e95ed`) (**chưa commit**). Index local re-ingest: 1203 chunk / 749 parent, fingerprint `620d26fd0e0c…`, sạch theo `check_chunks --db --strict`. Suite 324 passed / 1 skipped.
- Kết quả eval: AC-01…AC-04, AC-06 đạt; **AC-05 chưa đạt** — hybrid ngang RAG-05 (hit@4 0.850 = 0.850, MRR 0.778 vs 0.780), BM25 tăng (+0.02 hit@4 nhờ `search_text`), nhóm 18 câu thủ tục giảm hit@4 0.667 → 0.611 (3 câu thuộc guide "HƯỚNG DẪN THỦ TỤC HÀNH CHÍNH"). Review self_review `changes_requested` với R-01 (high) chờ quyết định người dùng.
- Blocker: R-01 — người dùng cần chọn: (a) chỉnh AC-05 thành "không thụt lùi" và đóng task; (b) task tiếp theo tối ưu retrieval cho tài liệu guide; (c) contextual embedding bằng LLM.
- Bước tiếp theo: người dùng xem diff + quyết định R-01; sau đó coordinator đóng task hoặc chuyển hướng.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-25T09:30:19+07:00` — `zcode-agent`: tạo task từ đề bài RAG-06 (Notion). Chốt: (1) index DB giữ đúng 1 tài liệu D26 processed như sau RAG-05 để eval so sánh cùng kho, mọi kiểm tra lọc nhiễu trên tài liệu khác chạy dry-run; (2) "nhóm câu hỏi thủ tục" trong AC-05 định nghĩa bằng danh sách ID câu hỏi vì dataset chưa có `question_type` (ghi trong verification); (3) min-child 120 ký tự lấy từ cấu hình mới `MIN_CHILD_CHUNK_CHARS`.
- `2026-10-25T11:10:00+07:00` — `zcode-agent`: triển khai xong S-01…S-05. Hai quyết định có đo lường: (1) `EMBEDDING_INPUT_FIELD` mặc định `text` (embed `search_text` làm hybrid tụt 0.820/0.738 — thí nghiệm A; BM25 vẫn dùng `search_text` và tăng +0.02 hit@4); (2) lọc nhiễu bỏ cả section "MỤC LỤC" thay vì từng dòng (bảng và entry `.. 145` né luật theo dòng). AC-05 không đạt → task giữ `in_progress`, không tự đóng.
