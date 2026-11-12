# Review: 2026-11-12-keep-toc-chunks

- Reviewer: `claude-code`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree `feat/keep-toc-chunks` trên `92aa804` — `backend/app/ingestion/cleaner.py`, `backend/app/ingestion/pipeline.py`, `backend/scripts/check_chunks.py`, test liên quan.
- Cập nhật lúc: `2026-11-12T23:20:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-05, S-01…S-03.
- Bằng chứng kiểm chứng: V-01…V-05.
- Điểm cần đánh giá: section mục lục kết thúc đúng chỗ (không nuốt nội dung thật), idempotent với `check_noise_chunk`, entry lạc vẫn lọc, tương thích chunk cũ không có `is_toc`.

## Nhận xét

Không có nhận xét bắt buộc. Ghi chú không bắt buộc:

### R-01 — Chunk sau mục lục không có heading vẫn mang `is_toc`

- Vị trí: `backend/app/ingestion/pipeline.py` (`is_toc_heading(chunk.heading)`).
- Liên quan: AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: cleaner kết thúc section mục lục khi gặp dòng không giống entry, nhưng chunker chỉ tách section theo heading; nếu nội dung thật nối ngay sau mục lục không có heading, chunk đó vẫn nằm dưới "MỤC LỤC" và bị gắn `is_toc = true`. Không xảy ra ở D26 (sau mục lục là `# LỜI NÓI ĐẦU`); `is_toc` hiện chưa có bên đọc.
- Đề nghị xử lý: nếu sau này dùng `is_toc` để hạ trọng số, cân nhắc đánh dấu ranh giới ngay trong cleaner.
- Nếu deferred: theo dõi khi có bên đọc `is_toc`.

## Lịch sử các vòng review

- `2026-11-12T23:20:00+07:00` — claude-code — working tree trên `92aa804` — approved (self_review), R-01 deferred.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01.
- Phần chưa review / giới hạn: chưa có reviewer độc lập.
- Bước tiếp theo: người dùng review PR trước khi merge.
