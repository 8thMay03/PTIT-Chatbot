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

Hệ thống sử dụng kiến trúc **RAG (Retrieval-Augmented Generation)** gồm ba thành phần chính:

1. **Retriever:** Tìm các đoạn văn liên quan trong kho tài liệu.
2. **Vector Database:** Lưu trữ embedding của tài liệu để truy xuất ngữ nghĩa.
3. **Large Language Model:** Sinh câu trả lời dựa trên context được truy xuất.

Quy trình hoạt động:

1. Người dùng nhập câu hỏi.
2. Câu hỏi được chuyển thành embedding.
3. Retriever tìm các đoạn tài liệu phù hợp.
4. LLM sinh câu trả lời từ context.
5. Hệ thống trả về đáp án kèm nguồn trích dẫn.

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

## 8. Công nghệ dự kiến

| Thành phần      | Công nghệ                  |
| --------------- | -------------------------- |
| Frontend        | React / Next.js            |
| Backend         | FastAPI                    |
| Embedding       | BGE-M3 hoặc Qwen Embedding |
| Vector Database | Qdrant                     |
| LLM             | Chatgpt, Gemini            |
| Document Parser | LlamaParse hoặc Docling    |
| Graph Database  | Neo4j                      |
---

## 9. Kết quả mong đợi

Sau khi hoàn thành, PTIT AI Chatbot có thể trở thành cổng tra cứu thông tin tập trung cho sinh viên PTIT, cho phép người dùng đặt câu hỏi bằng tiếng Việt và nhận câu trả lời nhanh chóng, chính xác, có căn cứ từ các tài liệu chính thức của Học viện.
