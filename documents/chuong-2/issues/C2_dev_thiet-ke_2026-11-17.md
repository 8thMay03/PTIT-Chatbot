# Bàn giao thiết kế Chương 2 — agent dev — 2026-11-17

## Phản hồi của agent dev (vòng 1)

### Phạm vi đã làm
Thiết kế lại 12 biểu đồ Chương 2 theo ĐA và Hình 1. Danh sách file, cách import và cách sinh lại: `documents/chuong-2/README.md`. Đặc tả: `specs/2.1`, `2.2-usecase.md`, `2.5-tuan-tu.md`, `2.6-csdl.md`, `2.7-kien-truc.md`, `truy-vet.md`.

| Biểu đồ | File import | Ảnh demo | Kiểm |
|---|---|---|---|
| 2.2.1 / 2.2.2 / 2.2.3 use case | `import/2.2.*.xml` | `demo/2.2.*.png` | ImportXML + ExportDiagramImage (CLI VP 18.1) đạt; đếm phần tử bằng grep khớp spec (3/9/11/5/3; 2/16/7/0/11; 1/10/3/0/8) |
| 2.5.1–2.5.5 tuần tự | `import/2.5.*.txt` | `demo/2.5.*.png` (PlantUML) | Sinh từ 1 nguồn; message 14/34/25/22/17 khớp spec. **Chưa** import thử trên VP (import text chỉ có trên giao diện) |
| 2.6.2 ERD | `import/2.6.2-erd.xml`, `import/2.6-csdl.sql` | `demo/2.6.2-erd.png` | ReverseDDL đạt (11 bảng, 13 FK, chú thích tiếng Việt); ERD import + xuất ảnh đạt |
| 2.7.1 kiến trúc | `import/2.7.1-kien-truc-tong-the.xml` | `demo/2.7.1-…png` | Import + xuất ảnh đạt (18 thành phần, 23 phụ thuộc) |
| 2.7.2a/b hoạt động | `import/2.7.2a|b-*.xml` | `demo/2.7.2a|b-…png` | Import + xuất ảnh đạt (17 và 13 luồng) |

### Quyết định thiết kế
1. Thứ tự luồng truy vấn lấy nguyên Hình 1: viết lại câu nối tiếp ở bước (2), **trước** kiểm tra phạm vi và tra bộ nhớ đệm.
2. 3 tác nhân đúng Bảng 2; ứng dụng vỏ chỉ là môi trường chạy (xuất hiện ở kiến trúc).
3. CN10–CN14 không vẽ thành use case (không có tác nhân khởi phát), truy vết ở `truy-vet.md`.
4. UC cần danh tính `<<include>>` Đăng nhập; UC con `<<extend>>` UC cha.
5. CSDL 11 bảng nghiệp vụ; `knowledge_groups` thay cho `datasets` của baseline, có phòng ban phụ trách (QT2).
6. Hình 1 vẽ lại thành 2 biểu đồ hoạt động UML, giữ số bước (1)–(10), (A)–(F).

### Hạn chế đã biết
- Tuần tự: chưa thử import trên VP các khối `alt/opt/loop/note`; sau import phải đổi tay kiểu Actor/Database.
- ERD: đường tự tham chiếu `documents.supersedes_id` không hiện khi import; cột `embedding` ghi `VECTOR` không kèm số chiều do giới hạn của VP.
- Kiến trúc: còn vài đường phụ thuộc đi qua thành phần khác; người dùng có thể kéo lại trên VP.
- Ảnh demo xuất từ VP bản Evaluation nên có watermark.
- File cũ lỗi thời — **đã xoá** sau khi user đồng ý (2026-11-17): `import/2.5.1-v1.txt`, `import/2.5.1-v2.txt`, `import/test-usecase.xml`, `PROMPT-claude-desktop.md`, `specs/00-huong-dan-ve-vp.md`, `specs/2.2.1-usecase-tong-quat.md`, `specs/2.2.2-usecase-uc05.md`, `specs/2.2.3-usecase-uc07.md`, và trong `drafts/` các file `2.2.*`, `2.5.1-tuan-tu-cache-hit.*`, `2.5.2-tuan-tu-truy-xuat-sinh.*`, `2.5.3-tuan-tu-tu-choi.*`, `2.6.2-erd.*`, `2.7.1-kien-truc.*`, `2.7.2-luong-xu-ly.*`. **Reviewer bỏ qua các file này.**
