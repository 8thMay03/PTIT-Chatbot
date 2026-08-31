# PRD — PTIT AI Chatbot hỗ trợ sinh viên

## 1. Thông tin tài liệu

* **Tên sản phẩm:** PTIT AI Chatbot
* **Phiên bản:** 1.0
* **Mục tiêu:** Xây dựng trợ lý AI hỗ trợ sinh viên PTIT tra cứu thông tin học vụ, quy chế và các thủ tục của nhà trường bằng ngôn ngữ tự nhiên.

---

# 2. Bối cảnh

Hiện nay sinh viên PTIT phải tìm kiếm thông tin từ nhiều nguồn khác nhau như website, cổng đào tạo, file PDF quy chế và các biểu mẫu hành chính. Việc này gây mất thời gian và dễ dẫn đến sử dụng tài liệu cũ hoặc sai phiên bản.

PTIT AI Chatbot được xây dựng nhằm trở thành một điểm truy cập thống nhất, cho phép sinh viên đặt câu hỏi bằng tiếng Việt và nhận được câu trả lời kèm nguồn trích dẫn từ tài liệu chính thức.

---

# 3. Mục tiêu sản phẩm

### Mục tiêu chính

* Trả lời câu hỏi của sinh viên bằng tiếng Việt dựa trên tài liệu chính thức.
* Tra cứu thông tin chính xác từ quy chế, học phí, học phần và các biểu mẫu PTIT.
* Hiển thị nguồn trích dẫn rõ ràng (tài liệu, Điều, Khoản) để người dùng kiểm chứng.
* Giảm hallucination tối đa nhờ Guardrails và Confidence Gate.
* Giảm thời gian phản hồi với cơ chế Real-time NDJSON Streaming.

### Chỉ số thành công (Success Metrics - Đo lường thực tế với Ragas)

Kết quả kiểm thử tự động trên bộ đánh giá 50 câu hỏi RAG (`top_k=4`):

| Chỉ số | Mục tiêu ban đầu | Kết quả thực tế MVP | Ý nghĩa |
| --- | ---: | ---: | --- |
| **Context Precision** | ≥ 85% | **0.90 (90%)** | Mức độ liên quan và thứ hạng của context truy xuất |
| **Context Recall** | ≥ 90% | **0.95 (95%)** | Khả năng tìm đủ bằng chứng cần thiết từ tài liệu |
| **Faithfulness** | ≥ 90% | **0.93 (93%)** | Mức độ câu trả lời trung thực với context, không bịa |
| **Answer Relevancy** | ≥ 80% | **0.85 (85%)** | Mức độ câu trả lời tập trung vào đúng câu hỏi |
| **Thời gian phản hồi (TTFT)** | ≤ 5 giây | **< 2 giây** | Thời gian xuất hiện ký tự đầu tiên (Streaming) |

---

# 4. Đối tượng người dùng

## Người dùng chính

**Sinh viên PTIT**

Nhu cầu:

* Hỏi học phí, quy chế đào tạo.
* Thủ tục xin giấy xác nhận, quy trình hành chính.
* Quy định học lại, cải thiện điểm, điều kiện tốt nghiệp.

## Người dùng phụ

* Giảng viên
* Cán bộ phòng đào tạo (tra cứu nhanh văn bản)

---

# 5. Phạm vi (Scope)

## Trong phạm vi MVP 1.0 (In Scope)

* Hỏi đáp tiếng Việt theo dạng hội thoại (hỗ trợ lưu lịch sử hội thoại).
* Real-time Streaming câu trả lời (NDJSON streaming).
* Nạp và xử lý tài liệu cấu trúc **Markdown (`.md`) và Text (`.txt`)** bảo toàn cấu trúc tiêu đề.
* Parent-child chunking & Hybrid retrieval (Vector + BM25 + RRF + Reranker).
* Trích dẫn nguồn chi tiết (tên tài liệu, tiêu đề Mục/Điều/Khoản, đoạn văn bản bằng chứng).
* Guardrail chặn câu hỏi ngoài phạm vi PTIT và chống Prompt Injection.
* Confidence gate từ chối trả lời khi không có đủ bằng chứng.
* Web UI quản lý tài liệu: Tải file lên, xem trước, tải xuống và xóa tài liệu.

## Định hướng nâng cấp ở các phiên bản sau (Out of Scope for MVP 1.0)

* Đọc file PDF, DOCX, Excel thô (chưa qua chuẩn hóa Markdown/TXT).
* Chỉnh sửa dữ liệu sinh viên hoặc Đăng ký môn học.
* Thanh toán học phí hoặc Truy cập dữ liệu cá nhân từ hệ thống SIS.
* Tư vấn pháp lý hoặc y tế ngoài học vụ PTIT.

---

# 6. User Stories

### US-01: Tra cứu quy chế

**Là một sinh viên**, tôi muốn hỏi:

> "Điều kiện học cải thiện là gì?"

Để biết mình có đủ điều kiện hay không.

**Acceptance Criteria**

* Trả lời đúng theo quy chế.
* Hiển thị tên tài liệu, Mục/Điều và trang/đoạn trích dẫn.

---

### US-02: Tra cứu thủ tục

**Là một sinh viên**, tôi muốn hỏi:

> "Làm giấy xác nhận sinh viên như thế nào?"

**Acceptance Criteria**

* Liệt kê đầy đủ các bước.
* Đính kèm trích dẫn văn bản quy định.

---

### US-03: Học phí

**Là một sinh viên**, tôi muốn biết:

> "Học phí ngành CNTT bao nhiêu?"

**Acceptance Criteria**

* Trả lời theo đúng năm học trong tài liệu.
* Ưu tiên văn bản quy định mới nhất.

---

### US-04: Quản lý tài liệu tri thức (Admin/Quản trị)

