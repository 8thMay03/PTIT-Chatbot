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

Hệ thống gồm các thành phần chính:

* **Frontend Chat & Admin UI:** Xây dựng bằng React 18, Vite 5, hỗ trợ Real-time Streaming và Quản lý tài liệu.
* **FastAPI Backend:** Xử lý API, điều phối luồng RAG và quản lý cơ sở dữ liệu.
* **Scope & Security Guardrails:** Chặn các câu hỏi ngoài phạm vi PTIT và phòng chống Prompt Injection.
* **Query Rewrite & Multi-query Generator:** Tối ưu câu hỏi tiếng Việt và mở rộng các câu hỏi tương đương.
* **Hybrid Retriever:** Kết hợp Vector Search (**ChromaDB**) và Keyword Search (**BM25**).
* **RRF & Reranker:** Hợp nhất kết quả bằng Reciprocal Rank Fusion và đánh lại thứ tự ưu tiên bằng Reranker.
* **Parent-Child Chunking Engine:** Truy xuất child chunks và khôi phục nội dung parent chunk kèm cấu trúc Mục/Điều/Khoản.
* **Confidence Gate:** Đánh giá độ mạnh của context trước khi gọi LLM.
* **Large Language Model (LLM):** OpenAI `gpt-4.1-mini` sinh câu trả lời theo dạng Streaming.
* **Data Storage (SQLite & SQLAlchemy):** Lưu lịch sử hội thoại, nguồn trích dẫn và metadata tài liệu.

### Luồng xử lý câu hỏi chi tiết:

1. Người dùng gửi câu hỏi từ Frontend UI tới API `POST /api/chat/stream`.
2. Guardrail kiểm tra an toàn (Scope & Prompt Injection).
3. Nếu hợp lệ, hệ thống tạo truy vấn mở rộng (Multi-query).
4. Tìm kiếm song song trên ChromaDB (Vector Search) và BM25 Index (Keyword Search).
5. Hợp nhất danh sách bằng RRF, sắp xếp lại bằng Reranker và khôi phục Parent Context.
6. Confidence Gate kiểm tra xem context có đủ mạnh không. Nếu yếu, trả về thông báo từ chối cố định.
7. LLM sinh câu trả lời và truyền về cho Frontend theo dạng NDJSON Streaming (`start`, `delta`, `done`).
8. Lưu câu hỏi, câu trả lời, debug metadata và danh sách nguồn (sources) vào cơ sở dữ liệu SQLite.

---

# 3. Yêu cầu chức năng

## FR-01 Tiếp nhận câu hỏi
**Mô tả:** Hệ thống phải cho phép người dùng nhập câu hỏi bằng tiếng Việt trên giao diện web.
**Input:** Văn bản UTF-8 (độ dài tối đa 1000 ký tự).
**Output:** Chuyển câu hỏi sang bộ lọc Guardrail và Retriever.
**Độ ưu tiên:** Cao

---

## FR-02 Truy xuất tài liệu Hybrid (Hybrid Retrieval)
**Mô tả:** Hệ thống tìm các đoạn văn liên quan nhất kết hợp Vector Search và BM25.
**Điều kiện:**
* Sử dụng embedding OpenAI `text-embedding-3-small` (hoặc fallback).
* Sử dụng giải thuật BM25 trên tập từ khóa tiếng Việt.
* Sử dụng RRF và Reranker để xếp hạng.
* Khôi phục parent chunk để giữ toàn bộ ngữ cảnh đoạn văn.
**Output:** Danh sách context gồm: Chunk ID, Document Name, Section Path (Mục/Điều/Khoản), Text Content, Rerank Score.

---

## FR-03 Sinh câu trả lời Real-time Streaming
**Mô tả:** LLM sinh câu trả lời chỉ dựa trên context đã được kiểm duyệt và truyền streaming về client.
**Ràng buộc:**
* Không tự bổ sung thông tin ngoài nguồn được cung cấp.
* Trả lời bằng tiếng Việt tự nhiên, dễ hiểu.
* Truyền nội dung theo dạng NDJSON Streaming (`type: delta`).
**Output:** Stream câu trả lời + Citation Metadata.

---

## FR-04 Trích dẫn nguồn (Citations)
**Mô tả:** Mỗi câu trả lời có bằng chứng phải hiển thị danh sách trích dẫn.
**Thông tin hiển thị:**
* Tên tài liệu (`source_name` / `title`)
* Vị trí (`heading` / `section_path`)
* Đoạn văn bản trích dẫn ngắn (`preview_text`)

---

## FR-05 Lưu lịch sử hội thoại
**Mô tả:** Hệ thống tự động lưu lịch sử trao đổi trong SQLite.
**Thông tin lưu trữ:**
* Lịch sử hội thoại (Conversation ID, User ID, Title)
* Danh sách tin nhắn (Role, Content, Timestamp, Metadata Debug)
* Nguồn trích dẫn liên kết với từng tin nhắn (MessageSource)

---

