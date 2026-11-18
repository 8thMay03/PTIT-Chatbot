# Chương 2 — Bộ thiết kế (bản 2026-11-17, sửa theo hội đồng vòng 3)

**Chuẩn duy nhất:** `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md` (gọi tắt **ĐA**, đã được GVHD duyệt) và Hình 1 ĐA (`imgs/hình 1.png`). Code baseline `dev @ 92aa804` chỉ dùng để ghi chú ✅ đã có / 🆕 chưa có, **không** kéo thiết kế lệch khỏi ĐA.

## 1. Danh sách biểu đồ

| Mục | Biểu đồ | File import vào VP | Ảnh demo | Cách kiểm |
|---|---|---|---|---|
| 2.2.1 | Use case tổng quát | `import/2.2.1-usecase-tong-quat.xml` | `demo/2.2.1-usecase-tong-quat.png` | Import XML + xuất ảnh bằng CLI VP |
| 2.2.2 | Use case phân rã nhóm Sinh viên | `import/2.2.2-usecase-sinh-vien.xml` | `demo/2.2.2-usecase-sinh-vien.png` | như trên |
| 2.2.3 | Use case phân rã nhóm Quản trị viên | `import/2.2.3-usecase-quan-tri-vien.xml` | `demo/2.2.3-usecase-quan-tri-vien.png` | như trên |
| 2.5.0 | Tuần tự: đăng nhập (trình duyệt / ứng dụng vỏ) | `import/2.5.0-tuan-tu-dang-nhap.txt` | `demo/2.5.0-…png` | (*) |
| 2.5.1 | Tuần tự: trả lời từ bộ nhớ đệm | `import/2.5.1-tuan-tu-tra-loi-tu-bo-nho-dem.txt` | `demo/2.5.1-…png` | Ảnh render PlantUML từ cùng nguồn (*) |
| 2.5.2 | Tuần tự: truy xuất và sinh câu trả lời | `import/2.5.2-tuan-tu-truy-xuat-va-sinh-cau-tra-loi.txt` | `demo/2.5.2-…png` | (*) |
| 2.5.3 | Tuần tự: từ chối câu hỏi | `import/2.5.3-tuan-tu-tu-choi-cau-hoi.txt` | `demo/2.5.3-…png` | (*) |
| 2.5.4 | Tuần tự: nạp tài liệu | `import/2.5.4-tuan-tu-nap-tai-lieu.txt` | `demo/2.5.4-…png` | (*) |
| 2.5.5 | Tuần tự: cập nhật phiên bản | `import/2.5.5-tuan-tu-cap-nhat-phien-ban.txt` | `demo/2.5.5-…png` | (*) |
| 2.5.6a | Tuần tự: đánh giá câu trả lời | `import/2.5.6a-tuan-tu-danh-gia-cau-tra-loi.txt` | `demo/2.5.6a-…png` | (*) |
| 2.5.6b | Tuần tự: xem phản hồi | `import/2.5.6b-tuan-tu-xem-phan-hoi.txt` | `demo/2.5.6b-…png` | (*) |
| 2.6.2 | Lược đồ CSDL (ERD, 14 bảng: 12 nghiệp vụ + 2 cấu hình) | `import/2.6.2-erd.xml` (bảng + biểu đồ) hoặc `import/2.6-csdl.sql` (chỉ bảng); chỉ mục ở `import/2.6-csdl-chi-muc.sql` (không import VP) | `demo/2.6.2-erd.png` | ReverseDDL → ExportXML → thêm ERDiagram → Import XML + xuất ảnh |
| 2.7.1 | Kiến trúc tổng thể (component) | `import/2.7.1-kien-truc-tong-the.xml` | `demo/2.7.1-kien-truc-tong-the.png` | Import XML + xuất ảnh |
| 2.7.2a | Hoạt động: luồng truy vấn (Hình 1 bước 1–10) | `import/2.7.2a-hoat-dong-luong-truy-van.xml` | `demo/2.7.2a-…png` | Import XML + xuất ảnh |
| 2.7.2b | Hoạt động: luồng nạp dữ liệu (Hình 1 bước A–F) | `import/2.7.2b-hoat-dong-luong-nap-du-lieu.xml` | `demo/2.7.2b-…png` | Import XML + xuất ảnh |

