# Project Overview — PTIT AI Chatbot hỗ trợ sinh viên

## 1. Thông tin dự án

* **Tên dự án:** PTIT AI Chatbot
* **Loại dự án:** Trợ lý AI hỏi đáp sử dụng RAG (Retrieval-Augmented Generation)
* **Đối tượng:** Sinh viên, giảng viên và cán bộ học vụ PTIT
* **Mục tiêu:** Hỗ trợ tra cứu thông tin học vụ và các văn bản chính thức của Học viện thông qua hội thoại bằng tiếng Việt.

---

## 2. Bài toán

Sinh viên PTIT thường phải tìm kiếm thông tin từ nhiều nguồn như website, quy chế đào tạo, thông báo, biểu mẫu và các tài liệu PDF. Các tài liệu này có số lượng lớn, nhiều phiên bản và không thuận tiện để tra cứu, dẫn đến việc mất nhiều thời gian hoặc sử dụng nhầm thông tin đã hết hiệu lực.

Dự án PTIT AI Chatbot được xây dựng nhằm giải quyết bài toán tra cứu thông tin bằng ngôn ngữ tự nhiên, giúp người dùng đặt câu hỏi như đang trò chuyện với một trợ lý và nhận được câu trả lời dựa trên tài liệu chính thức của nhà trường.

---

## 3. Mục tiêu

### Mục tiêu tổng quát

Xây dựng một hệ thống AI có khả năng hiểu câu hỏi tiếng Việt, tìm kiếm nội dung liên quan trong kho tài liệu PTIT và sinh câu trả lời chính xác kèm nguồn trích dẫn.

### Mục tiêu cụ thể

* Tra cứu quy chế đào tạo và học vụ.
* Hỗ trợ tìm kiếm thủ tục hành chính.
* Giải đáp thông tin về học phí, học bổng và tốt nghiệp.
* Trích dẫn tài liệu và số trang để đảm bảo tính minh bạch.
* Hạn chế hiện tượng AI tạo ra thông tin không có trong nguồn.

---

## 4. Đối tượng sử dụng

| Đối tượng  | Nhu cầu                           |
| ---------- | --------------------------------- |
| Sinh viên  | Tra cứu quy chế, học phí, thủ tục |
| Giảng viên | Tìm nhanh văn bản đào tạo         |
| Cán bộ     | Hỗ trợ trả lời câu hỏi thường gặp |

---

## 5. Phạm vi dự án

### Trong phạm vi

* Chatbot hỏi đáp bằng tiếng Việt.
* Tìm kiếm thông tin từ PDF, DOCX và Excel.
* Trích dẫn nguồn tài liệu.
* Lưu lịch sử hội thoại.
* Hỗ trợ các lĩnh vực học vụ và hành chính.

### Ngoài phạm vi

* Đăng ký môn học.
* Chỉnh sửa dữ liệu sinh viên.
* Thanh toán học phí.
* Truy cập dữ liệu cá nhân từ hệ thống đào tạo.

---

## 6. Giải pháp đề xuất

Hệ thống sử dụng kiến trúc **Advanced Hybrid RAG (Retrieval-Augmented Generation)** gồm các thành phần chính:

1. **Guardrails:** Kiểm tra an toàn, chống prompt injection và lọc câu hỏi ngoài phạm vi PTIT.
2. **Multi-query & Rewriter:** Chuẩn hóa câu hỏi tiếng Việt và mở rộng các truy vấn tương đương.
3. **Hybrid Retriever:** Kết hợp tìm kiếm ngữ nghĩa (**Vector Search với ChromaDB**) và tìm kiếm từ khóa (**BM25 Search**).
4. **Reciprocal Rank Fusion (RRF) & Reranker:** Hợp nhất và sắp xếp lại thứ tự ưu tiên của các đoạn văn bản.
5. **Parent-Child Context Restoration:** Tìm kiếm trên các thẻ thông tin nhỏ (child chunks) nhưng khôi phục toàn bộ ngữ cảnh đoạn lớn (parent chunk) kèm tiêu đề/Điều/Khoản.
6. **Confidence Gate:** Kiểm tra độ tin cậy của bằng chứng trước khi chuyển tới mô hình ngôn ngữ.
7. **Large Language Model (LLM):** Sinh câu trả lời theo dạng streaming chỉ dựa trên context được cung cấp.

Quy trình hoạt động:

1. Người dùng nhập câu hỏi trên giao diện web.
2. Guardrail kiểm tra tính hợp lệ và phạm vi câu hỏi.
3. Hệ thống tạo các truy vấn tìm kiếm mở rộng (multi-query).
4. Thực hiện truy xuất song song qua Vector DB và BM25 Index.
5. Sắp xếp lại kết quả bằng RRF và Reranker, sau đó khôi phục ngữ cảnh Parent Chunk.
6. Confidence Gate đánh giá độ mạnh của bằng chứng.
7. LLM sinh câu trả lời kèm nguồn trích dẫn và truyền về giao diện theo dạng Real-time Streaming.

---

## 7. Giá trị mang lại

### Đối với sinh viên

* Giảm thời gian tìm kiếm thông tin.
* Tiếp cận đúng văn bản chính thức.
* Hỏi đáp bằng ngôn ngữ tự nhiên.

### Đối với nhà trường

* Giảm khối lượng câu hỏi lặp lại.
* Chuẩn hóa nguồn thông tin cung cấp.
* Tăng khả năng tiếp cận các quy định và thủ tục.

---

## 8. Công nghệ thực tế (MVP Stack)

| Thành phần      | Công nghệ thực tế                   |
| --------------- | ----------------------------------- |
| Frontend        | React 18, Vite 5, Lucide React     |
| Backend API     | Python 3.10+, FastAPI, Uvicorn     |
| Embedding       | OpenAI `text-embedding-3-small` (hỗ trợ SentenceTransformers / Hash fallback) |
| Vector Database | ChromaDB                           |
| Keyword Search  | BM25 (`rank-bm25`)                 |
| Data Storage    | SQLite, SQLAlchemy                 |
| LLM             | OpenAI `gpt-4.1-mini`              |
| RAG Pipeline    | Parent-Child Chunking, RRF, Reranker, Scope & Injection Guardrails |
| Evaluation      | Ragas, pytest                      |
| Deployment      | Docker, Docker Compose, Nginx      |
---

## 9. Kết quả mong đợi

Sau khi hoàn thành, PTIT AI Chatbot trở thành cổng tra cứu thông tin tập trung cho sinh viên PTIT, cho phép người dùng đặt câu hỏi bằng tiếng Việt và nhận câu trả lời nhanh chóng, chính xác, có căn cứ từ các tài liệu chính thức của Học viện.