**Là một quản trị viên**, tôi muốn tải lên hoặc xóa tài liệu trên giao diện web để hệ thống tự động cập nhật kho tri thức RAG.

**Acceptance Criteria**

* Upload thành công file `.md` / `.txt`.
* Hệ thống tự động làm sạch, chunking, embedding và lưu vào PostgreSQL (pgvector + BM25).
* Có thể xóa tài liệu và tự động làm sạch vector store.

---

# 7. Chức năng sản phẩm

## 7.1 Chat hỏi đáp & Streaming

**Mô tả**

Người dùng nhập câu hỏi bằng ngôn ngữ tự nhiên. Giao diện nhận phản hồi dạng Real-time Streaming (NDJSON) từng từ/từng dòng.

**Input**

> "Em được học lại tối đa bao nhiêu lần?"

**Output**

* Câu trả lời stream từng ký tự
* Danh sách nguồn trích dẫn (sources)
* Nút sao chép câu trả lời và xem debug thông tin retrieval

---

## 7.2 Trích dẫn nguồn (Citations)

Mỗi câu trả lời phải hiển thị danh sách bằng chứng:

* Tên tài liệu
* Tiêu đề/Vị trí (Mục, Điều, Khoản)
* Đoạn văn bản trích dẫn (Preview text)

---

## 7.3 Lịch sử hội thoại

* Lưu các cuộc trò chuyện trong PostgreSQL database.
* Hiển thị danh sách hội thoại ở thanh bên (Sidebar).
* Cho phép chọn lại hội thoại cũ để xem tiếp.

---

## 7.4 Bảo mật & Lọc an toàn (Guardrails)

* **Scope Filter:** Tự động phát hiện và từ chối các câu hỏi không liên quan tới PTIT hoặc câu hỏi tư vấn y tế, pháp lý.
* **Prompt Injection Protection:** Chặn các câu hỏi cố tình thay đổi chỉ thị hệ thống (System Prompt Override).
* **Confidence Gate:** Nếu điểm tương đồng context quá thấp, trả về thông báo cố định: *"Chưa tìm thấy thông tin này trong tài liệu."* mà không tự suy diễn.

---

## 7.5 Quản lý tài liệu (Document Management UI)

* **Danh sách tài liệu:** Hiển thị tên, số lượng chunk, dung lượng file.
* **Tải tài liệu mới (Upload):** Kéo thả hoặc chọn file `.md`/`.txt` để nạp trực tiếp vào kho tri thức.
* **Xem trước & Tải về:** Xem nội dung file text/markdown hoặc tải file gốc về máy.
* **Xóa tài liệu:** Xóa tài liệu khỏi hệ thống backend, tự động đồng bộ gỡ bỏ khỏi PostgreSQL (metadata + pgvector).

---

# 8. Luồng người dùng

1. Sinh viên mở chatbot.
2. Nhập câu hỏi.
3. Hệ thống chạy Guardrail kiểm tra an toàn.
4. Chạy Hybrid Search (Vector pgvector + BM25) + RRF + Reranker.
5. Kiểm tra Confidence Gate.
6. AI sinh câu trả lời dạng Streaming (NDJSON) kèm nguồn trích dẫn.
7. Người dùng đọc đáp án, kiểm tra nguồn trích dẫn và tiếp tục hỏi đáp.

---

# 9. Yêu cầu phi chức năng

## Hiệu năng

* Thời gian phản hồi ký tự đầu tiên (TTFT) < 2 giây.
* Hỗ trợ xử lý song song Hybrid Search + Reranking nhanh chóng.

## Độ tin cậy & An toàn

* Chỉ sử dụng bằng chứng từ tài liệu chính thức đã nạp.
* Tự động từ chối khi câu hỏi ngoài phạm vi hoặc cố tình hack prompt.

## Bảo mật

* Không lưu thông tin nhạy cảm cá nhân trong prompt.
* Lưu trữ an toàn trong cơ sở dữ liệu nội bộ (PostgreSQL).

---

# 10. Tiêu chí hoàn thành (Definition of Done)

* Chatbot trả lời chính xác các nhóm câu hỏi quy chế học vụ PTIT.
* Mọi câu trả lời hợp lệ đều có trích dẫn nguồn (mục, Điều, Khoản).
* Có Guardrail từ chối khi câu hỏi ngoài phạm vi hoặc thiếu dữ liệu.
* Bộ kiểm thử Ragas đạt kết quả: Context Recall ≥ 90%, Faithfulness ≥ 90%.
* Giao diện web chạy mượt mà tính năng Streaming và Quản lý tài liệu.

---

# 11. Phiên bản MVP 1.0 (Trạng thái hoàn thành thực tế)

| Độ ưu tiên | Chức năng | Trạng thái MVP 1.0 |
| ---------- | ------------------------------- | :---: |
| P0 | Chat hỏi đáp tiếng Việt & Streaming | **Đã hoàn thành** |
| P0 | Hybrid RAG (Vector + BM25 + Parent-child) | **Đã hoàn thành** |
| P0 | Trích dẫn nguồn (Tên tài liệu, Điều/Khoản) | **Đã hoàn thành** |
| P0 | Guardrails (Chống injection & Lọc scope) | **Đã hoàn thành** |
| P1 | Lưu lịch sử hội thoại (PostgreSQL) | **Đã hoàn thành** |
| P1 | Quản lý tài liệu trên Web UI (Upload/Delete) | **Đã hoàn thành** |
| P1 | Hỗ trợ dữ liệu Markdown (`.md`) và TXT (`.txt`) | **Đã hoàn thành** |
| P2 | Tự động đọc file PDF/DOCX thô | Roadmap (P2) |
| P2 | Đánh giá chất lượng tự động với Ragas | **Đã hoàn thành** |

