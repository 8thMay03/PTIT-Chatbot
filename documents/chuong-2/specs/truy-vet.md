# Truy vết chức năng, quy tắc tới thiết kế Chương 2

## Chức năng (ĐA Bảng 5)
| CN | Use case | Tuần tự | CSDL | Kiến trúc / hoạt động |
|---|---|---|---|---|
| CN01 Đăng nhập | UC01 (2.2.1) | 2.5.0 (trình duyệt / ứng dụng vỏ); kiểm tra phiên ở 2.5.1–2.5.6b | `users` (`student_code`, `auth_source`, `cohort`, `major`) | API xác thực; Ứng dụng vỏ truyền danh tính |
| CN02 Hỏi đáp | UC02 + 2 dạng con (2.2.2) | 2.5.1, 2.5.2, 2.5.3 (API đọc lịch sử theo mã hội thoại, kiểm chủ hội thoại) | `conversations`, `messages` | API hỏi đáp; 2.7.2a (1)–(10) |
| CN03 Nguồn trích dẫn | UC03, "Xem đoạn văn bản gốc" | 2.5.2 (gắn trích dẫn), 2.5.1 (nguồn từ đệm) | `message_sources`, `answer_cache_sources`, `chunks.section_path` | 2.7.2a (8) |
| CN04 Gợi ý câu hỏi | UC04 + 2 dạng con | 2.5.0 (câu hỏi phổ biến), 2.5.2 (câu hỏi liên quan từ LLM) | `suggested_questions`, `messages.related_questions` | 2.7.2a (8) |
| CN05 Lịch sử hội thoại | UC05 + UC con (2.2.2) | — (đọc/sửa/xóa đơn giản) | `conversations` | API hỏi đáp |
| CN06 Đánh giá | UC06, "Gửi góp ý" | 2.5.6a (kiểm tra câu trả lời thuộc hội thoại của sinh viên) | `feedback` | API hỏi đáp |
| CN07 Quản lý tài liệu | UC07 + UC con (2.2.3) | 2.5.4; xóa mềm mô tả ở 2.2.3, 2.6 | `documents`, `audiences`, `knowledge_groups`, `chunks` | API quản trị, Kho tệp; 2.7.2b |
| CN08 Cập nhật phiên bản | UC08 | 2.5.5 | `documents.version`, `supersedes_id`, `status`; `audiences` | 2.7.2b (F) |
| CN09 Xem phản hồi | UC09 + 2 UC con | 2.5.6b | `feedback`, `messages.answer_status` | API quản trị |
| CN10 Trích xuất | "Kiểm tra nội dung trích xuất bản scan" | 2.5.4 (B), (C) | `documents.extracted_text`, `is_scanned`, `status = needs_review` | Bộ trích xuất (OCR); 2.7.2b (B)(C) |
| CN11 Chuẩn hóa, viết lại | — (nội bộ) | 2.5.1–2.5.3 bước (2) | `messages.rewritten_question` | Bộ chuẩn hóa, viết lại; 2.7.2a (2) |
| CN12 Truy xuất lai, xếp hạng lại | — | 2.5.2, 2.5.3 | `chunks.tokenized_text`, `embedding`, `chunk_strategy`, `start_offset`/`end_offset`; `audiences`; `documents.is_official`; cấu hình `retrieval_mode` (2.7) | Bộ truy xuất lai, Bộ xếp hạng lại; 2.7.2a (5)(6) |
| CN13 Bộ nhớ đệm | — | 2.5.1 (trúng), 2.5.2 (ghi theo khóa, ngành), 2.5.4, 2.5.5 (hủy theo nhóm tri thức, tăng `knowledge_groups.cache_epoch`) | `answer_cache`, `answer_cache_sources`, `messages.from_cache` | Bộ nhớ đệm; 2.7.2a (4)(10), 2.7.2b (F) |
| CN14 Kiểm soát | — | 2.5.3 (2 nhánh từ chối), 2.5.2 (đủ căn cứ; `alt` không có trích dẫn hợp lệ → thay câu trả lời đã hiển thị) | `messages.answer_status` | Bộ kiểm soát câu trả lời; 2.7.2a (3)(7), ◇ trích dẫn sau (8) |

## Quy tắc (ĐA Bảng 4)
| QT | Thể hiện ở |
|---|---|
| QT1 ≥1 nguồn, chỉ dùng tài liệu đã nạp | 2.5.2 (yêu cầu LLM chỉ dùng k đoạn; kiểm tra ≥1 trích dẫn hợp lệ, không đạt thì thay câu trả lời đã hiển thị); 2.7.2a ◇ sau (8); `message_sources`; xóa mềm hủy đệm (2.6) |
| QT2 không đủ căn cứ → báo rõ + phòng ban | 2.5.3 nhánh 2 (nhóm của đoạn điểm cao nhất / nhóm mặc định); `knowledge_groups.department`, `is_default`; 2.7.2a (7) |
| QT3 không dùng văn bản bị thay thế / hết hạn | 2.5.2 bước (5); 2.5.5 (bản cũ "đã bị thay thế"); `documents.status`, `expiry_date`, `chunks.expiry_date`; 2.7.2a (5) |
| QT4 nêu đối tượng áp dụng; chưa rõ thì theo từng trường hợp | 2.5.2 (truyền khóa, ngành; yêu cầu LLM nêu đối tượng, chưa rõ thì trình bày theo từng khóa, ngành); khóa bộ nhớ đệm luôn gồm khóa, ngành (không có khóa chung; SV chưa có khóa/ngành không dùng đệm); `users.cohort/major`, `audiences`; 2.7.2b (D) |
| QT5 khuyến cáo đối chiếu văn bản gốc | 2.5.2 (yêu cầu gửi LLM) |
| Bảng 3 (yêu cầu theo nhóm tri thức) | 2.5.2: ngữ cảnh kèm tên văn bản, ngày ban hành, năm học, nhóm; lịch thi ghi ngày ban hành, học phí ghi năm học, học vụ ghi đơn vị xử lý; trích dẫn kèm ngày ban hành; ưu tiên `documents.is_official` |
| Bảng 6, Bảng 7 (bật/tắt cải tiến, Recall@k theo span) | `chunks.chunk_strategy`, `start_offset`, `end_offset`; đoạn liên quan = đoạn chứa trọn span (`specs/2.6`); cấu hình thực nghiệm `retrieval_mode = vector \| bm25 \| hybrid` (2.7), lưu ở `app_config_overrides`; mô hình ở `model_profiles`. Màn Cấu hình là công cụ thực nghiệm, không có use case (`specs/2.2`); thực nghiệm chạy trên máy chủ riêng (`specs/2.7`) |
| QT6 hủy đệm khi tài liệu thay thế / hết hạn | 2.5.5 (trong giao dịch kích hoạt); 2.5.4 (nạp mới: hủy theo nhóm tri thức); xóa mềm (2.6); `answer_cache_sources`, `answer_cache.expires_at` NOT NULL; `knowledge_groups.cache_epoch` (không ghi đệm cũ sau khi hủy); 2.7.2b (F) và nhánh [không] |
| QT7 từ chối ngoài phạm vi, chèn lệnh | 2.5.3 nhánh 1 (kể cả dữ liệu cá nhân, giao dịch — ĐA mục 2); 2.7.2a (3) |
