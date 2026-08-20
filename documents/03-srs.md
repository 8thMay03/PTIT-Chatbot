# Software Requirements Specification (SRS)

## PTIT AI Chatbot hỗ trợ sinh viên

**Phiên bản:** 1.0

---

# 1. Giới thiệu

## 1.1 Mục đích

Tài liệu này đặc tả các yêu cầu chức năng và phi chức năng của hệ thống **PTIT AI Chatbot**, một trợ lý AI hỗ trợ sinh viên tra cứu thông tin từ các văn bản chính thức của Học viện Công nghệ Bưu chính Viễn thông (PTIT).

SRS là cơ sở để đội phát triển, kiểm thử và triển khai hệ thống thống nhất về phạm vi và hành vi của phần mềm.

## 1.2 Phạm vi

Hệ thống cho phép người dùng:

* Đặt câu hỏi bằng tiếng Việt.
* Tra cứu thông tin từ kho tài liệu của PTIT.
* Nhận câu trả lời kèm nguồn trích dẫn.
* Lưu và tiếp tục lịch sử hội thoại.

Hệ thống **không** thực hiện các nghiệp vụ như đăng ký môn học, cập nhật dữ liệu sinh viên hoặc truy cập hệ thống SIS.

## 1.3 Định nghĩa

| Thuật ngữ | Giải thích                             |
| --------- | -------------------------------------- |
| RAG       | Retrieval-Augmented Generation         |
| Retriever | Thành phần truy xuất tài liệu          |
| Context   | Các đoạn văn được tìm thấy từ tài liệu |
| Citation  | Trích dẫn nguồn tài liệu               |
| Chunk     | Đoạn văn sau khi chia nhỏ tài liệu     |

---

# 2. Mô tả tổng quan

## 2.1 Người dùng

| Vai trò       | Quyền                            |
| ------------- | -------------------------------- |
| Sinh viên     | Đặt câu hỏi, xem lịch sử         |
| Giảng viên    | Tra cứu tài liệu                 |
| Quản trị viên | Quản lý kho tài liệu và hệ thống |

## 2.2 Kiến trúc mức cao

Hệ thống gồm các thành phần:

* Frontend Chat Interface
* FastAPI Backend
* Retriever
* ChromaDB
* Large Language Model
* Document Storage

Luồng xử lý:

1. Người dùng gửi câu hỏi.
2. Backend nhận yêu cầu.
3. Retriever tìm Top-K context.
4. LLM sinh câu trả lời.
5. Trả về đáp án và nguồn.

---

# 3. Yêu cầu chức năng

## FR-01 Tiếp nhận câu hỏi

**Mô tả**

Hệ thống phải cho phép người dùng nhập câu hỏi bằng tiếng Việt.

**Input**

* Văn bản UTF-8
* Độ dài tối đa 1000 ký tự

**Output**

* Yêu cầu được chuyển tới Retriever

**Độ ưu tiên:** Cao

---

## FR-02 Truy xuất tài liệu

**Mô tả**

Hệ thống phải tìm các đoạn văn liên quan nhất từ Vector Database.

**Điều kiện**

* Sử dụng embedding ngữ nghĩa.
* Mặc định lấy Top 5 chunk.

**Output**

Danh sách context gồm:

* Nội dung
* Tên tài liệu
* Trang
* Điểm tương đồng

---

## FR-03 Sinh câu trả lời

**Mô tả**

LLM phải sinh câu trả lời **chỉ dựa trên context**.

**Ràng buộc**

* Không tự bổ sung thông tin ngoài nguồn.
* Ưu tiên diễn đạt dễ hiểu.
* Trả lời bằng tiếng Việt.

**Output**

* Answer
* Citation

---

## FR-04 Trích dẫn nguồn

Mỗi câu trả lời phải chứa tối thiểu một nguồn.

Thông tin hiển thị:

* Tên tài liệu
* Số trang
* Đoạn được sử dụng

Ví dụ:

> Quy chế đào tạo 2026 — Trang 18

---

## FR-05 Lưu lịch sử hội thoại

Hệ thống phải lưu:

* Câu hỏi
* Câu trả lời
* Thời gian
* Danh sách citation

Người dùng có thể xem lại các cuộc hội thoại trước.

---

## FR-06 Xử lý khi không tìm thấy thông tin