(*) Import "Text Based Sequence Diagram" của VP chỉ chạy trên giao diện, không có lệnh dòng lệnh, nên ảnh demo tuần tự được render bằng PlantUML (`drafts/*.puml`) từ **cùng một nguồn** (`tools/sequence_specs.py`). Cú pháp cơ bản (participant, message, `\n` trong tên) đã import thử đạt ngày 2026-11-16; dòng `title`, `autonumber` và các khối `alt`/`opt`/`loop`/`note` **chưa** được thử trên VP — xem `specs/2.5-tuan-tu.md` mục "Lưu ý khi import".

Ảnh demo có watermark "Evaluation copy" vì VP đang ở bản dùng thử; bạn tự import trên máy rồi xuất lại thì cách hiển thị watermark tùy bản quyền.

## 2. Cách import vào Visual Paradigm 18.1
- Điều kiện: `C:\Program Files\Visual Paradigm 18.1\bin\Visual Paradigm.vmoptions` có dòng `-Dfile.encoding=UTF-8`, nếu thiếu thì tiếng Việt bị vỡ.
- **XML (use case, ERD, hoạt động, kiến trúc):** mở project trống → `Project > Import > XML…` → chọn file `.xml`. Mỗi biểu đồ nên đặt trong **một project riêng** để tránh watermark chéo khi VP hết hạn dùng thử.
- **Tuần tự:** `Project > Import > Text Based Sequence Diagram` → dán nội dung file `.txt`. Sau khi import, đổi kiểu lifeline `Sinh viên`, `Quản trị viên`, `Dịch vụ LLM` sang Actor và `CSDL`, `Kho tệp tài liệu` sang Database (vì VP không nhận từ khóa `actor`/`database` khi import text).
- **CSDL bằng DDL:** `Tools > DB > Reverse DDL` → PostgreSQL → UTF-8 → `import/2.6-csdl.sql`. Cách này chỉ tạo bảng; muốn có sẵn biểu đồ thì dùng `2.6.2-erd.xml`.

## 3. Sinh lại và tự kiểm (`tools/`)
> `tools/` và `drafts/` chỉ có trên máy Ngọc (người phụ trách thiết kế), không đưa lên repo. Người khác chỉ cần đọc `specs/`, xem `demo/`, dùng `import/`.

| Script | Việc |
|---|---|
| `usecase_specs.py`, `gen_usecase.py`, `run_usecase.sh` | Nội dung + toạ độ use case → XML → import + xuất PNG |
| `sequence_specs.py`, `gen_sequence.py` | Nội dung tuần tự → `import/*.txt` + `drafts/*.puml` |
| `gen_erd.py`, `run_erd.sh` | Reverse DDL → ExportXML → thêm ERDiagram → import + xuất PNG |
| `activity_specs.py`, `gen_activity.py` | Hai biểu đồ hoạt động → XML |
| `gen_component.py` | Kiến trúc tổng thể → XML |
| `vp.ps1`, `check_import.ps1` | Gọi CLI VP (`ImportXML`, `ReverseDDL`, `ExportXML`, `ExportDiagramImage`) trên project tạm |

Ví dụ: `VP_WORK=<thư mục tạm> tools/run_usecase.sh 2.2.1`; `python tools/gen_sequence.py`; render ảnh tuần tự trong `drafts/`: `java -DPLANTUML_LIMIT_SIZE=8192 -jar plantuml.jar -charset UTF-8 -tpng 2.5.*.puml` (2.5.2 rộng hơn 4096 px, giới hạn mặc định sẽ cắt ảnh). Không chạy CLI vào project đang mở trên VP.

## 4. Đặc tả từng phần
- `specs/2.1-tac-nhan-thuat-ngu.md` — tác nhân, thuật ngữ.
- `specs/2.2-usecase.md` — 3 biểu đồ use case.
- `specs/2.5-tuan-tu.md` — 8 biểu đồ tuần tự.
- `specs/2.6-csdl.md` — 14 bảng, chỉ mục, ràng buộc.
- `specs/2.7-kien-truc.md` — kiến trúc + 2 biểu đồ hoạt động.
- `specs/truy-vet.md` — truy vết CN01–CN14, QT1–QT7 tới biểu đồ.
- `issues/` — nhật ký phản biện qua nhiều vòng (tech lead đóng vai GVHD, QA đóng vai hội đồng); không bắt buộc đọc, kết quả đã nằm trong `specs/`.
- `chuan-bi-bao-ve.md` — đáp án các câu hỏi phản biện Q-1…Q-33.
