# Review: 2026-11-24-reranker-api-providers

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (cùng agent triển khai, không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/reranker-api-providers` (tách từ `dev` tại `8d9b134`), toàn bộ `git diff`
  và `backend/tests/test_reranker_api_profiles.py`.
- Cập nhật lúc: `2026-11-24T18:59:15+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06; S-01, S-02.
- Bằng chứng kiểm chứng: V-01..V-06. Chưa kiểm chứng với dịch vụ thật.
- Điểm cần đánh giá:
  - Khoá chỉ đi tới đúng hãng và URL.
  - Tương thích profile/`.env` `rerank_api` cũ.
  - Gate dùng ngưỡng rerank.
  - Import vòng.

## Nhận xét

### R-01 — Pinecone/TEI giới hạn số đoạn mỗi request

- Vị trí: `backend/app/retrieval/reranker.py` `build_rerank_request`.
- Liên quan: AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động:
  - Giới hạn số đoạn mỗi request: Pinecone `bge-reranker-v2-m3` 100, TEI mặc định 32.
  - Top-K tối đa 20 × hệ số ứng viên tối đa 8 = 160 ứng viên, vượt các giới hạn trên. Khi đó dịch vụ trả 4xx và câu hỏi
    dùng heuristic, không sai kết quả nhưng mất rerank.
- Đề nghị xử lý: chia lô nếu cấu hình thực tế vượt giới hạn.
- Nếu deferred:
  - Mặc định chỉ có 12 ứng viên. Gợi ý UI của Pinecone/TEI đã ghi giới hạn.
  - Chia lô sẽ cần gộp điểm giữa các lô; với các dịch vụ này điểm là tuyệt đối nên gộp được nếu cần sau.

Không có nhận xét bắt buộc khác. Đã kiểm:

- Hãng có URL cố định bỏ `base_url` ở profile, settings, endpoint kiểm tra và runtime.
- `resolve_reranker_test_key` không dùng khoá của hãng khác.
- `rerank_api` giữ hành vi cũ, các test cũ đều qua.
- `confidence.py` import trong hàm để tránh nạp `app.retrieval` ở cấp module.

## Lịch sử các vòng review

- `2026-11-24T18:59:15+07:00` — claude-agent — working tree trên — `approved`; R-01 `deferred`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01.
- Phần chưa review / giới hạn: chưa có review độc lập; chưa thử dịch vụ thật.
- Bước tiếp theo: coordinator đóng task.