Nếu Retriever không tìm đủ context hoặc độ tương đồng dưới ngưỡng:

Hệ thống phải trả lời:

> "Không tìm thấy thông tin trong các tài liệu chính thức của PTIT."

Không được suy diễn.

---

## FR-07 Quản lý tài liệu (Admin)

Quản trị viên có thể:

* Upload PDF
* Upload DOCX
* Upload Excel
* Xóa tài liệu
* Re-index Vector Database

---

# 4. Use Case

## UC-01 Tra cứu quy chế

**Actor**

Sinh viên

**Tiền điều kiện**

* Hệ thống hoạt động.
* Kho tài liệu đã được index.

**Luồng chính**

1. Sinh viên nhập câu hỏi.
2. Hệ thống tìm context.
3. LLM sinh câu trả lời.
4. Hiển thị đáp án và nguồn.

**Luồng thay thế**

Nếu không có context:

* Thông báo không tìm thấy.
* Gợi ý đặt câu hỏi khác.

---

## UC-02 Xem lịch sử

1. Người dùng mở mục lịch sử.
2. Danh sách hội thoại được hiển thị.
3. Chọn một cuộc hội thoại để xem lại.

---

# 5. Yêu cầu phi chức năng

## NFR-01 Hiệu năng

| Tiêu chí           |  Giá trị |
| ------------------ | -------: |
| Thời gian phản hồi | ≤ 5 giây |
| Truy xuất vector   | ≤ 1 giây |
| Concurrent users   |      100 |

## NFR-02 Độ chính xác

* Retriever Recall ≥ 95%
* Faithfulness ≥ 90%
* Citation Coverage = 100%

## NFR-03 Khả dụng

* Uptime ≥ 99%
* Tự động khởi động lại khi Backend lỗi

## NFR-04 Bảo mật

* HTTPS
* Mã hóa lịch sử hội thoại
* Phân quyền Admin/User
* Không lưu thông tin nhạy cảm trong prompt

---

# 6. Quy tắc nghiệp vụ

## BR-01

Chỉ sử dụng tài liệu có trạng thái **Approved**.

## BR-02

Nếu tồn tại nhiều phiên bản của cùng một văn bản:

* Ưu tiên phiên bản mới nhất.
* Phiên bản cũ chỉ dùng để tham khảo.

## BR-03

Citation luôn lấy từ chính context đã được Retriever trả về.

---

# 7. Mô hình dữ liệu

## Conversation

| Thuộc tính | Kiểu     |
| ---------- | -------- |
| id         | UUID     |
| user_id    | UUID     |
| created_at | Datetime |

## Message

| Thuộc tính | Kiểu           |
| ---------- | -------------- |
| role       | user/assistant |
| content    | Text           |
| timestamp  | Datetime       |

## Document Chunk

| Thuộc tính    | Kiểu    |
| ------------- | ------- |
| chunk_id      | UUID    |
| document_name | String  |
| page          | Integer |
| content       | Text    |
| embedding     | Vector  |

---

# 8. API Requirements

## POST /chat

### Request

```json
{
  "question": "Điều kiện học cải thiện là gì?",
  "conversation_id": "uuid"
}
```

### Response

```json
{
  "answer": "...",
  "citations": [
    {
      "document": "Quy che dao tao.pdf",
      "page": 18
    }
  ]
}
```

---

## GET /conversations

Trả về danh sách lịch sử hội thoại của người dùng.

---

## POST /documents

Upload tài liệu mới và thực hiện indexing.

---

# 9. Tiêu chí chấp nhận

| ID    | Tiêu chí                                                              |
| ----- | --------------------------------------------------------------------- |
| AC-01 | Chatbot trả lời bằng tiếng Việt                                       |
| AC-02 | Có ít nhất một citation trong mỗi câu trả lời                         |
| AC-03 | Không trả lời khi không có context phù hợp                            |
| AC-04 | Lưu được lịch sử hội thoại                                            |
| AC-05 | Admin upload tài liệu thành công và có thể tra cứu ngay sau khi index |

---

# 10. Giới hạn hệ thống

* Chỉ hỗ trợ tiếng Việt.
* Chỉ trả lời dựa trên tài liệu nội bộ PTIT.
* Không thay thế các hệ thống nghiệp vụ của Học viện.
* Chất lượng câu trả lời phụ thuộc vào chất lượng tài liệu và quá trình indexing.