## FR-06 An toàn & Từ chối trả lời (Guardrail & Confidence Gate)
**Mô tả:** 
* Nếu phát hiện Prompt Injection hoặc câu hỏi ngoài phạm vi PTIT: Trả về câu từ chối cố định theo quy định.
* Nếu điểm tương đồng context của tất cả các đoạn đều dưới ngưỡng (Confidence Gate): Trả về *"Chưa tìm thấy thông tin này trong tài liệu."* mà không tự suy diễn.

---

## FR-07 Quản lý tài liệu (Document Management)
**Mô tả:** Người dùng/Quản trị viên có thể quản lý kho tài liệu RAG qua Web UI hoặc REST API.
**Chức năng:**
* `POST /api/documents`: Upload file `.md` / `.txt`, tự động phân chia parent-child chunk, embedding và lưu trữ.
* `GET /api/documents`: Lấy danh sách tài liệu kèm số lượng chunk và dung lượng.
* `GET /api/documents/{id}`: Xem chi tiết metadata và bản xem trước (preview text).
* `GET /api/documents/{id}/file`: Tải file gốc về máy.
* `DELETE /api/documents/{id}`: Xóa tài liệu khỏi hệ thống backend, ChromaDB và SQLite.

---

# 4. Use Case

## UC-01 Tra cứu quy chế & học vụ

**Actor:** Sinh viên / Người dùng

**Tiền điều kiện:** Hệ thống hoạt động, tài liệu đã được nạp và index.

**Luồng chính:**
1. Người dùng nhập câu hỏi trên chat UI.
2. Backend kiểm tra Guardrail -> Chạy Hybrid Search -> Rerank -> Khôi phục Parent Chunk.
3. Confidence Gate xác nhận bằng chứng đủ mạnh.
4. LLM sinh câu trả lời dạng Streaming.
5. Giao diện hiển thị phản hồi và danh sách nguồn trích dẫn.

**Luồng thay thế:**
* Nếu câu hỏi ngoài phạm vi hoặc bị Confidence Gate từ chối: Hiển thị thông báo từ chối cố định.

---

## UC-02 Quản lý tài liệu tri thức

**Actor:** Quản trị viên / Người dùng

**Luồng chính:**
1. Người dùng mở trang **Tài liệu** trên giao diện web.
2. Chọn "Tải lên tài liệu" và tải file `.md` hoặc `.txt`.
3. Hệ thống nạp dữ liệu, tạo vector embedding và báo thành công.
4. Người dùng có thể xem trước nội dung hoặc xóa tài liệu khi không còn sử dụng.

---

# 5. Yêu cầu phi chức năng

## NFR-01 Hiệu năng

| Tiêu chí | Giá trị |
| --- | ---: |
| Thời gian phản hồi ký tự đầu tiên (TTFT) | ≤ 2 giây |
| Thời gian truy xuất Hybrid Search | ≤ 1 giây |
| Đồng bộ dữ liệu khi upload file | Real-time |

## NFR-02 Độ chính xác (Kết quả đo đạc thực tế với Ragas)

* **Context Precision:** ≥ 0.90 (90%)
* **Context Recall:** ≥ 0.95 (95%)
* **Faithfulness:** ≥ 0.93 (93%)
* **Answer Relevancy:** ≥ 0.85 (85%)

## NFR-03 Khả dụng & Triển khai

* Hỗ trợ chạy container hóa hoàn toàn với **Docker & Docker Compose**.
* Tự động khởi động lại dịch vụ backend khi gặp lỗi.

## NFR-04 Bảo mật

* Bảo mật API với CORS & HTTP Headers (`X-Accel-Buffering: no` cho streaming).
* Phòng chống Prompt Injection ở tầng Guardrail trước khi gọi LLM.

---

# 6. Quy tắc nghiệp vụ

## BR-01
Chỉ sinh câu trả lời dựa trên thông tin có trong các tài liệu PTIT đã được nạp.

## BR-02
Nếu tồn tại nhiều phiên bản văn bản, ưu tiên sử dụng phiên bản mới nhất dựa trên tiêu đề hoặc metadata.

## BR-03
Citation luôn được trích xuất trực tiếp từ các parent chunks đã thông qua Confidence Gate.

---

# 7. Mô hình dữ liệu (SQLite / SQLAlchemy Schema)

## Conversation (Bảng lưu hội thoại)

| Thuộc tính | Kiểu dữ liệu | Mô tả |
| --- | --- | --- |
| id | String (UUID) | Khóa chính |
| user_id | String | ID người dùng |
| title | String | Tiêu đề cuộc hội thoại |
| created_at | DateTime | Thời gian tạo |
| updated_at | DateTime | Thời gian cập nhật |

## Message (Bảng lưu tin nhắn)

| Thuộc tính | Kiểu dữ liệu | Mô tả |
| --- | --- | --- |
| id | String (UUID) | Khóa chính |
| conversation_id | String (FK) | Khóa ngoại tới Conversation |
| role | String | `user` hoặc `assistant` |
| content | Text | Nội dung tin nhắn |
| metadata_json | Text (JSON) | Lưu thông tin retrieval debug |
| timestamp | DateTime | Thời gian tạo |

