# Issues — Thiết kế Chương 2

## Flow làm việc 3 agent
```
[A] Agent dev: thiết kế, sinh file import VP + ảnh demo, tự kiểm, ghi "Phản hồi của agent dev"
  → [B] Tech lead (vai GVHD, chỉ đọc): review nghiệp vụ theo ĐA, chuẩn UML, tính thống nhất ──không đạt──→ [A]
  → đạt: tech lead ghi "Bàn giao cho hội đồng"
  → [C] QA (vai hội đồng bảo vệ, chỉ đọc): câu hỏi phản biện, lỗi phải sửa ──còn "phải sửa"──→ [A] → [B] xác nhận
  → xong: báo user
```
- Mã: R-n (tech lead), QA-n (hội đồng), U-n (user). Đánh số tiếp, không dùng lại.
- File chỉ **thêm mục**, không xoá lịch sử. Tên: `C2_<loại>_<chủ đề>_<YYYY-MM-DD>.md`.
- Chuẩn đánh giá duy nhất: `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md` + `documents/chuong-2/imgs/hình 1.png`.

## Danh sách file
- `C2_dev_thiet-ke_2026-11-17.md` — bàn giao của agent dev.
- `C2_review_thiet-ke_2026-11-17.md` — tech lead (GVHD): vòng 1 Không đạt (R-1…R-25), vòng 2 Đạt (R-26…R-31) + "Bàn giao cho hội đồng"; phản hồi dev các vòng ở cuối.
- `C2_hoi-dong_2026-11-17.md` — hội đồng: lần đầu Đạt với điều kiện (QA-1…QA-10, Q-1…Q-25); chấm lại vòng 3 (QA-11…QA-16, Q-26…Q-33), vòng 4 (QA-17, QA-18), vòng 5 **Đạt**, hết mục PHẢI SỬA.
- `C2_review_thiet-ke_2026-11-17.md` vòng 3–5 (R-32…R-57): **Đạt**.
- `../chuan-bi-bao-ve.md` — đáp án Q-1…Q-33 (5 câu khó nhất ở đầu).
