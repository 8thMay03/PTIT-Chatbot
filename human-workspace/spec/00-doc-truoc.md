# Đọc trước — tài liệu thiết kế và phân công (cập nhật 2026-11-18)

> Dành cho cả nhóm, nhất là Khánh khi mới pull về. Đọc file này trước, rồi đi theo thứ tự ở mục 2.

## 1. Tình trạng
- **Thiết kế Chương 2 (phần biểu đồ) đã xong:** 15 biểu đồ; review mô phỏng GVHD và hội đồng qua 6 vòng, kết luận **Đạt**.
- **Chuẩn duy nhất:** `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md` (gọi tắt **ĐA**) và Hình 1 bản rõ `documents/chuong-2/imgs/hình 1.png`. Code nhánh `dev @ 92aa804` chỉ là hiện trạng (✅ đã có / 🆕 chưa có), không phải chuẩn.
- **Chưa làm:** văn bản 2.2.4, 2.2.5, 2.3, 2.4 của quyển; chỉnh tay ảnh trên Visual Paradigm (Ngọc); code theo checklist (cả hai).

## 2. Thứ tự đọc
**Khánh (lõi RAG):**
1. ĐA dòng 1–167 (dòng 168 là ảnh base64, bỏ qua).
2. `03-checklist-khanh-rag.md`: việc của Khánh. Mục 🔗 là hợp đồng với Ngọc, 🆕 là việc mới từ thiết kế, ⚠️ là việc đã đổi so với bản 2026-11-09.
3. `documents/chuong-2/specs/2.7-kien-truc.md`: kiến trúc 18 thành phần, mục **"Cấu hình thực nghiệm"** (bật/tắt cải tiến, cách đo Bảng 7).
4. `documents/chuong-2/specs/2.5-tuan-tu.md` và ảnh `demo/2.5.1`–`2.5.3`: luồng hỏi đáp từng bước, có đánh số message.
5. `documents/chuong-2/specs/2.6-csdl.md` và `import/2.6-csdl.sql`: bảng `chunks`, `messages`, `knowledge_groups`, `app_config_overrides`.
6. `documents/chuong-2/specs/truy-vet.md`: CN01–CN14, QT1–QT7 nằm ở biểu đồ, bảng nào.
7. `documents/chuong-2/chuan-bi-bao-ve.md`: đáp án phản biện. Phần A là 5 câu khó nhất, nhiều câu hỏi thẳng vào RAG.

**Ngọc:** `04-checklist-ngoc-fe-be.md`, sau đó đọc cùng các file trên.

## 3. Thư mục `documents/chuong-2/`
| Thư mục / file | Chứa gì |
|---|---|
| `README.md` | Danh sách 15 biểu đồ, file import, cách import vào Visual Paradigm 18.1 |
| `specs/` | Đặc tả từng mục 2.1–2.7 và bảng truy vết. **Đọc phần này để hiểu thiết kế.** |
| `demo/` | Ảnh 15 biểu đồ, xem ngay không cần VP (có watermark bản dùng thử) |
| `import/` | File import VP (XML, TXT); `2.6-csdl.sql` (14 bảng) và `2.6-csdl-chi-muc.sql` (chỉ mục, FK ghép) — dùng làm chuẩn khi viết migration |
| `chuan-bi-bao-ve.md` | 33 câu hỏi phản biện kèm trả lời, dẫn chứng, câu hỏi nối tiếp |
| `issues/` | Nhật ký phản biện các vòng (mã R-n, QA-n, Q-n). Không bắt buộc đọc; muốn biết **vì sao** một quyết định như vậy thì tìm mã trong này |

## 4. Quyết định thiết kế đã chốt

