# Task: Định vị chính xác đoạn (chunk) trên bản tài liệu khi trỏ chuột

- ID: `2026-11-12-chunk-highlight-mapping`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: người dùng (8thMay03): "việc map giữa chunk với vị trí của chunk trên tài liệu gốc đôi khi không chính xác, hãy kiểm chứng lại, checkout ra nhánh mới rồi fix"
- Tạo lúc: `2026-11-12T23:58:00+07:00`
- Cập nhật lúc: `2026-11-13T00:05:00+07:00`

## Yêu cầu và kết quả mong muốn

Trong `DocumentView`, trỏ chuột vào một đoạn ở cột phải sẽ đánh dấu và cuộn tới vị trí của đoạn trên bản Markdown ở cột trái. Vị trí này đôi khi sai.

Kiểm chứng trên tài liệu thật "Sổ tay sinh viên D26" (1017 đoạn, index local) bằng thuật toán cũ `findMatchingElements`:
- 136/1017 đoạn không khớp được chữ nào và bị đặt theo tỷ lệ `chunk_index / tổng` (sai chỗ);
- 124 lần vị trí đoạn sau nằm trước đoạn liền trước;
- độ phủ trung bình 0.627 (tỷ lệ nội dung đoạn nằm trong vùng đánh dấu).

Nguyên nhân:
1. Hàng bảng trong đoạn là Markdown thô (`|a|b|`, `<br/>`, `\@`) nên không bao giờ khớp `textContent` của `tr`.
2. Không khớp thì đoán theo tỷ lệ; tỷ lệ không phản ánh mật độ đoạn (bảng dày, văn bản thưa).
3. Mọi đoạn con đều được chép dòng heading của section vào đầu; heading và dòng ngắn lặp lại khớp nhầm chỗ, cửa sổ mở rộng −10/+25 khối đánh dấu thêm khối không liên quan.
4. Khi đang tìm kiếm, tỷ lệ dùng số kết quả tìm kiếm thay cho tổng số đoạn.
5. Nội dung trùng thật trong tài liệu (Điều 6 xuất hiện hai lần, bảng học phần giống nhau giữa các ngành) không có gì để phân xử.

## Phạm vi

- Bao gồm: `frontend/src/lib/chunkLocator.js` (mới), `frontend/src/lib/chunkLocator.test.js` (mới), `frontend/src/DocumentView.jsx`.
- Ngoài phạm vi: backend/chunker (không lưu offset), chế độ xem bản gốc (PDF/DOCX), CSS.
- Ràng buộc: nhánh `feat/chunk-highlight-mapping` tách từ `dev` tại `20e1b92`.

## Tiêu chí nghiệm thu

- [x] AC-01: Trên D26 thật, mọi đoạn đều định vị được và vị trí theo đúng thứ tự đoạn (0 lần lùi) với trang 20/50/100 đoạn; độ phủ và độ chính xác trung bình ≥ 0.95.
- [x] AC-02: Test đơn vị cho bảng, heading lặp, nội dung na ná, nội dung trùng, không khớp.
- [x] AC-03: Toàn bộ test frontend và `vite build` không hồi quy.

## Tài liệu và phụ thuộc

- Không có.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: commit `dc205de`, PR #62 vào `dev` (https://github.com/8thMay03/PTIT-Chatbot/pull/62); đã sửa, kiểm chứng bằng đánh giá trên dữ liệu thật và test tự động; chưa kiểm tra thủ công trên trình duyệt (extension Chrome không kết nối).
- Blocker: không có.
- Bước tiếp theo: người dùng kiểm tra trên trình duyệt và merge PR #62.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-12T23:58:00+07:00 — claude-code: sửa ở frontend (căn chỉnh văn bản đã chuẩn hóa) thay vì lưu offset ở backend, vì đoạn được chia từ `clean_text(parsed_text)` còn cột trái render `parsed_text` gốc — offset trên bản đã làm sạch không dùng trực tiếp được; chuyển `in_review`.