## MessageSource (Bảng lưu trích dẫn của tin nhắn)

| Thuộc tính | Kiểu dữ liệu | Mô tả |
| --- | --- | --- |
| id | Integer | Khóa chính tự tăng |
| message_id | String (FK) | Khóa ngoại tới Message |
| document_id | String | ID tài liệu trích dẫn |
| chunk_id | String | ID chunk được dùng |
| heading | String | Tiêu đề đoạn/mục |
| section_path | String | Đường dẫn cấu trúc Mục/Điều/Khoản |
| text | Text | Nội dung văn bản bằng chứng |
| rank | Integer | Thứ hạng truy xuất |
| score | Float | Điểm số tương đồng |

## Document (Bảng lưu thông tin tài liệu)

| Thuộc tính | Kiểu dữ liệu | Mô tả |
| --- | --- | --- |
| id | String | Khóa chính (hash hoặc UUID) |
| title | String | Tiêu đề tài liệu |
| source_path | String | Đường dẫn file trên ổ đĩa |
| file_hash | String | Hash kiểm tra trùng lặp file |
| created_at | DateTime | Thời gian nạp tài liệu |
| updated_at | DateTime | Thời gian cập nhật |

## DocumentParentChunk (Bảng lưu đoạn văn bản gốc)

| Thuộc tính | Kiểu dữ liệu | Mô tả |
| --- | --- | --- |
| id | String | Khóa chính chunk |
| document_id | String (FK) | Khóa ngoại tới Document |
| chunk_index | Integer | Thứ tự chunk trong tài liệu |
| heading | String | Tiêu đề đoạn/mục |
| section_path | String | Đường dẫn cấu trúc Mục/Điều/Khoản |
| text | Text | Nội dung đầy đủ của Parent Chunk |

---

# 8. API Requirements

## POST /api/chat/stream (Endpoint chính dùng cho Real-time Chat)

### Request
```json
{
  "message": "Điều kiện học cải thiện là gì?",
  "conversation_id": "optional-uuid",
  "top_k": 4
}
```

### Response (NDJSON Stream)
```ndjson
{"type": "start", "conversation_id": "c1f7b8d0-..."}
{"type": "delta", "content": "Theo quy chế đào tạo..."}
{"type": "delta", "content": " sinh viên được học cải thiện khi..."}
{"type": "done", "answer": "...", "sources": [{"title": "...", "section_path": "...", "text": "..."}], "conversation_id": "c1f7b8d0-..."}
```

---

## POST /api/chat (Endpoint đồng bộ)

### Response
```json
{
  "conversation_id": "c1f7b8d0-...",
  "answer": "Theo quy chế đào tạo...",
  "sources": [
    {
      "title": "Quy chế đào tạo 2024",
      "heading": "Điều 18. Học cải thiện",
      "section_path": "Chương III > Điều 18",
      "preview_text": "Sinh viên đạt điểm D..."
    }
  ]
}
```

---

## GET /api/documents (Danh sách tài liệu)

### Response
```json
{
  "documents": [
    {
      "id": "doc-01",
      "title": "Quy che dao tao.md",
      "source_path": "data/Quy che dao tao.md",
      "chunk_count": 12,
      "size_bytes": 15420,
      "created_at": "2026-08-20T10:00:00"
    }
  ]
}
```

---

## POST /api/documents (Upload tài liệu mới)

* **Content-Type:** `multipart/form-data`
* **Body:** `file` (File `.md` hoặc `.txt`)
* **Response:** Chi tiết tài liệu đã được nạp và index.

---

## DELETE /api/documents/{document_id} (Xóa tài liệu)

* **Response:** `{"success": true, "message": "Đã xóa tài liệu thành công."}`

---

## GET /api/health (Health Check)

* **Response:** `{"status": "ok"}`

---

# 9. Tiêu chí chấp nhận (Acceptance Criteria)

| ID | Tiêu chí | Trạng thái |
| --- | --- | :---: |
| AC-01 | Chatbot trả lời bằng tiếng Việt theo dạng Streaming mượt mà | **Pass** |
| AC-02 | Mỗi câu trả lời đúng có trích dẫn nguồn (Mục/Điều/Khoản) | **Pass** |
| AC-03 | Tự động từ chối khi câu hỏi ngoài phạm vi PTIT hoặc thiếu bằng chứng | **Pass** |
| AC-04 | Lưu và tải lại được lịch sử hội thoại trong SQLite | **Pass** |
| AC-05 | Người dùng có thể upload, xem trước và xóa tài liệu trên Web UI | **Pass** |

---

# 10. Giới hạn hệ thống (System Limitations)

* Tập trung tối ưu cho dữ liệu văn bản tiếng Việt.
* MVP 1.0 nạp các file văn bản đã được định dạng cấu trúc Markdown (`.md`) hoặc Text (`.txt`).
* Phụ thuộc vào kết nối OpenAI API (hoặc local fallback embedding/LLM nếu được cấu hình).

