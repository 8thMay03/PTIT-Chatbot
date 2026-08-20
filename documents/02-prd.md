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

* Trả lời câu hỏi của sinh viên bằng tiếng Việt.
* Tra cứu thông tin từ tài liệu chính thức của PTIT.
* Hiển thị nguồn trích dẫn để người dùng kiểm chứng.
* Giảm thời gian tìm kiếm thông tin học vụ và hành chính.

### Chỉ số thành công (Success Metrics)

| Chỉ số                            | Mục tiêu |
| --------------------------------- | -------: |
| Độ chính xác câu trả lời          |    ≥ 90% |
| Câu trả lời có trích nguồn        |     100% |
| Thời gian phản hồi                | ≤ 5 giây |
| Tỷ lệ tìm thấy tài liệu liên quan |    ≥ 95% |

---

# 4. Đối tượng người dùng

## Người dùng chính

**Sinh viên PTIT**

Nhu cầu:

* Hỏi học phí
* Tra cứu quy chế đào tạo
* Thủ tục xin giấy xác nhận
* Quy định học lại, cải thiện điểm
* Lịch và quy trình hành chính

## Người dùng phụ

* Giảng viên
* Cán bộ phòng đào tạo (tra cứu nhanh văn bản)

---

# 5. Phạm vi (Scope)

## Trong phạm vi (In Scope)

* Hỏi đáp bằng tiếng Việt.
* Tra cứu tài liệu PDF, DOCX, Excel của PTIT.
* Trích dẫn nguồn và số trang.
* Lưu lịch sử hội thoại.
* Hỗ trợ các lĩnh vực:

  * Quy chế đào tạo
  * Học phí
  * Học bổng
  * Thủ tục hành chính
  * Biểu mẫu
  * Quy định tốt nghiệp

## Ngoài phạm vi (Out of Scope)

* Chỉnh sửa dữ liệu sinh viên.
* Đăng ký môn học.
* Thanh toán học phí.
* Truy cập dữ liệu cá nhân từ hệ thống SIS.
* Tư vấn pháp lý hoặc y tế.

---

# 6. User Stories

### US-01: Tra cứu quy chế

**Là một sinh viên**, tôi muốn hỏi:

> "Điều kiện học cải thiện là gì?"

Để biết mình có đủ điều kiện hay không.

**Acceptance Criteria**

* Trả lời đúng theo quy chế.
* Hiển thị tên tài liệu và trang nguồn.

---

### US-02: Tra cứu thủ tục

**Là một sinh viên**, tôi muốn hỏi:

> "Làm giấy xác nhận sinh viên như thế nào?"

**Acceptance Criteria**

* Liệt kê đầy đủ các bước.
* Đính kèm biểu mẫu nếu có.

---

### US-03: Học phí

**Là một sinh viên**, tôi muốn biết:

> "Học phí ngành CNTT bao nhiêu?"

**Acceptance Criteria**

* Trả lời theo đúng năm học.
* Nếu nhiều phiên bản, ưu tiên văn bản mới nhất.

---

# 7. Chức năng sản phẩm

## 7.1 Chat hỏi đáp

**Mô tả**

Người dùng nhập câu hỏi bằng ngôn ngữ tự nhiên.

**Input**

> "Em được học lại tối đa bao nhiêu lần?"

**Output**

* Câu trả lời
* Trích dẫn nguồn
* Trang tài liệu

---

## 7.2 Trích dẫn nguồn

Mỗi câu trả lời phải hiển thị:

* Tên tài liệu
* Số trang
* Đoạn văn được sử dụng

Ví dụ:

> Quy chế đào tạo đại học 2026 — Trang 18

---

## 7.3 Lịch sử hội thoại

* Lưu các cuộc trò chuyện.
* Cho phép xem lại.
* Tiếp tục cuộc hội thoại trước.

---

## 7.4 Xử lý khi không đủ thông tin

Nếu tài liệu không chứa đáp án, chatbot phải trả lời:

> "Mình không tìm thấy thông tin này trong các tài liệu chính thức của PTIT."

Không được tự suy diễn.

---

# 8. Luồng người dùng

1. Sinh viên mở chatbot.
2. Nhập câu hỏi.
3. Hệ thống tìm kiếm tài liệu liên quan.
4. AI sinh câu trả lời.
5. Hiển thị nguồn trích dẫn.
6. Người dùng có thể hỏi tiếp.

---

# 9. Yêu cầu phi chức năng

## Hiệu năng

* Phản hồi dưới 5 giây.
* Hỗ trợ tối thiểu 100 người dùng đồng thời.

## Độ tin cậy

* Chỉ sử dụng tài liệu đã được phê duyệt.
* Không tạo thông tin ngoài nguồn (hallucination).

## Bảo mật

* Không lưu thông tin cá nhân nhạy cảm.
* Nhật ký hội thoại được mã hóa khi lưu trữ.

---

# 10. Tiêu chí hoàn thành (Definition of Done)

* Chatbot trả lời được các nhóm câu hỏi học vụ chính.
* Mỗi câu trả lời đều có trích dẫn nguồn.
* Không trả lời bịa khi thiếu dữ liệu.
* Bộ kiểm thử đạt tối thiểu 90% độ chính xác.
* Hoàn thành tài liệu kỹ thuật và hướng dẫn triển khai.

---

# 11. Phiên bản MVP

Các chức năng ưu tiên cho bản đầu tiên:

| Độ ưu tiên | Chức năng                       |
| ---------- | ------------------------------- |
| P0         | Chat hỏi đáp tiếng Việt         |
| P0         | RAG từ tài liệu PDF             |
| P0         | Trích dẫn nguồn                 |
| P1         | Lưu lịch sử hội thoại           |
| P1         | Hỗ trợ DOCX và Excel            |
| P2         | Gợi ý câu hỏi thường gặp        |
| P2         | Đánh giá chất lượng câu trả lời |