### 4.1. Ảnh hưởng trực tiếp tới phần RAG (Khánh)
| # | Quyết định | Lý do | Xem |
|---|---|---|---|
| 1 | Theo Hình 1: chuẩn hóa + **viết lại câu nối tiếp ở bước (2), trước** kiểm tra phạm vi (3) và tra đệm (4). Viết lại theo luật; viết lại bằng LLM là hướng phát triển | Câu không dấu/viết tắt không bị guardrail từ chối nhầm; khóa đệm là câu độc lập | `specs/2.5`, 2.5.1–2.5.3 |
| 2 | `chunks` có `chunk_strategy` (`fixed`/`legal`), `start_offset`, `end_offset` (vị trí trong `documents.extracted_text`). Mỗi tài liệu lưu **cả hai bộ đoạn** | Bảng 6: so chia cố định với chia theo Điều/Khoản trên cùng kho | `specs/2.6`, QA-2 |
| 3 | **Đoạn liên quan** = đoạn **chứa trọn** span gán nhãn; span cắt qua nhiều đoạn thì lấy đoạn phủ phần lớn nhất; như nhau cho `fixed`/`legal` | Recall@k, Precision@k, MRR so được giữa hai cách chia | `specs/2.6`, QA-14 |
| 4 | Cờ thực nghiệm: `NORMALIZATION_ENABLED`, `FOLLOW_UP_REWRITE_ENABLED`, `RETRIEVAL_MODE = vector \| bm25 \| hybrid`, `RERANKER_ENABLED`, `CACHE_ENABLED`, `CHUNK_STRATEGY`. Lưu ở bảng `app_config_overrides`, admin bật/tắt ở màn Cấu hình; mô hình chọn từ `model_profiles` | Bảng 6 đòi bật/tắt từng cải tiến độc lập; RAG cơ bản = `fixed` + `vector`, tắt hết | `specs/2.7` "Cấu hình thực nghiệm" |
| 5 | Thực nghiệm chạy **trên máy chủ riêng** dùng bản sao CSDL; đổi cấu hình thì xóa `answer_cache` | Cờ áp dụng toàn hệ thống, không để sinh viên thật nhận câu trả lời của RAG cơ bản | `specs/2.7`, R-58 |
| 6 | Ba chỉ số truy xuất do script gọi thẳng Bộ chuẩn hóa → Bộ truy xuất lai → Bộ xếp hạng lại để lấy k mã đoạn theo thứ tự; không đi qua API | API chỉ trả các nguồn đã trích dẫn | `specs/2.7` |
| 7 | **QT1:** vẫn stream; sinh xong kiểm **≥1 trích dẫn hợp lệ**. Không đạt thì gửi sự kiện **thay câu trả lời đã hiển thị** bằng thông báo không đủ căn cứ + phòng ban, `answer_status = no_context`, không lưu đệm | Giữ tốc độ hiển thị dần mà vẫn bảo đảm QT1 | 2.5.2 msg 33–41, 2.7.2a, QA-1 |
| 8 | **QT2 dùng hai ngưỡng:** ngưỡng căn cứ (cao) quyết định có trả lời không; ngưỡng chọn nhóm tri thức (thấp) để chỉ phòng ban | Câu không đủ căn cứ vẫn chỉ đúng phòng ban | `specs/2.5` |
| 9 | `answer_status` ∈ `answered`, `out_of_scope`, `injection`, `no_context`, `error` (CHECK trong SQL). LLM lỗi giữa chừng chỉ lưu thông báo `error`. Câu trả lời chỉ lưu **sau** bước kiểm trích dẫn, kể cả khi client ngắt | Không lưu câu chưa kiểm vào lịch sử/đệm | `specs/2.5`, `2.6` |
| 10 | Truy xuất lọc `status = active`, chưa hết hạn, đúng khóa/ngành (`audiences`); ưu tiên nguồn chính thức (`documents.is_official`) | QT3, QT4 | 2.5.2 msg 19–21 |
| 11 | Bộ truy xuất **đọc `knowledge_groups.cache_epoch` trước khi tìm kiếm**, trả đoạn kèm nhóm tri thức + epoch đã đọc | Để Ngọc chỉ ghi đệm khi epoch chưa đổi (QT6), tránh lưu câu trả lời dùng tài liệu vừa bị thay | 2.5.2 msg 16–17, 22 |
| 12 | Lịch sử hội thoại do API đọc từ CSDL theo mã hội thoại (bỏ lượt bị từ chối) rồi truyền vào `prepare_query()`; khung chat chỉ gửi mã hội thoại | Client không gửi lịch sử giả được | 2.5.1–2.5.3 msg 5–6, QA-18 |
| 13 | Bản scan: trích xuất xong chờ admin kiểm tra/sửa rồi mới chia đoạn, lập chỉ mục | CN10 | 2.5.4, 2.7.2b |

### 4.2. Phần của Ngọc (để biết)
- 3 tác nhân: Sinh viên, Quản trị viên, Dịch vụ LLM. Ứng dụng vỏ **không** phải tác nhân, chỉ xuất hiện ở 2.5.0 và 2.7.1. CN10–CN14 là xử lý nội bộ, không vẽ use case.
- **Bộ nhớ đệm:** không có khóa đệm chung; khóa = băm(câu độc lập, khóa, ngành); sinh viên chưa có khóa/ngành thì không đọc/ghi đệm. `expires_at` = min(+7 ngày, 00:00 ngày sau hạn sớm nhất của đoạn nguồn).
- **Hủy đệm theo nhóm tri thức** khi nạp mới / cập nhật phiên bản / xóa mềm: tăng `cache_epoch`, xóa đệm, rồi mới đổi trạng thái tài liệu, trong một giao dịch, khóa theo thứ tự nhóm → tài liệu.
- Xóa tài liệu = xóa mềm (`status = deleted`); hết hạn suy từ `expiry_date`. Cập nhật phiên bản: `supersedes_id`, bản cũ `superseded`, bản mới lỗi thì giữ bản cũ.
- Đánh giá câu trả lời (2.5.6a) kiểm câu trả lời thuộc hội thoại của sinh viên; xem phản hồi (2.5.6b) chỉ admin.
- Màn Cấu hình là công cụ thực nghiệm, không phải chức năng nghiệp vụ nên không vẽ use case.

## 5. Hợp đồng chung cần chốt sớm (chi tiết ở mục 0 của checklist 03 và 04)
- Lược đồ CSDL theo `import/2.6-csdl.sql`: Ngọc viết model + migration; Khánh dùng các cột của `chunks`.
- Tách `RagChain` thành `prepare_query()` và `answer_stream()` để Ngọc chèn bộ nhớ đệm giữa hai bước.
- Kết quả trả về: `answer_status`, `related_questions`, nguồn có `chunk_id`, `document_id`, đoạn trích, tên văn bản, ngày ban hành, Điều/Khoản.
- Sự kiện stream "thay câu trả lời", epoch trả về từ bộ truy xuất, lịch sử do API truyền vào.
- Danh sách cờ thực nghiệm (mục 4.1 dòng 4).
