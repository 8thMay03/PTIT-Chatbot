# Task: Nút nhúng tài liệu trong dataset và bắt nhúng lại khi đổi mô hình embedding

- ID: `2026-11-24-reembed-documents`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("Thêm nút embed tài liệu trong màn hình dataset, ngoài ra khi đổi model embedding thì hãy
  yêu cầu embed lại toàn bộ tài liệu")
- Tạo lúc: `2026-11-24T23:29:37+07:00`
- Cập nhật lúc: `2026-11-24T23:59:00+07:00`

## Yêu cầu và kết quả mong muốn

**Hiện trạng** (nhánh `dev` tại `e477524`):

- Nhúng vector chỉ xảy ra trong bước chia đoạn (`IngestionPipeline.chunk_document/chunk_documents`): muốn có vector mới
  phải chia đoạn lại. Không có thao tác chỉ nhúng lại các đoạn hiện có.
- Không lưu đoạn nào được nhúng bằng mô hình nào. Đổi embedding → vector cũ (không gian vector khác, kể cả khác số chiều
  đã đệm 0) vẫn được tìm kiếm cosine với câu hỏi của mô hình mới → kết quả sai lệch, không có cảnh báo nào trừ hộp thoại
  xác nhận lúc chọn.
- Chọn profile embedding chỉ có hiệu lực sau khi khởi động lại backend (embedder bị ghim khi đã `ready`).

**Kết quả cần có** (theo D-01 … D-03):

- Màn hình dataset có nút "Nhúng" cho cả dataset và cho từng tài liệu; chạy nền có tiến độ, chỉ nhúng lại vector (không
  chia đoạn lại).
- Mỗi đoạn ghi lại chữ ký mô hình đã tạo vector. Đổi mô hình embedding thì giao diện báo toàn bộ tài liệu cần nhúng lại và
  có nút nhúng lại toàn bộ.

## Quyết định

Người dùng chọn cả ba phương án khuyến nghị (2026-11-24, qua câu hỏi trong phiên):

- D-01 — Áp ngay: bấm "Dùng" profile embedding thì embedder mới chạy luôn, không cần khởi động lại backend. Không tạo được
  mô hình mới khi đang có mô hình chạy được → 422, giữ mô hình cũ và lựa chọn cũ.
- D-02 — Bỏ vector cũ: đoạn có vector của mô hình khác (hoặc chưa có vector) không tham gia tìm kiếm vector, chỉ còn BM25;
  chat vẫn chạy, giao diện nhắc nhúng lại.
- D-03 — Job nền có tiến độ: nhúng chạy như job parse (trả về ngay, thanh tiến độ, không bị timeout proxy).

## Phạm vi

- Bao gồm:
  - Backend: cột `chunks.embedding_signature` (+ migration `0009`), chữ ký embedder trong `app/embeddings`, ghi chữ ký ở bước
    chia đoạn, bước nhúng lại `IngestionPipeline.embed_chunks`, job `embed` trong `app/ingestion/jobs.py`, lọc chữ ký ở
    `PgVectorStore.search`/`Retriever`, đổi embedding ngay trong `app/core/model_profiles.py`, API mới và số liệu
    "cần nhúng lại" ở tài liệu/dataset.
  - Frontend: nút nhúng (dataset, từng tài liệu), trạng thái "Cần nhúng", banner nhắc nhúng lại toàn bộ (danh sách dataset,
    trang Mô hình), xác nhận khi đổi embedding, cập nhật lời nhắc "khởi động lại backend".
- Ngoài phạm vi:
  - Tự nhúng lại ngay khi đổi mô hình mà không cần admin bấm (tốn chi phí API; admin quyết định lúc chạy).
  - Đổi số chiều cột vector; hiệu chỉnh `VECTOR_THRESHOLDS` cho mô hình mới.
  - `POST /config/reset` vẫn chỉ đổi `embedding_profile_id` (áp ở lần khởi động sau) như trước.
- Ràng buộc:
  - Không đổi kết quả tìm kiếm khi mọi đoạn đã khớp mô hình đang chạy (giữ đường truy vấn HNSW nhanh).
  - Nhúng lại không ghi vector cho đoạn đã bị chia đoạn lại/sửa trong lúc job chạy.
  - Dữ liệu cũ (chưa có chữ ký) được gán chữ ký của mô hình chạy lúc khởi động, để nâng cấp không bắt nhúng lại toàn bộ.

## Tiêu chí nghiệm thu

- [x] AC-01: Chia đoạn/nạp lại ghi `embedding_signature` của mô hình đã tạo vector; nhúng lại (dataset, tài liệu, toàn
  bộ) chỉ cập nhật vector + chữ ký, không đổi đoạn; mặc định chỉ nhúng đoạn "cần nhúng"; bỏ qua đoạn đã đổi nội dung.
- [x] AC-02: Job `embed` chạy nền qua `/parse-jobs`, có tiến độ, lỗi embedding → job `failed` với lý do an toàn; trùng
  phạm vi đang chạy → 409.
- [x] AC-03: Tìm kiếm vector bỏ đoạn có chữ ký khác mô hình đang nhúng câu hỏi; khi không có đoạn lệch thì truy vấn như cũ.
- [x] AC-04: Chọn/sửa profile embedding đang dùng áp ngay; lỗi tạo mô hình khi đang có mô hình chạy → 422, giữ nguyên;
  `restart_required` không còn bật sau khi áp thành công.
- [x] AC-05: API trả số đoạn/tài liệu cần nhúng ở tài liệu, dataset và `GET /api/embeddings/status`.
- [x] AC-06: Giao diện: nút nhúng dataset + từng tài liệu, trạng thái "Cần nhúng lại", tiến độ job, banner nhắc nhúng lại
  toàn bộ ở danh sách dataset và trang Mô hình, hộp thoại xác nhận đổi embedding nói rõ phải nhúng lại.
- [x] AC-07: `pytest` backend, `npm test`, `npm run build` đạt; ảnh chụp màn hình dataset.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-11-24-embedding-api-providers/` (provider embedding, đệm 0), `2026-11-07-be13-safe-embedding-startup/`
  (runtime embedder), `2026-10-27-background-parse-jobs/` (job nền), `2026-11-03-multi-dataset/`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai S-01 … S-04 trên nhánh `feat/reembed-documents` (tách từ `dev` tại `e477524`), chưa commit.
  AC-01 … AC-07 có bằng chứng (`verification.md` `passed`); self review `approved` (R-01, R-02 `deferred`).
- Blocker: không có.
- Bước tiếp theo: người dùng build lại container (entrypoint chạy migration `0009`, lần khởi động đầu gán chữ ký cho vector
  cũ); commit/PR vào `dev` khi muốn.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-24T23:29:37+07:00 — claude-agent: tạo task; người dùng chọn D-01 … D-03; chuyển `in_progress`.
- 2026-11-24T23:59:00+07:00 — claude-agent: triển khai xong, kiểm chứng đạt, self review `approved`; chuyển `done`.
  Bổ sung ngoài kế hoạch: CSS toolbar dataset xuống hàng cả nút (thêm nút nhúng làm nhãn bị bẻ dòng); `README.md`.
