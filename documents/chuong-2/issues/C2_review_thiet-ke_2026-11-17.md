# Review vòng 1 — Tech lead (GVHD)

- Ngày: 2026-11-17. Đối tượng: bàn giao `issues/C2_dev_thiet-ke_2026-11-17.md`.
- Căn cứ duy nhất: `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md` (ĐA) và Hình 1 (`imgs/hình 1.png`).
- Đã xem: 12 ảnh `demo/*.png`; 5 file `import/2.5.*-tuan-tu-*.txt`; `import/2.6-csdl.sql`; grep `2.6.2-erd.xml`, `2.7.*.xml`, `tools/gen_component.py`; 6 file specs, `README.md`. Bỏ qua các file lỗi thời có trong danh sách của bàn giao.

## Kiểm lại số liệu (đếm trên file thật)
| Mục | Spec ghi | Đếm lại | Kết quả |
|---|---|---|---|
| 2.5.1–2.5.5 số message | 14/34/25/22/17 | 14/34/25/22/17 (bỏ dòng `alt/else/opt/loop/end`, tính `note`) | Khớp |
| 2.6 số bảng / khóa ngoại | 11 / 13 | 11 `CREATE TABLE` / 13 `FOREIGN KEY` | Khớp |
| 2.7.1 thành phần / phụ thuộc | 18 / 23 | `COMPONENTS` 18, `DEPENDENCIES` 23 (`gen_component.py` dòng 21–51) | Khớp |
| 2.7.2a nút / luồng | 15 / 17 | 15 / 17 (đếm trên ảnh) | Khớp |
| 2.7.2b nút / luồng | 12 / 13 | 12 / 13 (đếm trên ảnh) | Khớp |
| Tên bảng/cột trong 2.5, 2.7, truy-vet | — | `messages.from_cache`, `answer_status`, `rewritten_question`, `related_questions`, `knowledge_groups.department`, `documents.supersedes_id/status/audience/expiry_date`, `chunks.section_path/tokenized_text/embedding/cohorts/expiry_date`, `users.cohort/major`, `answer_cache.expires_at`, `answer_cache_documents` đều có trong SQL | Khớp |
| Thứ tự luồng truy vấn so với Hình 1 | (1)→(2)→(3)→(4)→(5)→(6)→(7)→(8)→(9)→(10) | Đúng ở 2.5.1–2.5.3 và 2.7.2a; các nhánh từ chối nhập lại ở (9) qua nút R (nút hợp nhất) | Khớp |

Điểm tốt: bám đúng thứ tự Hình 1 (viết lại ở bước 2, trước kiểm tra phạm vi và tra đệm); 3 tác nhân đúng Bảng 2; câu từ chối có lưu hội thoại nhưng không lưu vào bộ nhớ đệm (ĐA mục 5); cột nghiệp vụ của CN07 có đủ (nhóm, nguồn, ngày ban hành, hết hạn, đối tượng); truy vết có đủ CN01–CN14 và QT1–QT7.

## Bảng finding

| Mã | Mức độ | Biểu đồ / file (dòng) | Vấn đề | Căn cứ ĐA | Đề xuất sửa |
|---|---|---|---|---|---|
| R-1 | **Major** | `import/2.5.1…txt` d.20; `2.5.2…txt` d.24, d.26; `2.6-csdl.sql` d.125, d.134; `specs/2.5-tuan-tu.md` d.21 | Khóa bộ nhớ đệm chỉ là băm câu hỏi đã viết lại (`question_key` UNIQUE), trong khi truy xuất ở 2.5.2 lại ưu tiên theo **khóa, ngành của sinh viên**. Kết quả: SV khóa D22 có thể nhận câu trả lời đệm đã sinh cho SV D21 (học phí, chuẩn đầu ra khác nhau theo khóa). | QT4; Bảng 3 (Học phí "thay đổi theo ngành, khóa"); Bảng 1 dòng 3 (3/4 câu lệch khóa, ngành) | Chọn một trong hai và ghi rõ: (a) khóa đệm = băm(câu hỏi độc lập + khóa + ngành), thêm cột `cohort`, `major` vào `answer_cache`, đổi UNIQUE thành (`question_key`, `cohort`, `major`); hoặc (b) chỉ lưu đệm câu trả lời không phụ thuộc đối tượng (mọi đoạn nguồn có `cohorts` rỗng). Sửa nhãn message 2.5.1 d.20 và 2.5.2 d.24, d.50 cho khớp. |
| R-2 | **Major** | `import/2.5.5…txt` d.11, d.15–18; `specs/2.5-tuan-tu.md` d.42 | Điều kiện `alt [Khác đối tượng áp dụng]` không thể đánh giá: quản trị viên chỉ nhập "ngày ban hành, ngày hết hạn" (d.11), CSDL chỉ trả đối tượng của **bản cũ** (d.15); không có giá trị đối tượng của bản mới để so. | CN08 "văn bản mới có cùng đối tượng áp dụng"; QT3 "(cùng đối tượng áp dụng)" | Message d.11 nhập thêm **đối tượng áp dụng** (và nguồn) của văn bản mới; d.12 gửi kèm; thêm self-message "So sánh đối tượng áp dụng bản mới với bản cũ" trước `alt`. Hoặc bỏ `alt`, quy định bản mới kế thừa đối tượng của bản cũ — nhưng khi đó phải xóa nhánh lỗi. |
| R-3 | **Major** | `2.6-csdl.sql` d.69, d.107, d.142; `2.2.3` UC "Xóa tài liệu"; không có tuần tự xóa | (1) `message_sources.chunk_id` FK mặc định RESTRICT (d.107) chặn `ON DELETE CASCADE` từ `documents` → `chunks` (d.69): tài liệu nào **đã từng được trích dẫn** thì không xóa được. (2) Xóa tài liệu chỉ cascade xóa dòng liên kết `answer_cache_documents` (d.142), còn dòng `answer_cache` vẫn còn → câu trả lời đệm dựa trên tài liệu đã xóa vẫn được trả. | CN07 "xóa tài liệu"; CN05 (lịch sử vẫn phải xem được nguồn); QT1 "chỉ trả lời dựa trên tài liệu đã nạp"; QT6, CN13 "hết hạn theo tài liệu nguồn" | Dùng xóa mềm: thêm `deleted` vào `documents.status`, bỏ khỏi truy xuất, giữ chunk cho lịch sử; khi xóa thì hủy đệm giống bước (F) (`DELETE FROM answer_cache WHERE id IN (SELECT cache_id FROM answer_cache_documents WHERE document_id = …)`). Ghi quy tắc này ở 2.6 và thêm 1–2 message vào đặc tả UC "Xóa tài liệu". |
| R-4 | **Major** | `specs/2.1-tac-nhan-thuat-ngu.md` d.13; `2.5.*` message "Xác thực phiên…"; `gen_component.py` d.43–44; `truy-vet.md` d.6 | CN01 có yêu cầu riêng "danh tính do ứng dụng vỏ truyền sang (mô phỏng)", nhưng không biểu đồ nào thể hiện: 2.1 nói "được mô tả trong **đặc tả UC01**" nhưng không có đặc tả UC01 ở đâu; 2.5 chỉ có self-message "Xác thực phiên sinh viên"; 2.7.1 Ứng dụng vỏ chỉ "nhúng" Khung chat. Đăng nhập bằng mã SV và nhận khóa/ngành (dùng cho QT4 ở R-1) cũng chưa có luồng. | CN01; ĐA mục 2 "Nền tảng"; Bảng 8 dòng 6 (ứng dụng vỏ WebView) | Thêm tuần tự **2.5.0 Đăng nhập** với 2 nhánh `alt`: (a) SV nhập mã SV + mật khẩu; (b) Ứng dụng vỏ mở WebView kèm danh tính (mã SV, khóa, ngành) → API xác thực kiểm tra → tạo/cập nhật `users` → đặt phiên. Trên 2.7.1 thêm phụ thuộc Ứng dụng vỏ → API xác thực (nhãn "truyền danh tính"). Sửa câu tham chiếu ở 2.1 d.13. |
| R-5 | **Major** | `demo/2.6.2-erd.png` (toàn bộ 11 hộp) | Ảnh ERD **không hiện tên bảng**: thanh tiêu đề 11 hộp đều trống; người đọc chỉ đoán bảng qua cột. Tên có trong model (`<DBTable Name="users"…>`), lỗi nằm ở hiển thị khi xuất ảnh. Hình chính của 2.6.2 như vậy không dùng được trong quyển. | Bảng 8 dòng 3 (đầu ra "CSDL" của chương 2) | Kiểm tra thuộc tính hiển thị tên của shape trong `gen_erd.py` (d.64–70, `ModelElementNameAlignment`, chiều cao header) hoặc bật "Show name" trên VP rồi xuất lại; xem lại ảnh trước khi bàn giao. |
| R-6 | **Major** | `specs/2.5-tuan-tu.md` d.5, d.10; `2.5.*.txt` participant `API`; `2.7.1` (`gen_component.py` d.15, d.25–27, d.38); `2.5.4…txt` d.13–14 | Không thống nhất lifeline 2.5 với thành phần 2.7.1: (1) lifeline "Máy chủ API (FastAPI)" là **gói** ở 2.7.1, không phải thành phần; thành phần thật là API hỏi đáp / API xác thực / API quản trị — spec d.5 lại khẳng định "trùng tên thành phần". (2) Thành phần "Kho tệp tài liệu" (có phụ thuộc API quản trị → FILES) không xuất hiện ở tuần tự nào; 2.5.4 không có bước lưu tệp, CSDL chỉ có `file_name`, không có đường dẫn lưu trữ. (3) Xác thực vẽ thành self-message trên API dù 2.7.1 có thành phần API xác thực. | Yêu cầu thống nhất giữa các mục của Chương 2 (Bảng 8 dòng 3) | Đổi lifeline: "API hỏi đáp" cho 2.5.1–2.5.3, "API quản trị" cho 2.5.4–2.5.5 (giữ chú thích "thuộc Máy chủ API"). 2.5.4 thêm message "Lưu tệp gốc" → lifeline "Kho tệp tài liệu"; `documents` thêm cột `storage_path`. Xác thực: hoặc gọi API xác thực, hoặc ghi rõ trong spec là middleware dùng chung. |
| R-7 | Minor | `2.5.3…txt` d.34–35; `specs/2.5` d.35 | Khi "không đủ căn cứ" thì chưa rõ lấy **nhóm tri thức nào** để tra phòng ban (câu hỏi chưa được gán nhóm; có thể không có đoạn nào liên quan). Không có phòng ban mặc định. | QT2; Hình 1 nhánh (7) "không" → "chỉ phòng ban phụ trách" | Ghi quy tắc: nhóm của đoạn có điểm cao nhất sau bước (6); nếu không có đoạn thì dùng phòng ban mặc định (cấu hình). Thêm tham số vào message d.34. |
| R-8 | Minor | `demo/2.2.2`, `demo/2.2.3`; `specs/2.2-usecase.md` d.12 | Dùng `<<extend>>` cho chức năng **bắt buộc** của UC cha: "Đặt câu hỏi mới" (thiếu nó thì "Hỏi đáp" vô nghĩa), "Xem danh sách nguồn", "Xem danh sách hội thoại", "Xem danh sách tài liệu", "Tải lên tài liệu". Theo UML, UC cơ sở phải hoàn chỉnh khi không có extend. Hội đồng thường hỏi điểm này. | Chuẩn UML (extend = hành vi tùy chọn, có điều kiện) | "Đặt câu hỏi mới"/"Hỏi nối tiếp" → quan hệ tổng quát hóa (là hai dạng của Hỏi đáp); các UC "Xem danh sách…" → `<<include>>` hoặc gộp vào UC cha; giữ `<<extend>>` cho Đổi tên, Xóa, Gửi góp ý, Cập nhật phiên bản, Kiểm tra bản scan (ghi điều kiện "tài liệu là bản scan"). Nếu giữ cách PTIT quen dùng thì ghi một câu giải thích quy ước ở 2.2. |
| R-9 | Minor | `2.5.2…txt` d.37; `truy-vet.md` d.27; `2.6-csdl.sql` d.65 | QT4 vế 2 "câu hỏi chưa rõ đối tượng thì trình bày theo từng trường hợp (từng khóa, ngành)" không thể hiện ở đâu. `chunks` có `cohorts`, `academic_year` nhưng không có ngành, trong khi 2.5.2 truyền cả ngành. | QT4; Bảng 6 dòng 3 | Thêm vào yêu cầu gửi LLM (d.37): "nếu chưa rõ đối tượng thì trình bày theo từng khóa, ngành"; cập nhật truy-vet. Thêm `chunks.majors` hoặc ghi rõ ngành chỉ lấy từ `documents.audience`. |
| R-10 | Minor | `2.5.2…txt` d.44–46 | Không có bước kiểm tra sau sinh: nếu LLM trả lời có nội dung nhưng **không có trích dẫn hợp lệ** thì vẫn hiển thị và lưu đệm. | QT1 "mỗi câu trả lời có nội dung phải kèm ít nhất một nguồn"; CN14 | Sau d.45 thêm self-message của Bộ sinh "Kiểm tra ≥1 trích dẫn hợp lệ" kèm note: không đạt thì chuyển thành thông báo không đủ căn cứ, không lưu đệm. |
| R-11 | Minor | `2.5.4…txt` d.18–24; `2.5.5…txt` d.19 | (1) Bước kiểm tra bản scan (C) vẽ như đồng bộ trong một yêu cầu tải lên; thực tế tài liệu nằm ở trạng thái `needs_review`, quản trị viên quay lại sau. (2) 2.5.5 d.19 gói trích xuất, kiểm tra scan, chia đoạn vào một self-message "như 2.5.4", ẩn mất các lifeline Bộ trích xuất / Bộ chia đoạn. | Hình 1 (C) là thao tác thủ công của quản trị viên; CN10 | (1) Kết thúc 2.5.4 ở "chờ kiểm tra" trong `opt`, tách phần quản trị viên xác nhận thành tương tác riêng (hoặc ghi note "bất đồng bộ"). (2) Dùng khung `ref` "Nạp tài liệu (2.5.4)" — nếu import text của VP không nhận `ref` thì vẽ tay sau import. |
| R-12 | Minor | `demo/2.7.2b` nút "Thay thế bản cũ cùng đối tượng?"; `2.5.4`, `2.5.5`; `specs/2.5` d.38–42 | 2.7.2b đặt quyết định thay thế **sau** (E) giống Hình 1, còn 2.5.5 kiểm tra đối tượng **trước** khi trích xuất và tách thành luồng riêng do quản trị viên khởi phát; 2.5.4 không có nhánh này. Không có câu nào giải thích ánh xạ. | Hình 1 nhánh (E) → ◇ → (F) | Thêm vào spec 2.5: "2.5.4 = nhánh [không]; 2.5.5 = nhánh [có] của Hình 1; quyết định do quản trị viên chọn 'Cập nhật phiên bản'"; đổi guard 2.7.2b thành "[quản trị viên chọn thay thế bản cũ cùng đối tượng]". |
| R-13 | Minor | `demo/2.7.2a`, `demo/2.7.2b` | Biểu đồ hoạt động không có phân vùng (partition): không thấy hành động nào của Sinh viên / Quản trị viên / Dịch vụ LLM / Hệ thống. Hình 1 có ký hiệu thao tác thủ công riêng cho (C), bản UML làm mất thông tin này. Kho dữ liệu cũng bị bỏ (spec 2.7 d.24 đã giải thích). | Hình 1 (ký hiệu "Thao tác thủ công (quản trị viên)") | Thêm partition: 2.7.2a {Sinh viên, Hệ thống, Dịch vụ LLM}; 2.7.2b {Quản trị viên, Hệ thống}. Có thể thêm `«datastore»` Bộ nhớ đệm, CSDL cho bước (4), (10), (F) để giữ ý "dùng chung" của ĐA mục 5. |
| R-14 | Minor | `2.6-csdl.sql` d.43, d.65, d.90, d.128–129 | Một số cột vi phạm 1NF hoặc khó truy vấn: `answer_cache.sources` TEXT, `related_questions` TEXT (JSON), `chunks.cohorts` VARCHAR nhiều giá trị, `documents.audience` văn bản tự do (CN08 so sánh "cùng đối tượng" bằng chuỗi). Khi trúng đệm (2.5.1 d.24) phải dựng lại `message_sources` (cần `chunk_id` NOT NULL) từ chuỗi `sources`. | CN08, CN03, CN13 | Dùng `JSONB`/`TEXT[]` và giải thích lý do, hoặc tách `answer_cache_sources(cache_id, chunk_id, citation_no, excerpt)` (khi đó `answer_cache_documents` suy ra được). Chuẩn hóa `audience` thành cấu trúc (khóa, ngành, hệ) để so sánh được. |
| R-15 | Minor | `2.6-csdl.sql` d.171 | Trạng thái `expired` của tài liệu không có tiến trình nào đặt; QT3 thực tế dựa vào lọc `expiry_date`. | QT3, QT6 | Bỏ `expired` (suy từ `expiry_date`), hoặc mô tả tác vụ định kỳ đặt `expired` + hủy đệm. |
| R-16 | Minor | `2.5.3…txt` d.21; `specs/2.5` d.34 | Nhánh từ chối không nhắc nhóm câu hỏi **ngoài phạm vi đồ án** nhưng trong miền sinh viên: tra điểm cá nhân, lịch thi cá nhân, công nợ, đăng ký học phần, nộp đơn. Đây là loại câu hội đồng dễ thử nhất. | ĐA mục 2 "Ngoài phạm vi"; QT7 | Ghi rõ trong guard/spec: câu hỏi dữ liệu cá nhân hoặc giao dịch → từ chối và hướng dẫn tới hệ thống quản lý đào tạo hoặc phòng ban; `answer_status` dùng `out_of_scope`. |
| R-17 | Minor | `import/2.5.*.txt` d.1–2 và các khối `alt/opt/loop/note` | Rủi ro khi import vào VP: dòng `title`, `autonumber` (không có số bắt đầu) và các khối `alt/else/opt/loop/note`, dòng thụt lề **chưa thử**; file thử ngày 16/11 (`2.5.1-v1.txt`) đã không còn để đối chiếu. current-status 2026-11-16 đã ghi VP đánh số lồng `1.1.1`. | — (khả thi import) | Thử 2.5.3 (alt + note) và 2.5.2 (loop) trước. Nếu `autonumber` hoặc `title` lỗi thì bỏ, dùng đánh số của VP và đặt tên biểu đồ trên VP. Ghi kết quả thử vào README. |
| R-18 | Minor | `specs/` (thiếu); `truy-vet.md` d.5–19 | So với kế hoạch Chương 2 (`human-workspace/spec/02-…md`), còn thiếu 2.2.4 (CN10–CN14), 2.2.5 (QT), 2.3 (phi chức năng), 2.4 (đặc tả UC). Chưa có tuần tự cho CN06 → CN09, là vòng khép kín "định kỳ xem câu trả lời không hữu ích để bổ sung tài liệu". CN03 "bấm xem đoạn gốc" và CN05 đúng là đọc đơn giản, không bắt buộc vẽ. | ĐA 3.3 đoạn cuối; CN06, CN09; Bảng 8 dòng 3 | Chưa chặn vòng này vì bàn giao chỉ nhận phần biểu đồ, nhưng phải có trước khi viết quyển. Đề xuất thêm 1 tuần tự gộp "SV đánh giá → QTV xem phản hồi" (truy vấn `feedback` + `messages.answer_status IN (no_context)`). |
| R-19 | Minor | `specs/2.1-tac-nhan-thuat-ngu.md` d.28, d.31, d.33, d.43 | Thuật ngữ thừa hoặc lệch so với thiết kế: "Đoạn cha / đoạn con", "Truy vấn đa hướng", "RRF" không xuất hiện ở biểu đồ nào; "Kho tài liệu (Dataset)" là tên của baseline, trong khi thiết kế dùng "Nhóm tri thức" (`knowledge_groups`), mà thuật ngữ này lại không có trong bảng. | Bảng 3 "Nhóm tri thức" | Thay "Kho tài liệu" bằng "Nhóm tri thức"; bỏ hoặc đánh dấu "chi tiết cài đặt" cho các thuật ngữ không dùng; thêm "Phòng ban phụ trách", "Phiên bản/bị thay thế". |
| R-20 | Nit | `2.5.5…txt` d.17, d.23–24 | Nhánh lỗi không có `ADM-->QTV` hiển thị lỗi. Hai lệnh ghi d.23–24 nên gộp trong một giao dịch (note hiện có chưa nói rõ). | — | Thêm `ADM-->QTV: Hiển thị lỗi`; sửa note thành "d.21–25 trong một giao dịch; lỗi thì hoàn tác, giữ bản cũ". |
| R-21 | Nit | `demo/2.2.1` | Tác nhân phụ "Dịch vụ LLM" đặt bên trái cạnh Sinh viên; các đường liên kết của Sinh viên cắt nhau. | Quy ước trình bày UML | Chuyển Dịch vụ LLM sang phải, ngoài khung hệ thống; sắp lại UC để giảm số đường cắt. |
| R-22 | Nit | `demo/2.7.1` | Gói có tab tên rỗng ở góc trái, tên gói nằm giữa thanh; nhiều phụ thuộc đi xuyên thành phần khác (bàn giao đã biết); không có stereotype `«use»`. | — | Kéo lại đường trên VP; cân nhắc gom phụ thuộc API hỏi đáp → 6 bộ thành một đường tới gói "Lõi RAG – luồng truy vấn" cho dễ đọc. |
| R-23 | Nit | `demo/2.6.2-erd.png` | Nhãn khóa ngoại bị cắt (`fk_documen…`, `fk_conversa…`) và đè lên đường; đường tự tham chiếu `supersedes_id` chưa vẽ (bàn giao đã biết). | — | Ẩn tên FK hoặc kéo lại; vẽ tay đường tự tham chiếu trước khi chụp vào quyển. |
| R-24 | Nit | `demo/2.7.2a` nút (10) | Nhánh trúng đệm (4)[có] cũng đi qua (10) "chỉ lưu câu trả lời có căn cứ vào bộ nhớ đệm", dễ hiểu là ghi đệm lại. Hình 1 cũng như vậy. | Hình 1 (10) | Thêm chú thích "không ghi lại nếu lấy từ đệm" (hoặc "tăng `hit_count`"). |
| R-25 | Nit | `demo/2.7.2a` nút (5) | Nhãn chỉ ghi "bỏ tài liệu đã hết hạn", thiếu "bị thay thế" (2.5.2 d.30 đã có). Nhãn của Hình 1 cũng vậy. | QT3 | Thêm "/ bị thay thế" hoặc ghi chú QT3 ở spec 2.7. |

## Tổng hợp
- Blocker: 0 · **Major: 6** (R-1 … R-6) · Minor: 13 (R-7 … R-19) · Nit: 6 (R-20 … R-25).

## Kết luận: **Không đạt**
Còn 6 finding Major. R-1, R-2, R-3 là lỗi logic nghiệp vụ so với QT4, CN08, CN07/QT1/QT6. R-4 thiếu thiết kế cho yêu cầu đặc thù của CN01. R-5 làm hình ERD không dùng được. R-6 làm lifeline 2.5 không khớp thành phần 2.7.1. Dev cần sửa hết Major (khuyến nghị sửa luôn R-7, R-8, R-10, R-16 vì hội đồng dễ hỏi) rồi bàn giao vòng 2. Mục "Bàn giao cho hội đồng" sẽ viết khi review đạt.

---

## Phản hồi của agent dev — vòng 2 (2026-11-17)
User duyệt "sửa theo agent review" (kể cả thêm 2 tuần tự 2.5.0 và 2.5.6). Mọi ảnh trong `demo/` đã sinh lại và xem toàn bộ; số liệu trong specs đếm lại bằng grep.

| Mã | Đã sửa | File |
|---|---|---|
| R-1 | Khóa đệm = băm(câu hỏi độc lập + khóa + ngành); `answer_cache` thêm `cohort`, `major`; message tra/ghi đệm ở 2.5.1–2.5.3 ghi "(câu hỏi độc lập, khóa, ngành)"; khóa, ngành lấy từ API xác thực | `2.6-csdl.sql`, `tools/sequence_specs.py`, `specs/2.5`, `2.6` |
| R-2 | 2.5.5: QTV nhập cả nguồn và đối tượng áp dụng của văn bản mới; thêm self-message so sánh trước `alt`; nhánh lỗi có `ADM-->QTV` (gộp R-20) | `sequence_specs.py` |
| R-3 | Xóa mềm (`status = deleted`), giữ đoạn cho lịch sử, hủy đệm theo tài liệu; mô tả ở 2.2.3 và 2.6 "Quy tắc dữ liệu" | `2.6-csdl.sql`, `specs/2.2`, `2.6` |
| R-4 | Thêm tuần tự **2.5.0 Đăng nhập** (2 alt: trình duyệt / ứng dụng vỏ; hợp lệ → lấy câu hỏi phổ biến); `users.auth_source`, `password_hash` cho phép rỗng; 2.7.1 thêm phụ thuộc Ứng dụng vỏ → API xác thực "truyền danh tính"; sửa tham chiếu ở 2.1 | `sequence_specs.py`, `gen_component.py`, `2.6-csdl.sql`, `specs/2.1` |
| R-5 | Bật lại caption bảng (chính là tên bảng); ẩn tên FK bằng `ShowConnectorName="1"`; xếp lại bảng có quan hệ cạnh nhau. Lỗi đã ghi vào `learn.md` | `tools/gen_erd.py`, `tools/run_erd.sh` |
| R-6 | Lifeline đổi thành API hỏi đáp / API quản trị / API xác thực (thành phần thật); kiểm tra phiên là message tới API xác thực; 2.5.4 thêm Kho tệp tài liệu (lưu tệp gốc), `documents.storage_path` | `sequence_specs.py`, `2.6-csdl.sql` |
| R-7 | Phòng ban theo nhóm của đoạn điểm cao nhất; không có đoạn → `knowledge_groups.is_default` | 2.5.3, sql |
| R-8 | Đặt câu hỏi mới/Hỏi nối tiếp, Chọn câu hỏi phổ biến/liên quan → tổng quát hóa; Xem danh sách hội thoại/tài liệu, 2 UC con của Xem phản hồi → include; extend chỉ cho hành vi tùy chọn; quy ước ghi ở 2.2. "Xem danh sách nguồn" gộp vào UC cha | `tools/gen_usecase.py`, `usecase_specs.py`, `specs/2.2` |
| R-9 | Yêu cầu gửi LLM thêm "chưa rõ thì trình bày theo từng khóa, ngành"; đối tượng (khóa, ngành) tách bảng `audiences` cho tài liệu hoặc từng đoạn | 2.5.2, sql |
| R-10 | Thêm self-message "Kiểm tra có ít nhất một trích dẫn hợp lệ (QT1)" + note xử lý khi không đạt | 2.5.2 |
| R-11 | (1) note "bất đồng bộ" trong `opt` bản scan; (2) giữ self-message "(tham chiếu 2.5.4)" — không dùng `ref` vì chưa chắc import text của VP nhận; ghi lý do ở specs/2.5 | 2.5.4, 2.5.5 |
| R-12 | Specs 2.5/2.7 ghi 2.5.4 = nhánh [không], 2.5.5 = nhánh [có]; quyết định 2.7.2b đổi thành "Cập nhật phiên bản cho bản cũ?" | `activity_specs.py`, specs |
| R-13 | **Không thêm partition**: không có mẫu XML swimlane của VP; Hình 1 cũng không có làn; tên hành động đã nêu người thực hiện. Ghi lý do ở specs/2.7; nếu GVHD cần thì thêm trên VP | specs/2.7 |
| R-14 | Tách `answer_cache_sources` (thay `answer_cache_documents` + cột `sources`), `audiences` (thay `documents.audience`, `chunks.cohorts`); `related_questions` giữ TEXT (JSON) có giải thích — VP không đọc JSON/JSONB | sql, specs/2.6 |
| R-15 | Bỏ `expired`; hết hạn suy từ `expiry_date` | sql, specs/2.6 |
| R-16 | Kiểm soát đầu vào gồm "yêu cầu dữ liệu cá nhân hoặc giao dịch"; nhánh từ chối hướng dẫn kênh phù hợp | 2.5.1–2.5.3 |
| R-17 | Chưa thử được (import text chỉ có trên giao diện VP) — đã nhờ user thử; ghi hướng xử lý ở specs/2.5 | README, specs/2.5 |
| R-18 | Thêm tuần tự **2.5.6 Đánh giá → Xem phản hồi**. Phần văn bản 2.2.4, 2.2.5, 2.3, 2.4 để task sau (user đồng ý phạm vi vòng này chỉ biểu đồ) | `sequence_specs.py` |
| R-19 | Bỏ RRF, đoạn cha/con, truy vấn đa hướng, "Kho tài liệu"; thêm Nhóm tri thức, Phòng ban phụ trách, Phiên bản/bị thay thế | specs/2.1 |
| R-20 | Gộp vào R-2; note giao dịch ghi rõ 3 bước ghi | 2.5.5 |
| R-21 | Dịch vụ LLM chuyển sang phải, ngoài khung; QTV dời xuống để đường tới Đăng nhập không thẳng hàng với đường của SV | usecase_specs |
| R-22 | Bỏ nhãn "streaming" chồng chữ; tab gói rỗng là cách VP vẽ gói khi import — chưa xử lý | gen_component |
| R-23 | Tên FK đã ẩn; đường tự tham chiếu vẫn phải kéo tay (ghi ở specs/2.6) | gen_erd |
| R-24 | Nhãn (10): "chỉ lưu câu trả lời **mới sinh** có căn cứ vào bộ nhớ đệm" | activity_specs |
| R-25 | Nhãn (5): "bỏ tài liệu hết hạn, bị thay thế" | activity_specs |

Số liệu mới: use case 3/9/11 assoc/5 inc/3 ext · 2/15/6/1/5 + 4 tổng quát hóa · 1/10/3/3/5. Tuần tự (message/lifeline): 2.5.0 19/6 · 2.5.1 16/8 · 2.5.2 36/12 · 2.5.3 26/10 · 2.5.4 25/9 · 2.5.5 20/7 · 2.5.6 15/7. CSDL 12 bảng, 15 FK. Kiến trúc 18 thành phần, 24 phụ thuộc. Hoạt động 15/17 và 12/13.


---

# Review vòng 2 — Tech lead (GVHD)

- Ngày: 2026-11-17. Đối tượng: mục "Phản hồi của agent dev — vòng 2" ở trên.
- Đã xem lại cả 14 ảnh `demo/*.png` (riêng 2.5.1–2.5.3 thì đối chiếu bằng file `.txt` cùng nguồn), 7 file `import/2.5.*.txt`, `import/2.6-csdl.sql`, `tools/gen_component.py`, `tools/usecase_specs.py`, cùng toàn bộ specs và README.
- **Đính chính vòng 1:** bảng "Kiểm lại số liệu" của vòng 1 ghi "tính `note`" là sai. Số message thực ra **không** tính note, đúng như quy ước dev ghi ở `specs/2.5` ("Message = số mũi tên, không tính note"). Các con số của vòng 1 vẫn đúng.

## Kiểm lại số liệu vòng 2
| Mục | Spec ghi | Đếm lại | Kết quả |
|---|---|---|---|
| Tuần tự 2.5.0–2.5.6: message / lifeline | 19/6 · 16/8 · 36/12 · 26/10 · 25/9 · 20/7 · 15/7 | Đếm mũi tên `->` và dòng `participant` bằng grep: ra đúng các số này | Khớp |
| CSDL: số bảng / khóa ngoại | 12 / 15 | 12 `CREATE TABLE`, 15 `FOREIGN KEY` | Khớp |
| Kiến trúc: thành phần / phụ thuộc | 18 / 24 | `COMPONENTS` 18, `DEPENDENCIES` 24 (thêm SHELL → API_AUTH) | Khớp |
| Use case: quan hệ | 5 inc/3 ext · 1 inc/5 ext/4 gen · 3 inc/5 ext | Đúng như khai báo trong `usecase_specs.py` dòng 39–41, 79–84, 112–116 | Khớp |
| Tên bảng/cột nhắc trong 2.5, 2.7, truy-vet | — | `audiences`, `answer_cache_sources`, `storage_path`, `auth_source`, `is_default`, `answer_cache.cohort/major`, `status = deleted/needs_review` đều có trong SQL. Không còn chỗ nào nhắc `chunks.cohorts`, `documents.audience`, `answer_cache_documents`, `expired` | Khớp |

## Trạng thái R-1 … R-25
| Mã | Trạng thái | Ghi chú kiểm |
|---|---|---|
| R-1 | Đã sửa | `answer_cache` có `cohort`, `major`; `question_key` là băm của câu hỏi + khóa + ngành (SQL d.137–140, comment d.217). 2.5.1 d.22, 2.5.2 d.26 và d.54, 2.5.3 d.28 đều truyền khóa, ngành. Hệ quả về tỷ lệ trúng đệm: xem R-28. |
| R-2 | Đã sửa | 2.5.5 d.12 nhập cả đối tượng áp dụng; d.18 có self-message so sánh; nhánh lỗi có `ADM-->QTV` (d.21). |
| R-3 | Đã sửa | Xóa mềm: `status = deleted` (SQL d.189) và hủy đệm theo tài liệu (`specs/2.6` mục "Quy tắc dữ liệu", `specs/2.2` d.48). Đoạn được giữ lại nên FK RESTRICT của `message_sources` không còn chặn. |
| R-4 | Đã sửa | Có tuần tự 2.5.0 với hai nhánh trình duyệt / ứng dụng vỏ; có `users.auth_source`; 2.1 không còn tham chiếu treo. Hai lỗi nhỏ mới: R-26, R-27. |
| R-5 | Đã sửa | ERD hiện đủ tên 12 bảng, tên khóa ngoại đã ẩn, bố cục dễ đọc. |
| R-6 | Đã sửa | Lifeline dùng đúng tên thành phần (API hỏi đáp / quản trị / xác thực); kiểm tra phiên là message tới API xác thực; 2.5.4 có Kho tệp (d.18–19) và `storage_path`. |
| R-7 | Đã sửa | 2.5.3 d.36 lấy nhóm của đoạn có điểm cao nhất, không có thì dùng nhóm mặc định; có `knowledge_groups.is_default`. |
| R-8 | Đã sửa | 2.2.2 dùng tổng quát hóa (mũi tên tam giác rỗng, đúng chiều) cho Hỏi đáp và Gợi ý; dùng include cho Xem danh sách hội thoại / tài liệu và cho 2 UC con của Xem phản hồi; extend chỉ còn cho hành vi tùy chọn. Quy ước được ghi ở `specs/2.2` d.8–11. |
| R-9 | Đã sửa | 2.5.2 d.39 có vế "chưa rõ thì trình bày theo từng khóa, ngành"; bảng `audiences` có `major`; truy-vet QT4 đã cập nhật. |
| R-10 | Đã sửa | 2.5.2 d.48–49: self-message kiểm tra QT1 kèm note xử lý khi không đạt. |
| R-11 | Phần (1) đã sửa; phần (2) chấp nhận lý do | Note "bất đồng bộ" nằm trong `opt` (2.5.4 d.27). Message "(tham chiếu 2.5.4)" chấp nhận được vì import text chưa chắc nhận `ref`; khuyến nghị thay bằng khung `ref` trên VP trước khi chụp hình cho quyển. |
| R-12 | Đã sửa | `specs/2.5` d.103, d.110 và `specs/2.7` d.92 ghi rõ ánh xạ nhánh; guard 2.7.2b đổi thành "Cập nhật phiên bản cho bản cũ?". |
| R-13 | Chấp nhận lý do | Hình 1 cũng không có làn, và tên hành động đã nêu người thực hiện. Lý do được ghi ở `specs/2.7` d.95. Nếu hội đồng hỏi thì thêm làn trên VP. |
| R-14 | Đã sửa | Có thêm `answer_cache_sources` (có `chunk_id`) và `audiences`; giữ `related_questions` dạng TEXT, có giải thích (`specs/2.6` d.30). |
| R-15 | Đã sửa | Đã bỏ trạng thái `expired`; hết hạn suy ra từ `expiry_date` (`specs/2.6` d.27). |
| R-16 | Đã sửa | Guard ở 2.5.1–2.5.3 có "yêu cầu dữ liệu cá nhân hoặc giao dịch"; nhánh từ chối có "hướng dẫn kênh phù hợp". |
| R-17 | Chấp nhận lý do | Import text chỉ chạy được trên giao diện VP, agent không tự thử được. Hướng xử lý khi lỗi đã ghi ở `specs/2.5` d.124–126. **Bắt buộc** user thử trước khi chụp hình cho quyển (xem mục bàn giao). |
| R-18 | Biểu đồ đã sửa; phần văn bản chấp nhận lý do | Có tuần tự 2.5.6 (CN06 → CN09). Các mục 2.2.4, 2.2.5, 2.3, 2.4 để task sau, user đã đồng ý phạm vi vòng này chỉ gồm biểu đồ. |
| R-19 | Đã sửa | Bảng thuật ngữ có Nhóm tri thức (d.32) và Phòng ban phụ trách (d.36); không còn "Kho tài liệu (Dataset)". |
| R-20 | Đã sửa | Gộp vào R-2; note giao dịch ở 2.5.5 d.31. |
| R-21 | Đã sửa | Dịch vụ LLM đã ở bên phải, ngoài khung (2.2.1, 2.2.2). Còn một lỗi hiển thị: R-31. |
| R-22 | Phần nhãn đã sửa; tab gói chấp nhận lý do | Tab rỗng là cách VP vẽ gói khi import. |
| R-23 | Chấp nhận lý do | Đường tự tham chiếu sẽ kéo tay; đã ghi ở `specs/2.6` d.36. |
| R-24 | Đã sửa | Nhãn (10) có "mới sinh"; 2.5.1 d.23 chỉ tăng số lần dùng. |
| R-25 | Đã sửa | Nhãn (5) có "bị thay thế". |

Tổng: 18 mục đã sửa hẳn; 7 mục (R-11, R-13, R-17, R-18, R-21, R-22, R-23) đã sửa một phần hoặc chấp nhận lý do. Không mục nào chưa đạt.

## Finding mới
| Mã | Mức độ | Biểu đồ / file (dòng) | Vấn đề | Căn cứ | Đề xuất sửa |
|---|---|---|---|---|---|
| R-26 | Minor | `import/2.5.0…txt` d.20–23; `demo/2.5.0` message 9–10 | Ở nhánh ứng dụng vỏ, tài khoản được **tạo hoặc cập nhật** (msg 10) trước khi biết danh tính hợp lệ: `alt [Không hợp lệ]` đứng sau msg 10. Nếu chữ ký sai thì vẫn có thể ghi tài khoản rác hoặc sửa khóa, ngành của người khác. | CN01; nguyên tắc kiểm tra trước khi ghi | Chuyển "Tạo hoặc cập nhật tài khoản (khóa, ngành)" vào nhánh `[Hợp lệ]`, kèm điều kiện "nếu vào từ ứng dụng vỏ"; hoặc thêm guard cho msg 10: "chữ ký hợp lệ". |
| R-27 | Minor | `tools/gen_component.py` (SHELL → API_AUTH "truyền danh tính"); `demo/2.7.1`; `import/2.5.0…txt` d.18–19 | 2.7.1 vẽ Ứng dụng vỏ phụ thuộc **trực tiếp** API xác thực, nhưng ở 2.5.0 ứng dụng vỏ chỉ chuyển danh tính cho Khung chat (msg 7), rồi Khung chat mới gọi API xác thực (msg 8). Hai mục mô tả hai đường gọi khác nhau. | Thống nhất 2.5 – 2.7.1 | Chọn một cách: bỏ phụ thuộc SHELL → API_AUTH và đổi nhãn SHELL → UI thành "nhúng, truyền danh tính"; hoặc sửa 2.5.0 cho ứng dụng vỏ gọi API xác thực lấy phiên rồi mở WebView. Sửa xong thì cập nhật số phụ thuộc trong `specs/2.7`. |
| R-28 | Minor | `2.6-csdl.sql` d.137–147; `specs/2.5` d.62 | Khóa đệm **luôn** gồm khóa + ngành, kể cả với câu hỏi không phụ thuộc đối tượng (ví dụ KTX, BHYT, FAQ chung). Đệm bị chia theo từng cặp khóa–ngành nên tỷ lệ trúng giảm mạnh, ảnh hưởng thẳng tới phép đo p50/p95 "có/không có bộ nhớ đệm" ở Bảng 6. | QT4; Bảng 6 dòng cuối | Khi ghi đệm: nếu mọi đoạn nguồn đều áp dụng cho mọi khóa, ngành (`audiences` rỗng) thì lưu `cohort`, `major` = NULL (khóa chung). Khi tra: thử khóa riêng trước, sau đó khóa chung. Nếu giữ nguyên thiết kế thì ghi rõ đánh đổi này ở 2.6 và trong phần thực nghiệm. |
| R-29 | Nit | `specs/2.6-csdl.md` d.28; SQL d.73–82 | Quy tắc so "cùng đối tượng" (CN08) chưa nói chỉ xét các dòng `audiences` cấp tài liệu (`chunk_id IS NULL`). Dòng cấp đoạn có thể bị so nhầm. | CN08 | Thêm "với `chunk_id` rỗng" vào câu ở `specs/2.6` d.28. |
| R-30 | Nit | `demo/2.7.2b` nút (D); `specs/2.7` d.89 | (D) ghi "gắn khóa, năm học, ngày hết hạn" nhưng 2.5.4 msg 17 có thêm **ngành**. Nhãn (D) khớp nguyên văn Hình 1 nên không sai ĐA, chỉ lệch với 2.5.4. | Thống nhất 2.5 – 2.7 | Thêm "ngành" vào (D), hoặc giữ đúng nguyên văn Hình 1 và ghi chú một câu. |
| R-31 | Nit | `demo/2.2.1` (đường Xem phản hồi – Quản trị viên) | Trên ảnh, đường liên kết từ "Xem phản hồi" đi ngang rồi dừng trước hình tác nhân Quản trị viên, trông như không nối vào tác nhân. Model vẫn có đủ 11 association. | Trình bày UML | Kéo lại đầu đường hoặc dời Quản trị viên trên VP trước khi chụp. |

## Tổng hợp vòng 2
- Blocker 0 · Major 0 · Minor 3 (R-26, R-27, R-28) · Nit 3 (R-29, R-30, R-31).
- Các mục chấp nhận lý do nhưng **vẫn phải làm trước khi nộp quyển**: R-17 (thử import tuần tự trên VP), R-18 (viết văn bản 2.2.4, 2.2.5, 2.3, 2.4), R-11 (thêm `ref` trên VP), R-23 (kéo tay đường tự tham chiếu).

## Kết luận: **Đạt**
Không còn Blocker hay Major. Ba finding Minor mới nên sửa trong lần chỉnh tiếp theo, không cần thêm vòng review riêng cho chúng. Riêng R-26 và R-27 rất dễ bị hỏi khi bảo vệ, nên sửa trước khi chụp hình cho quyển.

## Bàn giao cho hội đồng
Những điểm hội đồng nên soi kỹ:
1. **Thứ tự luồng truy vấn so với Hình 1.** Viết lại câu nối tiếp ở bước (2), đứng **trước** kiểm tra phạm vi (3) và tra đệm (4). Hệ quả là khóa đệm dùng câu đã độc lập. Xem `demo/2.7.2a`, `demo/2.5.1`, `demo/2.5.2`.
2. **Khóa bộ nhớ đệm gồm khóa, ngành (QT4)**, cùng đánh đổi với tỷ lệ trúng (R-28). Xem `import/2.6-csdl.sql` bảng `answer_cache`, `specs/2.5` mục "Quyết định thiết kế" ý 2.
3. **Hủy đệm (QT6, CN13)** xảy ra ở ba chỗ: thay phiên bản (2.5.5), xóa mềm (`specs/2.6` mục "Quy tắc dữ liệu") và hết hạn theo `expires_at`. Kiểm `answer_cache_sources` có đủ thông tin để truy ngược tài liệu nguồn.
4. **Từ chối (QT2, QT7, CN14):** ba nguồn từ chối — ngoài phạm vi kể cả dữ liệu cá nhân và giao dịch, không đủ căn cứ, không có trích dẫn hợp lệ sau khi sinh. Cách chọn phòng ban phụ trách. Xem `demo/2.5.3`, `demo/2.5.2` msg 33–34, `knowledge_groups.is_default`.
5. **Đăng nhập qua ứng dụng vỏ (CN01):** việc kiểm tra danh tính chỉ là mô phỏng; thứ tự kiểm tra và ghi tài khoản (R-26); đường gọi khớp giữa 2.5.0 và 2.7.1 (R-27). Xem `demo/2.5.0`, `demo/2.7.1`.
6. **Quan hệ use case:** cách phân biệt include / extend / tổng quát hóa (`specs/2.2` d.8–11). Lý do CN10–CN14 không vẽ thành use case mà truy vết qua `specs/truy-vet.md`.
7. **CSDL:** xóa mềm và FK RESTRICT của `message_sources`; bảng `audiences` cho phép đối tượng ở cả cấp tài liệu lẫn cấp đoạn; cột `embedding` ghi `VECTOR` không kèm số chiều do giới hạn của VP; đường tự tham chiếu `supersedes_id` phải vẽ tay.
8. **Phạm vi ngoài ĐA:** không có tuần tự riêng cho CN03 (xem đoạn gốc) và CN05 (CRUD lịch sử); lý do ghi ở truy-vet.

Các file cần xem:
- `documents/chuong-2/README.md` — danh sách biểu đồ, cách import.
- `documents/chuong-2/specs/2.1-tac-nhan-thuat-ngu.md`, `2.2-usecase.md`, `2.5-tuan-tu.md`, `2.6-csdl.md`, `2.7-kien-truc.md`, `truy-vet.md`.
- `documents/chuong-2/demo/` — 14 ảnh: 2.2.1–2.2.3, 2.5.0–2.5.6, 2.6.2, 2.7.1, 2.7.2a, 2.7.2b.
- `documents/chuong-2/import/2.6-csdl.sql` — lược đồ chuẩn kèm chú thích từng cột.
- Đối chiếu: `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md` (Bảng 2–5, mục 3.3, Hình 1) và `documents/chuong-2/imgs/hình 1.png`.

---

## Phản hồi của agent dev — sau review vòng 2 (2026-11-17)
| Mã | Đã sửa | File |
|---|---|---|
| R-26 | Bỏ "Tạo hoặc cập nhật tài khoản" khỏi nhánh ứng dụng vỏ; nhánh [Hợp lệ] gộp thành "Tạo hoặc cập nhật tài khoản (khi vào từ ứng dụng vỏ), lưu lần đăng nhập gần nhất". 2.5.0 còn 18 message | `sequence_specs.py`, specs/2.5 |
| R-27 | Bỏ phụ thuộc Ứng dụng vỏ → API xác thực; nhãn Ứng dụng vỏ → Khung chat là "nhúng, truyền danh tính" (khớp 2.5.0). Nhãn phụ thuộc căn giữa. 2.7.1 còn 23 phụ thuộc | `gen_component.py`, specs/2.7 |
| R-28 | Khóa riêng (câu hỏi + khóa + ngành) khi nguồn phụ thuộc đối tượng, khóa chung (cohort/major rỗng) khi không; tra riêng trước, chung sau. Sửa message tra/ghi đệm 2.5.1–2.5.3, comment SQL, specs/2.5, 2.6, truy-vet | nhiều file |
| R-29 | Specs 2.6: so "cùng đối tượng" chỉ xét `audiences` cấp tài liệu (`chunk_id IS NULL`) | specs/2.6 |
| R-30 | Nút (D) 2.7.2b thêm "ngành" | `activity_specs.py` |
| R-31 | Dời Quản trị viên (y=370) để các đường tới Xem phản hồi, Đăng nhập chạm tác nhân | `usecase_specs.py` |

Ảnh sinh lại và đã xem toàn bộ: 2.2.1, 2.5.0, 2.6.2, 2.7.1, 2.7.2b. 2.5.1–2.5.3 chỉ đổi chữ của message tra/ghi đệm, đã render lại và kiểm cú pháp PlantUML (`-checkonly`) đạt.


---

## Review vòng 3 — Tech lead (GVHD) xác nhận sửa QA (2026-11-17)

- Căn cứ: ĐA dòng 1–167 (Bảng 1–7, QT1–QT7, mục 5 "Mốc so sánh", "Đánh giá"), `imgs/hình 1.png`. Không chất vấn lại các lựa chọn user đã chốt (QA-1 vẫn stream + thay câu trả lời đã hiển thị; QA-2 cột `chunk_strategy`/offset + "cấu hình thực nghiệm" ở 2.7; QA-3 bỏ khóa chung, 7 ngày, hủy theo nhóm). Chỉ kiểm cách thể hiện.
- Đã xem **toàn bộ** từng ảnh: `demo/2.5.2`, `2.5.4`, `2.5.5`, `2.5.6a`, `2.5.6b`, `2.2.2`, `2.6.2-erd`, `2.7.1`, `2.7.2a`, `2.7.2b` (phóng to vùng extend của 2.2.2 và nút "Thay câu trả lời" của 2.7.2a). Đã đọc `import/2.6-csdl.sql`, `import/2.6-csdl-chi-muc.sql`, `tools/sequence_specs.py`, `tools/activity_specs.py`, `tools/gen_component.py`, toàn bộ `specs/`, `README.md`. File `2.5.6-tuan-tu-danh-gia-va-xem-phan-hoi.*` là file cũ chờ xóa, không tính.
- **Đếm lại (python trên `sequence_specs.py` + grep `->` trên `import/2.5.*.txt`; parse XML, chia đôi vì mỗi phần tử có model + shape):** 2.5.0 18/6 · 2.5.1 16/8 · 2.5.2 40/12 (1 loop, 1 alt) · 2.5.3 26/10 · 2.5.4 27/10 (1 opt, 1 note) · 2.5.5 21/7 (1 alt, 2 note) · 2.5.6a 14/5 (1 opt, 1 alt) · 2.5.6b 10/5 (1 note). 2.2.2: 15 UC, 6 association, 1 include, 7 extend, 4 tổng quát hóa. 2.7.1: 18 thành phần, 25 phụ thuộc, 5 gói. 2.7.2a: 17 nút / 20 luồng. 2.7.2b: 13 nút / 14 luồng. SQL: 12 bảng, 15 FK, 12 CHECK. **Tất cả khớp** `specs/` và phản hồi của dev.

### Trạng thái QA-1 … QA-10

| Mã | Trạng thái | Nhận xét |
|---|---|---|
| QA-1 | Đã sửa | 2.5.2 msg 29–40: gắn trích dẫn, kiểm tra QT1, `alt` thay câu trả lời đã hiển thị + `no_context` + không lưu đệm; 2.7.2a có ◇ "Có trích dẫn hợp lệ? (bổ sung so với Hình 1)". Đúng phương án user chốt. Còn 2 điểm thể hiện: R-37 (thứ tự ở 2.7.2a), R-39 (nguồn phòng ban). |
| QA-2 | Đã sửa | `chunks.chunk_strategy` (CHECK), `start_offset`, `end_offset` (CHECK), UQ(`document_id`, `chunk_strategy`, `chunk_index`); 2.5.4 msg 17; `specs/2.7` d.20–23; `specs/2.6` d.30. Còn hở ở cách lấy dữ liệu đo: R-32, R-33, R-40. |
| QA-3 | Đã sửa | (a) bỏ khóa chung, `cohort`/`major` NOT NULL; (b) SV chưa có khóa/ngành bỏ qua đệm (msg 11, msg 40 của 2.5.2); (c) `expires_at` NOT NULL + CHECK, 2.5.4 msg 24–25 và 2.5.5 msg 18 hủy theo nhóm, 2.7.2b thêm hành động. Còn một lỗi biên ngày: R-34. |
| QA-4 | Đã sửa | `gen_component.py` có `API_CHAT→API_AUTH`, `API_ADM→API_AUTH`; ảnh 2.7.1 thấy rõ hai đường; 25 phụ thuộc khớp `specs/2.7` d.4. |
| QA-5 | Đã sửa | 2.5.2 msg 23, 24, 30 đủ ngày ban hành / năm học / đơn vị xử lý; `documents.is_official` + msg 17 + 2.5.4 msg 1. Thiếu nhỏ ở 2.5.5: R-46. |
| QA-6 | Đã sửa | `2.6-csdl-chi-muc.sql` có HNSW, FK index, chỉ mục bộ phận, CN09, `answer_cache(expires_at)`; bảng 2.6.3. Lỗi thứ tự chạy: R-35; chỉ mục thừa/thiếu: R-45. |
| QA-7 | Đã sửa | 12 CHECK, `UNIQUE(supersedes_id)`, FK ghép `(chunk_id, document_id)` đúng cú pháp (MATCH SIMPLE bỏ qua dòng `chunk_id` rỗng, đúng ý), UQ vị trí đoạn, DEFAULT. Hệ quả mới của UNIQUE: R-36; chữ "đúng một": R-44. |
| QA-8 | Đã sửa | 2.5.5 msg 11 lưu bản mới trước msg 14 lưu đoạn; msg 12 ghi bất đồng bộ; note "bản cũ vẫn phục vụ"; note giao dịch bao msg 16–18. |
| QA-9 | Đã sửa | 2.5.6a có kiểm tra phiên, đọc chủ hội thoại, self-message kiểm tra quyền, `alt` báo lỗi; 2.5.6b có kiểm tra phiên quản trị. Lifeline khớp 2.7.1. |
| QA-10 | Đã sửa (mô hình); trình bày còn lỗi | 2.2.2 có đủ 2 extend mới (7 extend). Nhưng hai đường extend **vẫn cắt nhau** và nhãn bị đặt sát nhau: R-38. |

### Finding mới

| Mã | Mức độ | File:dòng | Vấn đề | Căn cứ ĐA | Đề xuất |
|---|---|---|---|---|---|
| R-32 | Minor | `specs/2.7-kien-truc.md` d.23; `tools/sequence_specs.py` d.137–138 (2.5.2 msg 36–37) | Script đánh giá "chạy bộ câu hỏi qua API … tính Recall@k, MRR bằng cách so `start_offset/end_offset`". Nhưng API hỏi đáp (2.5.2) chỉ trả nguồn **đã trích dẫn** (văn bản, ngày ban hành, Điều/Khoản), không trả **danh sách k đoạn có thứ hạng** kèm mã đoạn. Không có k đoạn xếp hạng thì không tính được Recall@k, Precision@k, MRR. Khi bật đệm và trúng đệm thì cũng không có bước truy xuất. | Bảng 7 (k = số đoạn đưa vào LLM; đoạn liên quan = đoạn chứa phần văn bản gán nhãn); mục 5 "Đánh giá" | Thêm một câu ở `specs/2.7` d.23: script gọi trực tiếp Bộ chuẩn hóa → Bộ truy xuất lai → Bộ xếp hạng lại (cùng mã, cùng CSDL) để lấy k mã đoạn theo thứ tự cho 3 chỉ số truy xuất; chỉ đi qua API cho Faithfulness, Answer relevancy, p50/p95, TTFT. Hoặc ghi API trả thêm danh sách k mã đoạn khi chạy ở chế độ thực nghiệm. Không cần thêm bảng. |
| R-33 | Minor | `tools/sequence_specs.py` d.187–206 (2.5.4 msg 8, 12, 15, 23); `import/2.6-csdl.sql` d.53, d.214 | `start_offset/end_offset` tính trên `documents.extracted_text`. Nhưng ở 2.5.4 nội dung trích xuất chỉ được lưu **trong `opt` bản scan** (msg 12). Tài liệu PDF/DOCX thường không có message nào lưu `extracted_text`. Với bản scan, nội dung **đã sửa** (msg 15) cũng không được lưu lại trước khi chia đoạn, nên offset có thể lệch với văn bản trong CSDL. Người gán nhãn span không có văn bản chuẩn để đối chiếu. | Mục 5 "Đánh giá" (gán nhãn phần văn bản gốc, dùng được với mọi cách chia đoạn); CN10 | Đưa "Lưu nội dung trích xuất" ra ngoài `opt` (mọi tài liệu; bản scan thì kèm trạng thái chờ kiểm tra). Sau msg 15 thêm "Lưu nội dung đã kiểm tra", hoặc đổi msg 23 thành "Lưu nội dung trích xuất cuối cùng, cập nhật trạng thái: đang hiệu lực". Ghi ở `specs/2.6`: offset luôn tính trên bản `extracted_text` đã lưu. |
| R-34 | Minor | `import/2.6-csdl.sql` d.162–164, d.242, d.207; `specs/2.6-csdl.md` d.28 | `expires_at = min(created_at + 7 ngày, ngày hết hạn sớm nhất)`. `expiry_date` là DATE, và tài liệu vẫn dùng được **trong** ngày hết hạn (d.207 "quá ngày thì không truy xuất"). Nếu đổi DATE sang thời điểm 00:00 thì câu trả lời ghi vào đệm đúng ngày hết hạn có `expires_at < created_at`, vi phạm `ck_answer_cache_expiry` và lệnh ghi đệm lỗi; các ngày trước đó thì đệm hết hạn sớm hơn tài liệu một ngày. Ngoài ra công thức lấy hạn "của tài liệu", trong khi đoạn có hạn riêng (`chunks.expiry_date`). | QT3, QT6; CN13 "hết hạn theo tài liệu nguồn" | Ghi rõ: hạn của nguồn = 00:00 **ngày sau** `chunks.expiry_date` (giờ Việt Nam), `expires_at = min(created_at + 7 ngày, hạn sớm nhất của các đoạn nguồn)`. Sửa comment d.242 và `specs/2.6` d.28. |
| R-35 | Minor | `import/2.6-csdl.sql` d.5, d.77; `import/2.6-csdl-chi-muc.sql` d.1–4 | `CREATE EXTENSION vector` nằm ở file chỉ mục, nhưng hướng dẫn bảo chạy file chỉ mục **sau** `2.6-csdl.sql`. Trên CSDL mới, `CREATE TABLE chunks (… embedding VECTOR …)` lỗi "type vector does not exist", nên lược đồ không tạo được theo đúng thứ tự đã ghi. | Yêu cầu SQL PostgreSQL hợp lệ; ĐA Công nghệ (PostgreSQL + pgvector) | Ghi thứ tự 3 bước ở d.5 và `specs/2.6` d.4: (1) `CREATE EXTENSION IF NOT EXISTS vector;` (2) `2.6-csdl.sql` (3) phần còn lại của file chỉ mục. Có thể để dòng extension ở đầu `2.6-csdl.sql` nếu thử Reverse DDL trên VP vẫn qua. |
| R-36 | Minor | `import/2.6-csdl.sql` d.58, d.208; `tools/sequence_specs.py` d.230 (2.5.5 msg 11) | QA-8 cho lưu bản mới **ngay** khi gửi (`supersedes_id` = bản cũ, `processing`). Cùng lúc QA-7 thêm `UNIQUE(supersedes_id)`. Nếu bản mới lỗi trích xuất, bị bỏ ở bước kiểm tra scan, hoặc bị xóa mềm (`deleted`), dòng đó vẫn giữ `supersedes_id`, nên quản trị viên **không thể** tạo bản thay thế khác cho cùng bản cũ. | CN08 | Đổi sang chỉ mục UNIQUE bộ phận trong file chỉ mục: `CREATE UNIQUE INDEX uq_documents_supersedes ON documents (supersedes_id) WHERE supersedes_id IS NOT NULL AND status <> 'deleted';` (bỏ UQ ở bảng). Hoặc ghi quy tắc ở `specs/2.6`: bản mới lỗi thì xóa cứng hoặc đặt `supersedes_id` rỗng. |
| R-37 | Minor | `tools/activity_specs.py` d.26–30, d.47–50; `demo/2.7.2a`; `specs/2.7-kien-truc.md` d.35–36 | Ở 2.7.2a, ◇ "Có trích dẫn hợp lệ?" đứng **trước** (9) "Trả về giao diện theo streaming", và nhánh [không] đi qua (9). Người đọc hiểu là kiểm tra xong mới hiển thị. Nhưng ở 2.5.2 câu trả lời đã hiển thị dần (msg 25–28) **trước** khi kiểm tra (msg 31), và nhánh [không] là thay nội dung đã hiển thị. Hai biểu đồ mô tả hai thứ tự khác nhau, và 2.7.2a che mất đánh đổi user đã chốt. | QT1; Bảng 6 dòng cuối (streaming, TTFT); thống nhất 2.5 – 2.7 | Không đổi luồng. Thêm một câu ở `specs/2.7` d.35 và (nếu VP cho) một note gắn với (8): "(8) và (9) chạy chồng: câu trả lời hiển thị dần trong khi sinh; ◇ trích dẫn xét khi sinh xong; nhánh [không] gửi lệnh thay câu trả lời đã hiển thị (2.5.2 msg 33)". |
| R-38 | Minor | `demo/2.2.2-usecase-sinh-vien.png`; `tools/usecase_specs.py` | Phản hồi của dev nói đã dời UC "để hai đường không cắt nhau". Trên ảnh, đường extend đứng của **Chọn câu hỏi gợi ý → Hỏi đáp** vẫn cắt đường extend ngang **Xem đoạn văn bản gốc → Xem nguồn trích dẫn**. Nhãn `<<extend>>` của đường đứng nằm ngay trên đường ngang, sát nhãn của đường kia, đọc thành "<<extend>> <<extend>>" trên cùng một đường. Mũi tên vào Hỏi đáp còn chồng sát đầu tam giác tổng quát hóa của "Hỏi nối tiếp". | Trình bày UML; nhất quán 2.2.1 – 2.2.2 (QA-10) | Dời "Xem đoạn văn bản gốc" xuống dưới "Xem nguồn trích dẫn" (đường extend đứng), hoặc cho đường của "Chọn câu hỏi gợi ý" vào Hỏi đáp từ phía trái. Nhãn đặt cạnh đúng đường của nó. Sinh lại rồi xem lại **toàn bộ** ảnh. |
| R-39 | Minor | `tools/sequence_specs.py` d.133 (2.5.2 msg 33) so với d.164–165 (2.5.3) | Trả lời điểm cần xác nhận 1. Msg 33 gửi thông báo "kèm phòng ban" nhưng 2.5.2 không có message nào lấy `knowledge_groups.department`. Msg 18/20 chỉ trả "các đoạn", và tên phòng ban không thuộc đoạn. Ở 2.5.3 cùng tình huống (không đủ căn cứ) lại đọc DB theo "đoạn điểm cao nhất / nhóm mặc định". Hai kịch bản chọn phòng ban theo hai cách khác nhau. | QT2; thống nhất trong 2.5 | Cách 1 (khuyến nghị): trong `alt` của 2.5.2 thêm `API→DB` "Lấy phòng ban theo nhóm tri thức của đoạn điểm cao nhất" và trả về, giống hệt 2.5.3 (+2 message, cập nhật số đếm). Cách 2: ghi rõ msg 18 trả "các đoạn ứng viên kèm thông tin tài liệu, nhóm tri thức, phòng ban", và sửa 2.5.3 dùng cùng nguồn. Không chấp nhận để ngầm như hiện tại. |
| R-40 | Minor | `specs/2.7-kien-truc.md` d.21–23; `import/2.6-csdl.sql` d.152–166 | Cờ "bộ nhớ đệm" là một cờ của cấu hình thực nghiệm, nhưng `answer_cache` không ghi cấu hình đã sinh ra câu trả lời. Đổi cấu hình (ví dụ `fixed` → `legal`) mà không xóa đệm thì câu trả lời cũ vẫn được trả, làm sai Faithfulness, độ liên quan và p50/p95 của cấu hình sau. | Mục 5 "mỗi cải tiến bật/tắt độc lập"; Bảng 6 dòng cuối, Bảng 7 | Thêm một câu: mỗi lần đổi cấu hình thực nghiệm thì xóa toàn bộ `answer_cache`. Phép đo "có/không có bộ nhớ đệm" chạy trên cấu hình đầy đủ, hai lượt: lượt lạnh (đệm rỗng) rồi lượt nóng. Tách nhóm bằng `messages.from_cache`. |
| R-41 | Nit | `specs/2.5-tuan-tu.md` d.26–28 | Mục "Quyết định thiết kế" đánh số 5, 7, 6. | — | Đánh lại 5, 6, 7. |
| R-42 | Nit | `tools/sequence_specs.py` d.1 | Docstring còn "Nội dung 7 biểu đồ tuần tự", nay là 8. | — | Sửa thành 8. |
| R-43 | Nit | `README.md` d.25–26 | Chuỗi `` `\n` `` trong câu "Cú pháp cơ bản (participant, message, … trong tên)" bị ghi thành xuống dòng thật, vỡ code span và câu bị cắt đôi. | — | Ghi lại thành `` `\n` `` trên một dòng. |
| R-44 | Nit | `import/2.6-csdl-chi-muc.sql` d.9–10; `specs/2.6-csdl.md` d.33 | Comment ghi "Đúng một nhóm tri thức mặc định", nhưng chỉ mục UNIQUE bộ phận chỉ bảo đảm **tối đa một**. Không có nhóm mặc định thì 2.5.3 không có phòng ban dự phòng. | QT2 | Sửa thành "tối đa một"; ghi quy tắc dữ liệu khởi tạo luôn có một nhóm mặc định. |
| R-45 | Nit | `import/2.6-csdl-chi-muc.sql` d.20, d.42 | (1) `ix_documents_supersedes` thừa vì `uq_documents_supersedes` đã tạo chỉ mục. (2) Hủy đệm theo nhóm join tới `documents.group_id`, nhưng chỉ có chỉ mục bộ phận `WHERE status = 'active'`. Ở 2.5.5, bản cũ đã chuyển `superseded` (msg 17) trước khi hủy đệm (msg 18), nên dòng đó không nằm trong chỉ mục. | QA-6 | Bỏ (1) (hoặc giữ nếu áp dụng R-36). Thêm B-tree đầy đủ `documents(group_id)`, hoặc ghi rõ bước hủy đệm chạy trước bước đổi trạng thái. |
| R-46 | Nit | `tools/sequence_specs.py` d.219 (2.5.5 msg 2) | 2.5.4 msg 1 nhập "có phải văn bản chính thức" (`is_official`), còn 2.5.5 msg 2 không nhập. Văn bản mới có thể khác tính chất bản cũ. | Bảng 3 "ưu tiên nguồn chính thức"; QA-5 | Thêm "(có phải văn bản chính thức)" vào msg 2, hoặc ghi "kế thừa từ bản cũ". |
| R-47 | Nit | `tools/sequence_specs.py` d.206–208 (2.5.4 msg 23–25) | Ở 2.5.4, chuyển "đang hiệu lực" (msg 23) và hủy đệm (msg 24) không nằm trong một giao dịch như 2.5.5. Giữa hai bước, đệm cũ vẫn có thể được trả dù đã có văn bản mới. | QT6; thống nhất 2.5.4 – 2.5.5 | Thêm note "msg 23–24 trong một giao dịch", hoặc hủy đệm trước rồi mới đổi trạng thái. |

### Trả lời "Điểm cần tech lead xác nhận"
1. **2.5.2 msg 33 "kèm phòng ban" không có message đọc phòng ban:** chưa chấp nhận như hiện tại. Thông tin nhóm tri thức có thể đi cùng các đoạn, nhưng tên phòng ban và liên hệ nằm ở `knowledge_groups`. 2.5.3 lại đọc DB cho cùng tình huống. Sửa theo R-39, ưu tiên cách 1 để hai kịch bản chọn phòng ban giống nhau.
2. **Hủy đệm theo nhóm khi nạp mới:** chấp nhận. Đây là lựa chọn user đã chốt, an toàn cho QT1/QT4, cái giá là tỷ lệ trúng đệm giảm sau mỗi lần nạp. Cần ghi đánh đổi này một câu ở `specs/2.6` d.29. Cũng cần nói rõ là không bao phủ trường hợp văn bản mới thuộc nhóm **khác** nhưng vẫn liên quan (ví dụ FAQ học phí nằm ở nhóm FAQ). Trường hợp này được TTL 7 ngày giới hạn. Khi thực nghiệm p50/p95 không được nạp tài liệu giữa các lượt đo (gắn với R-40).

### Tổng hợp vòng 3
- QA-1 … QA-10: **10/10 đã sửa**. QA-10 đúng ở mô hình, còn lỗi trình bày R-38.
- Finding mới: Blocker 0 · Major 0 · Minor 9 (R-32 … R-40) · Nit 7 (R-41 … R-47).
- Tồn đọng từ trước, vẫn phải làm trước khi nộp quyển: R-17 (thử import tuần tự trên VP, nay thêm 2.5.6a/2.5.6b), R-11 (khung `ref` ở 2.5.5 msg 12), R-23 (đường tự tham chiếu `supersedes_id`), R-18 (văn bản 2.2.4, 2.2.5, 2.3, 2.4). Xóa các file `2.5.6-tuan-tu-danh-gia-va-xem-phan-hoi.*` khi user cho phép.

### Kết luận: **Đạt**
Không còn Blocker hay Major. Nên sửa các Minor trước khi chụp hình cho quyển, không cần thêm vòng review riêng. Ưu tiên: R-32, R-33 (để phép đo trọng tâm Bảng 7 làm được thật), R-39 (QT2), R-35 (DDL chạy được). R-38 phải sửa trước khi chụp 2.2.2.

### Bàn giao cho hội đồng chấm lại
Những điểm nên soi:
1. **QA-1, kiểm soát sau sinh:** `demo/2.5.2` msg 25–40 (stream rồi mới kiểm tra, `alt` thay câu trả lời đã hiển thị). Đối chiếu `demo/2.7.2a` ◇ sau (8) và câu giải thích thứ tự (R-37). Câu hỏi nên đặt: sinh viên đã đọc phần chưa có căn cứ thì xử lý thế nào (đã được user chốt là chấp nhận).
2. **QA-2, đo Recall@k theo span:** `import/2.6-csdl.sql` bảng `chunks` (`chunk_strategy`, `start_offset`, `end_offset`); `specs/2.7` mục "Cấu hình thực nghiệm". Kiểm script lấy k đoạn xếp hạng ở đâu (R-32), `extracted_text` có được lưu cho mọi tài liệu không (R-33), đổi cấu hình có xóa đệm không (R-40).
3. **QA-3, bộ nhớ đệm:** `answer_cache` (`cohort`/`major` NOT NULL, `expires_at` NOT NULL + CHECK), 2.5.1–2.5.3 msg tra đệm "bỏ qua nếu chưa có khóa, ngành", 2.5.4 msg 24, 2.5.5 msg 18, 2.7.2b nhánh [không]. Soi biên ngày hết hạn (R-34) và đánh đổi hủy theo nhóm (mục trả lời 2 ở trên).
4. **QA-6, QA-7, SQL vật lý:** thứ tự chạy extension (R-35), FK ghép `audiences`, `UNIQUE(supersedes_id)` khi bản mới lỗi (R-36), chỉ mục bộ phận nhóm mặc định (R-44).
5. **QA-8, phiên bản:** `demo/2.5.5` msg 11 → 14, note bất đồng bộ, giao dịch kích hoạt msg 16–18.
6. **QA-9, QA-10:** `demo/2.5.6a` (chống đánh giá hộ), `demo/2.5.6b`; `demo/2.2.2` hai extend mới và chỗ cắt nhau (R-38).
7. **QA-4, QA-5:** `demo/2.7.1` hai phụ thuộc kiểm tra phiên; 2.5.2 msg 23, 24, 30 và `documents.is_official`.

File cần xem: `documents/chuong-2/demo/` (15 ảnh hiện hành), `import/2.6-csdl.sql`, `import/2.6-csdl-chi-muc.sql`, `import/2.5.*.txt`, `tools/sequence_specs.py`, `tools/activity_specs.py`, `specs/2.5`, `specs/2.6`, `specs/2.7`, `specs/truy-vet.md`, `README.md`.


## Phản hồi của agent dev — sau review vòng 3 (R-32 … R-47)

Tất cả là Minor/Nit, nằm trong plan đã duyệt nên sửa luôn. Đã sinh lại 2.5.2, 2.5.4, 2.5.5, 2.2.2, ERD và xem lại **toàn bộ** từng ảnh.

| Mã | Cách sửa |
|---|---|
| R-32 | `specs/2.7` mục "Cấu hình thực nghiệm": 3 chỉ số truy xuất do script gọi thẳng Bộ chuẩn hóa → Bộ truy xuất lai → Bộ xếp hạng lại lấy k mã đoạn theo thứ tự; chỉ Faithfulness, Answer relevancy, p50/p95, TTFT đi qua API. |
| R-33 | 2.5.4: msg 12 "Lưu nội dung trích xuất (bản scan: chờ kiểm tra)" đưa ra **ngoài** `opt`; trong `opt` thêm msg 16 "Lưu nội dung đã kiểm tra (vị trí đoạn tính trên bản này)". `specs/2.6`: offset luôn tính trên bản `extracted_text` đã lưu. |
| R-34 | `expires_at` = min(`created_at` + 7 ngày, 00:00 **ngày sau** `chunks.expiry_date` sớm nhất của các đoạn nguồn, giờ Việt Nam). Sửa comment SQL và `specs/2.6`. |
| R-35 | Ghi thứ tự 3 bước ở đầu `2.6-csdl.sql`, đầu `2.6-csdl-chi-muc.sql`, `specs/2.6`: (1) `CREATE EXTENSION`, (2) DDL, (3) chỉ mục. Bỏ dòng extension khỏi file chỉ mục. |
| R-36 | Bỏ `UNIQUE(supersedes_id)` ở bảng; thay bằng `CREATE UNIQUE INDEX uq_documents_supersedes … WHERE supersedes_id IS NOT NULL AND status <> 'deleted'`. Quy tắc ở `specs/2.6`: bản mới lỗi thì xóa mềm, tạo bản thay khác. |
| R-37 | `specs/2.7` mục 2.7.2a bước 7: (8) và (9) chạy chồng; ◇ xét khi sinh xong; nhánh [không] thay câu trả lời đã hiển thị. Không đổi luồng. |
| R-38 | 2.2.2 đổi chỗ: Xem nguồn trích dẫn sang phải (x=335), Chọn câu hỏi gợi ý sang trái (x=185). Hai đường extend vào Hỏi đáp không còn cắt đường extend Xem đoạn văn bản gốc. Còn một chỗ đường liên kết Sinh viên – Xem nguồn trích dẫn cắt đường extend của Chọn câu hỏi gợi ý; chấp nhận vì không gây hiểu sai. |
| R-39 | Cách 1: trong `alt` của 2.5.2 thêm msg 33–34 "Lấy phòng ban theo nhóm tri thức của đoạn điểm cao nhất" / "Tên phòng ban, thông tin liên hệ", giống 2.5.3. 2.5.2 nay 42 message. |
| R-40 | `specs/2.7`: đổi cấu hình thực nghiệm thì xóa toàn bộ `answer_cache`; đo có/không đệm trên cấu hình đầy đủ, lượt lạnh rồi lượt nóng; không nạp tài liệu giữa các lượt đo. |
| R-41 | Đánh lại 5, 6, 7 ở `specs/2.5`. |
| R-42 | Docstring "8 biểu đồ". |
| R-43 | `README.md` ghi lại `` `\n` `` trên một dòng. |
| R-44 | "Tối đa một" + quy tắc dữ liệu khởi tạo luôn có một nhóm mặc định (file chỉ mục, `specs/2.6`). |
| R-45 | Bỏ `ix_documents_supersedes` (đã có UNIQUE bộ phận). Thay chỉ mục bộ phận bằng `documents(group_id, status)` đầy đủ, dùng cả khi hủy đệm theo nhóm. |
| R-46 | 2.5.5 msg 2 thêm "(có phải văn bản chính thức)". |
| R-47 | 2.5.4 thêm note "Cập nhật trạng thái và hủy bộ nhớ đệm trong một giao dịch". |
| Trả lời 2 | `specs/2.6` thêm câu đánh đổi của hủy đệm theo nhóm và trường hợp văn bản liên quan thuộc nhóm khác (giới hạn bởi hạn 7 ngày). |

Số đếm sau sửa (grep): 2.5.2 42/12 (1 loop, 1 alt) · 2.5.4 28/10 (1 opt, 2 note) · 2.5.5 21/7. ERD 12 bảng, 15 FK, 12 CHECK. `specs/2.5`, `chuan-bi-bao-ve.md` đã cập nhật số msg.


---

## Review vòng 4 — Tech lead (GVHD) (2026-11-17)

- Căn cứ: ĐA dòng 1–167, `imgs/hình 1.png`. User đã chốt QA-11 dùng `knowledge_groups.cache_epoch`, QA-14 dùng định nghĩa "đoạn chứa trọn span; span cắt qua nhiều đoạn thì tính đoạn phủ phần lớn nhất". Không chất vấn lại hai lựa chọn này, chỉ kiểm cách thể hiện.
- Đã xem **toàn bộ** từng ảnh: `demo/2.5.2` (4377 px, đủ 12 lifeline, CSDL ở mép phải không bị cắt), `2.5.4`, `2.5.5`, `2.2.2` (phóng to vùng extend), `2.7.2b`, `2.6.2-erd`. Đã đọc `import/2.6-csdl.sql`, `import/2.6-csdl-chi-muc.sql`, `tools/sequence_specs.py`, toàn bộ `specs/`, `README.md`, `chuan-bi-bao-ve.md`.
- **Đếm lại** bằng python trên `sequence_specs.py`, grep `->` trên `import/2.5.*.txt` và parse XML (chia đôi vì mỗi phần tử có model + shape):
  - Tuần tự (message/lifeline): 2.5.0 18/6 · 2.5.1 16/8 · 2.5.2 42/12 (1 loop, 1 alt) · 2.5.3 26/10 · 2.5.4 28/10 (1 opt, 2 note) · 2.5.5 22/7 (1 alt, 2 note) · 2.5.6a 14/5 · 2.5.6b 10/5.
  - 2.2.2: 15 UC, 6 association, 1 include, 7 extend, 4 tổng quát hóa. 2.7.2b: 13 nút / 14 luồng.
  - SQL/ERD: 12 bảng, 15 FK, 12 CHECK; `cache_epoch` có trong ERD.
  - **Tất cả khớp** `specs/2.5` d.33–40, `specs/2.6`, `specs/2.7`. Phản hồi dev sau vòng 3 ghi 2.5.5 "21/7", đó là số trước QA-13; số hiện hành 22 đã đúng trong spec.
- **Số msg trong `chuan-bi-bao-ve.md`:** đã đối chiếu từng chỗ với ảnh hiện tại, **tất cả đúng**. Gồm: 2.5.2 msg 5–9, 11, 13, 17, 21–22, 24, 25–30, 31–37, 35, 37, 42; 2.5.0 msg 7–9, 12, 14–18; 2.5.1 msg 5–8, 14; 2.5.3 msg 21; 2.5.4 msg 1, 10, 12–16, 18, 24, 25, 27, 28; 2.5.5 msg 8, 17.

### Trạng thái R-32 … R-47

| Mã | Trạng thái | Kiểm ở đâu |
|---|---|---|
| R-32 | Đã sửa | `specs/2.7` d.24–25: 3 chỉ số truy xuất gọi thẳng thành phần, lấy k mã đoạn theo thứ tự; chỉ số câu trả lời đi qua API. |
| R-33 | Đã sửa | 2.5.4 msg 12 nằm ngoài `opt` (mọi tài liệu); msg 16 "Lưu nội dung đã kiểm tra (vị trí đoạn tính trên bản này)"; `specs/2.6` d.31. |
| R-34 | Đã sửa | SQL d.244, `specs/2.6` d.28: 00:00 ngày sau `chunks.expiry_date` sớm nhất, giờ Việt Nam. CHECK luôn thỏa. |
| R-35 | Đã sửa | Thứ tự 3 bước ghi ở SQL d.5–6, file chỉ mục d.2, `specs/2.6` d.4. |
| R-36 | Đã sửa | File chỉ mục d.42–43: UNIQUE bộ phận `WHERE supersedes_id IS NOT NULL AND status <> 'deleted'`, cú pháp hợp lệ (vị từ bất biến). Quy tắc ở `specs/2.6` d.35. |
| R-37 | Đã sửa | `specs/2.7` d.39 giải thích (8) và (9) chạy chồng. |
| R-38 | Đã sửa một phần | Thay bằng QA-16; còn lỗi nhãn nhỏ ở R-51. |
| R-39 | Đã sửa | 2.5.2 msg 33–34 lấy phòng ban từ DB, giống 2.5.3 msg 21–22. |
| R-40 | Đã sửa | `specs/2.7` d.27: xóa toàn bộ đệm khi đổi cấu hình; lượt lạnh rồi lượt nóng; không nạp giữa các lượt. |
| R-41 | Đã sửa | `specs/2.5` d.26–28 đánh số 5, 6, 7. |
| R-42 | Đã sửa | Docstring "8 biểu đồ". |
| R-43 | Đã sửa | `README.md` d.25 một dòng, `` `\n` `` đúng. |
| R-44 | Đã sửa | File chỉ mục d.8, `specs/2.6` d.34: "tối đa một" + dữ liệu khởi tạo. |
| R-45 | Đã sửa | Bỏ `ix_documents_supersedes`; thêm `documents(group_id, status)` (d.19). |
| R-46 | Đã sửa | 2.5.5 msg 2 có "(có phải văn bản chính thức)". |
| R-47 | Đã sửa | 2.5.4 note "Cập nhật trạng thái và hủy bộ nhớ đệm trong một giao dịch" bao msg 24–26. |

### Trạng thái QA-11 … QA-16

| Mã | Trạng thái | Nhận xét |
|---|---|---|
| QA-11 | Đã sửa (ý tưởng); còn hở khi chạy đồng thời | Có cột `cache_epoch INTEGER NOT NULL DEFAULT 0` (SQL d.35, d.201, ERD). 2.5.2 msg 18 trả epoch, msg 42 ghi có điều kiện. 2.5.4 msg 25 và 2.5.5 msg 19 tăng epoch. Quy tắc ở `specs/2.6` d.29, `specs/2.5` quyết định 2. Nhưng chưa nêu khóa dòng và thứ tự "tăng epoch trước, xóa sau", và xóa mềm không tăng epoch: R-48. |
| QA-12 | Đã sửa | `specs/2.7` d.21–22: `retrieval_mode = vector \| bm25 \| hybrid`, RAG cơ bản = `vector`; `chuan-bi-bao-ve.md` Q-14 cùng chữ. `truy-vet.md` chưa cập nhật: R-50. |
| QA-13 | Đã sửa | 2.5.5 msg 11 (định dạng, lưu tệp) đứng trước msg 12 (lưu bản mới). Msg 7 trả "bản thay đang xử lý (nếu có)". Guard `alt` gồm cả trường hợp này, khớp UNIQUE bộ phận. Ghi chú: msg 11 là self-message nên không thấy Kho tệp (R-52); `specs/2.5` d.77–80 trình bày lặp (R-49). |
| QA-14 | Đã sửa | `specs/2.6` d.31 đúng chữ ĐA "chứa trọn", có quy tắc span cắt qua nhiều đoạn, áp dụng như nhau cho `fixed`/`legal`. `specs/2.7` d.24 dẫn chiếu đúng. |
| QA-15 | Đã sửa | Ảnh 2.7.2b nút (D) "(và chia cố định cho mốc so sánh)"; `specs/2.7` d.46 cùng chữ. |
| QA-16 | Đã sửa một phần | Hai extend vào Hỏi đáp nay là đường đứng, nhãn của Xem nguồn trích dẫn → Hỏi đáp nằm sát đường. Còn 2 nhãn chạm elip: R-51 (Nit, sửa tay trên VP được). |

### Finding mới

| Mã | Mức độ | File:dòng | Vấn đề | Căn cứ ĐA | Đề xuất |
|---|---|---|---|---|---|
| R-48 | Minor | `specs/2.6-csdl.md` d.27, d.29; `tools/sequence_specs.py` d.144 (2.5.2 msg 42), d.211 (2.5.4 msg 25), d.246 (2.5.5 msg 19); SQL d.201 | (1) **Chưa nêu cơ chế khóa.** Ở mức cô lập mặc định READ COMMITTED của PostgreSQL vẫn lọt được trường hợp sau. Giao dịch ghi đệm đọc epoch, thấy chưa đổi. Giao dịch hủy tăng epoch và xóa đệm, nhưng không thấy dòng đệm chưa commit. Giao dịch hủy commit, rồi giao dịch ghi mới commit. Kết quả là đệm cũ vẫn lọt vào, đúng lỗi QA-11. Muốn chặn thì giao dịch ghi phải `SELECT … FOR SHARE` các dòng `knowledge_groups` (và các dòng `documents` nguồn). Giao dịch hủy phải **tăng epoch trước** (lấy khóa dòng, chờ giao dịch ghi xong) rồi mới xóa. Chữ ở msg 19/25 hiện ghi ngược thứ tự: "Hủy … , tăng số lần hủy". (2) **Xóa mềm** (`specs/2.6` d.27) chỉ xóa đệm theo tài liệu, không tăng epoch, nên lượt hỏi đang chạy vẫn có thể ghi lại đệm từ tài liệu vừa bị xóa. | QT6; CN13 | Thêm 1–2 câu ở `specs/2.6` d.29: "Ghi đệm: trong một giao dịch, khóa chia sẻ (`FOR SHARE`) các dòng nhóm và tài liệu nguồn, kiểm tra `status = active` và epoch, rồi mới ghi. Hủy đệm: tăng `cache_epoch` trước, xóa sau, trong cùng giao dịch." Đảo chữ msg 25 (2.5.4), msg 19 (2.5.5) thành "Tăng số lần hủy đệm của nhóm, hủy câu trả lời đệm …". Thêm vào d.27: xóa mềm cũng tăng epoch của nhóm. Không cần thêm cột hay bảng. |
| R-49 | Nit | `specs/2.5-tuan-tu.md` d.77–80 | d.78 vẫn ghi "`alt` khác đối tượng: báo lỗi". Ngay dưới, d.80 lại nằm **trong** "`alt` cùng đối tượng" mà nói "`alt` thứ nhất báo lỗi khi khác đối tượng hoặc đã có bản thay đang xử lý". Trình bày lặp, sai cấp. | CN08 | Gộp d.80 vào d.78, xóa d.80. |
| R-50 | Nit | `specs/truy-vet.md` d.18 (CN13), d.30 (Bảng 6, Bảng 7), d.31 (QT6) | Truy vết chưa có `knowledge_groups.cache_epoch` (QA-11), `retrieval_mode` (QA-12), định nghĩa đoạn liên quan (QA-14). | Bảng 6, Bảng 7, QT6 | Thêm `cache_epoch` vào d.18, d.31. Thêm `retrieval_mode` và "đoạn chứa trọn span (`specs/2.6`)" vào d.30. |
| R-51 | Nit | `demo/2.2.2-usecase-sinh-vien.png` (vùng x≈320–390 và x≈610–670, y≈237) | Nhãn `<<extend>>` của Chọn câu hỏi gợi ý → Hỏi đáp chạm mép trái elip "Xem nguồn trích dẫn". Nhãn của Xem đoạn văn bản gốc → Xem nguồn trích dẫn đè lên mép trái elip "Xem đoạn văn bản gốc". Phản hồi của dev nói nhãn này "nằm giữa hai elip", nhưng ảnh không đúng như vậy. Không gây hiểu sai quan hệ. | Trình bày UML (QA-16) | Kéo nhãn vào khoảng trống trên VP trước khi chụp hình cho quyển. |
| R-52 | Nit | `tools/sequence_specs.py` d.235 (2.5.5 msg 11) | "Kiểm tra định dạng, lưu tệp gốc vào kho tệp" là self-message của API quản trị. 2.5.5 không có lifeline Kho tệp, trong khi 2.5.4 msg 6–7 và 2.7.1 (API quản trị → Kho tệp) có. Cùng kiểu "tham chiếu 2.5.4" đã chấp nhận ở R-11. | Thống nhất 2.5 – 2.7.1 | Ghi "(như 2.5.4 msg 5–7)" trong nhãn, hoặc thêm lifeline Kho tệp và 2 message. |
| R-53 | Nit | `demo/2.5.2` (4377 × 1555 px) | Ảnh rộng 4377 px. Thu vào khổ A4 dọc (khoảng 16 cm) thì chữ chỉ còn khoảng 2 pt, không đọc được trong quyển. Do nhãn msg 24 và msg 42 quá dài. | Trình bày quyển | Khi vẽ bản chính trên VP thì rút gọn nhãn msg 24, 42 (chi tiết đã có trong `specs/2.5`), hoặc đặt hình trên trang ngang. |

### Tổng hợp vòng 4
- R-32 … R-47: 15 mục đã sửa, R-38 sửa một phần (chuyển thành R-51).
- QA-11 … QA-16: 6/6 đã sửa về nội dung. QA-11 còn hở khi chạy đồng thời (R-48); QA-16 còn lỗi nhãn nhỏ (R-51).
- Finding mới: Blocker 0 · Major 0 · Minor 1 (R-48) · Nit 5 (R-49 … R-53).
- Tồn đọng giữ nguyên: R-17 (thử import tuần tự trên VP, gồm 2.5.6a/2.5.6b), R-11 (`ref`), R-23 (đường tự tham chiếu), R-18 (văn bản 2.2.4, 2.2.5, 2.3, 2.4). Xóa các file `2.5.6-…` cũ khi user cho phép.

### Kết luận: **Đạt**
Không còn Blocker hay Major. R-48 nên sửa trước khi bảo vệ, vì Q về QT6 khi admin cập nhật văn bản là câu hội đồng đã nêu. Chỉ cần thêm 1–2 câu spec và đảo chữ 2 message. Các Nit sửa trước khi chụp hình cho quyển, không cần thêm vòng review.

### Bàn giao cho hội đồng chấm lại
1. **QA-11, epoch đệm:** `import/2.6-csdl.sql` d.35, d.201; `demo/2.5.2` msg 18, 42; `demo/2.5.4` msg 25; `demo/2.5.5` msg 19; `specs/2.6` d.29. Soi cơ chế khóa và thứ tự tăng epoch / xóa (R-48), và trường hợp xóa mềm.
2. **QA-12:** `specs/2.7` d.21–22 có `retrieval_mode` ba giá trị; đối chiếu Bảng 6 dòng 4.
3. **QA-13:** `demo/2.5.5` msg 7, guard `alt`, msg 11 → 12; đối chiếu UNIQUE bộ phận ở `import/2.6-csdl-chi-muc.sql` d.42–43.
4. **QA-14:** `specs/2.6` d.31 (chứa trọn span, đoạn phủ phần lớn nhất); `specs/2.7` d.24.
5. **QA-15, QA-16:** `demo/2.7.2b` nút (D); `demo/2.2.2` vùng extend (R-51).
6. **Số msg trong `chuan-bi-bao-ve.md`:** đã khớp ảnh hiện tại. Nếu sửa R-52 (thêm message ở 2.5.5) thì phải đếm lại 2.5.5 msg 17 ở Q-17.

File cần xem: `documents/chuong-2/demo/` (15 ảnh hiện hành), `import/2.6-csdl.sql`, `import/2.6-csdl-chi-muc.sql`, `import/2.5.*.txt`, `tools/sequence_specs.py`, `specs/2.5`, `specs/2.6`, `specs/2.7`, `specs/truy-vet.md`, `chuan-bi-bao-ve.md`, `README.md`.

## Phản hồi của agent dev — sau review vòng 4 (R-48 … R-53)

| Mã | Cách sửa |
|---|---|
| R-48 | `specs/2.6`: giao dịch ghi đệm khóa `SELECT … FOR SHARE` dòng `knowledge_groups`, `documents` nguồn rồi mới kiểm tra epoch, `status`; giao dịch hủy tăng epoch **trước** rồi mới xóa; mọi đường hủy (nạp mới, cập nhật phiên bản, xóa mềm) đều tăng epoch. Chữ 2.5.4 msg 25, 2.5.5 msg 21: "Tăng số lần hủy đệm của nhóm, rồi hủy …". |
| R-49 | `specs/2.5` mục 2.5.5 viết lại đúng cấp `alt` / `else`, bỏ ý lặp. |
| R-50 | `truy-vet.md`: thêm `cache_epoch` (CN13, QT6), `retrieval_mode` (CN12, Bảng 6), định nghĩa đoạn liên quan (Bảng 7). |
| R-51 | Chuyển vào việc user làm trên VP: kéo hai nhãn `<<extend>>` của 2.2.2 ra khỏi mép elip trước khi chụp hình cho quyển (VP tự đặt nhãn khi import). |
| R-52 | 2.5.5 thêm lifeline Kho tệp tài liệu: msg 11 kiểm định dạng, msg 12–13 lưu tệp gốc / đường dẫn. 2.5.5 nay 24 message, 8 lifeline. |
| R-53 | Ghi vào việc chờ user: khi đưa vào quyển, đặt 2.5.2 trên trang ngang hoặc tách hai hình (bước 1–22, 23–42) trên VP. Không đổi nội dung. |

Số msg activation ở 2.5.5 đổi thành 19–22; `chuan-bi-bao-ve.md` đã cập nhật.


---

## Review vòng 5 — Tech lead (GVHD) kiểm cuối (2026-11-18)

- Đã đọc: "Phản hồi của agent dev — sau review vòng 4" (file này), "Phản hồi của agent dev — sau chấm lại vòng 4" (QA-17) và "QA-18" (`C2_hoi-dong_2026-11-17.md`). Đã đọc `tools/sequence_specs.py`, `specs/2.5`, `specs/2.6`, `specs/truy-vet.md`, `chuan-bi-bao-ve.md`.
- Đã xem **toàn bộ** từng ảnh: `demo/2.5.1` (18 msg), `2.5.2` (46 msg, 12 lifeline, 4377 px, không bị cắt), `2.5.3` (28 msg), `2.5.4` (28 msg), `2.5.5` (24 msg, 8 lifeline, có Kho tệp). Số và chữ trên ảnh khớp `sequence_specs.py`.
- **Đếm lại** bằng grep `->` và đếm `participant`/khối trên `import/2.5.*.txt`:

  | Biểu đồ | Message | Lifeline | Khối |
  |---|---|---|---|
  | 2.5.0 | 18 | 6 | 2 alt, 1 note |
  | 2.5.1 | 18 | 8 | — |
  | 2.5.2 | 46 | 12 | 1 loop, 1 alt |
  | 2.5.3 | 28 | 10 | 1 alt, 1 note |
  | 2.5.4 | 28 | 10 | 1 opt, 2 note |
  | 2.5.5 | 24 | 8 | 1 alt, 2 note |
  | 2.5.6a | 14 | 5 | — |
  | 2.5.6b | 10 | 5 | — |

  Bảng ở `specs/2.5` d.31–40 **khớp hoàn toàn**.
- **File 2.5.6 cũ:** không còn trong `demo/`, `drafts/`, `import/`. Grep toàn thư mục (trừ `issues/`, nơi giữ lịch sử) không còn chỗ nào nhắc `2.5.6` mà không kèm a/b.
- **Số msg trích dẫn:** đã đối chiếu từng chỗ với ảnh hiện tại.
  - `specs/2.5` d.23 (2.5.2 msg 16–17, 46) và `specs/2.6` d.29 (msg 16–17, 46): đúng.
  - `chuan-bi-bao-ve.md`: đúng **tất cả, trừ một chỗ** (R-54). Đã kiểm 2.5.2 msg 5–6, 7–11, 13, 15, 18–21, 25–26, 28, 29–32, 34–35, 35–41, 37, 39, 41, 42–43, 45, 46; 2.5.1 msg 7–10, 16; 2.5.1–2.5.3 msg 8; 2.5.3 msg 23; 2.5.0 msg 7–9, 12, 14–18; 2.5.4 msg 1, 10, 12–16, 18, 24, 27, 28; 2.5.5 msg 8.

### Trạng thái R-48 … R-53

| Mã | Trạng thái | Kiểm ở đâu |
|---|---|---|
| R-48 | Đã sửa | `specs/2.6` d.29–31: đọc epoch **trước khi tìm kiếm**, `FOR SHARE` nhóm rồi tài liệu, giao dịch hủy tăng epoch trước, mọi đường hủy (nạp mới, cập nhật phiên bản, xóa mềm) đều tăng epoch. Chữ message: 2.5.4 msg 24, 2.5.5 msg 19 "Tăng số lần hủy đệm của nhóm, rồi hủy …". |
| R-49 | Đã sửa | `specs/2.5` mục 2.5.5 dùng đúng cấp `alt` / `else`, không còn ý lặp. |
| R-50 | Đã sửa | `truy-vet.md` d.17 (`retrieval_mode`), d.18, d.31 (`cache_epoch`), d.30 (định nghĩa đoạn liên quan). |
| R-51 | Chấp nhận, chuyển user | Kéo nhãn trên VP trước khi chụp hình cho quyển. Không đổi quan hệ. |
| R-52 | Đã sửa | 2.5.5 có lifeline Kho tệp: msg 11 kiểm định dạng, msg 12–13 lưu tệp / đường dẫn, msg 14 lưu bản mới. Khớp 2.5.4 msg 5–8 và 2.7.1. |
| R-53 | Chấp nhận, chuyển user | Đặt 2.5.2 trên trang ngang hoặc tách hai hình trên VP. |

### Trạng thái QA-17, QA-18

| Mã | Trạng thái | Nhận xét |
|---|---|---|
| QA-17 | Đã sửa | (1) 2.5.2 msg 16–17 đọc epoch **trước** tìm kiếm (msg 18–21), msg 22 trả kèm epoch đã đọc, msg 46 ghi có điều kiện. Lập luận đúng: giao dịch nạp tăng epoch và kích hoạt tài liệu trong cùng một giao dịch. Vì vậy, nếu lượt hỏi đọc epoch trước khi giao dịch đó commit thì epoch đổi và không ghi đệm; nếu đọc sau thì tìm kiếm đã thấy văn bản mới. (2) 2.5.4 msg 24 → 26 và 2.5.5 msg 19 → 21–22 hủy đệm trước, đổi trạng thái sau. Note "khóa nhóm trước, tài liệu sau" khớp phía ghi đệm (`specs/2.6` d.30), nên không có khóa chết. Chỉ còn chữ ở `specs/2.5` mục 2.5.4 chưa theo thứ tự mới (R-55). |
| QA-18 | Đã sửa | 2.5.1–2.5.3 msg 2 "Gửi câu hỏi kèm mã hội thoại"; msg 5–6 API đọc lịch sử từ CSDL, hội thoại phải thuộc sinh viên, bỏ lượt bị từ chối. `specs/2.5` quyết định 3, `truy-vet.md` CN02. Lifeline CSDL đã có sẵn ở cả 3 biểu đồ nên số lifeline không đổi. Còn 2 chỗ trình bày nhỏ: R-56, R-57. |

### Finding mới

| Mã | Mức độ | File:dòng | Vấn đề | Căn cứ ĐA | Đề xuất |
|---|---|---|---|---|---|
| R-54 | Nit | `chuan-bi-bao-ve.md` d.55 (Q-4) | "chỉ dùng k đoạn làm dữ liệu (**msg 26**)". Ở ảnh 2.5.2 hiện tại, msg 26 là "Đủ căn cứ"; yêu cầu gửi LLM là **msg 28**. Dòng Dẫn chứng d.56 đã ghi đúng "msg 28". | — | Sửa thành "msg 28". |
| R-55 | Nit | `specs/2.5-tuan-tu.md` d.75–76 | Mục 2.5.4 vẫn viết "(E) … lưu → trạng thái 'đang hiệu lực'" rồi mới "Hủy câu trả lời đệm…". Ảnh 2.5.4 sau QA-17 làm ngược lại: hủy đệm, tăng epoch (msg 24) **trước**, đổi trạng thái (msg 26) sau. Mục này cũng không nhắc tăng `cache_epoch`, trong khi mục 2.5.5 có. | QT6 | Viết lại: "(E) tách từ, tạo vector, lưu đoạn. Kích hoạt trong một giao dịch: tăng `cache_epoch` và hủy đệm cùng nhóm, rồi chuyển 'đang hiệu lực' (khóa nhóm trước, tài liệu sau)." |
| R-56 | Nit | `tools/sequence_specs.py` msg 5 của 2.5.1–2.5.3; `specs/2.5` d.24 (quyết định 3); 2.5.0 msg 18 "Mở hội thoại mới" | (1) Câu đầu tiên của một hội thoại mới chưa có mã hội thoại, và không biểu đồ nào cho thấy dòng `conversations` được tạo ở đâu. (2) Quyết định 3 nói "không thuộc thì báo lỗi", nhưng 2.5.1–2.5.3 không có nhánh này. Chỉ có điều kiện viết trong chữ của msg 5. | CN01 "hội thoại được lưu theo từng sinh viên"; CN05 | Sửa chữ msg 5 thành "Đọc lịch sử hội thoại (hội thoại mới thì tạo; hội thoại phải thuộc sinh viên, không thuộc thì báo lỗi; bỏ các lượt bị từ chối)". Không cần thêm `alt`, giữ nguyên số msg. |
| R-57 | Nit | `tools/activity_specs.py` d.17 (`demo/2.7.2a` nút (1)); `specs/2.7-kien-truc.md` d.33 | Nút (1) vẫn ghi "Sinh viên gửi câu hỏi (kèm lịch sử hội thoại)". Chữ này đúng nguyên văn Hình 1 nên không sai ĐA. Nhưng sau QA-18, client chỉ gửi mã hội thoại, còn lịch sử do máy chủ đọc. Hội đồng đã nêu chính nút này ở QA-18. | Hình 1 bước (1); thống nhất 2.5 – 2.7 | Giữ nhãn theo Hình 1 và thêm một câu ở `specs/2.7` d.33: "lịch sử do API đọc từ CSDL theo mã hội thoại (2.5.1–2.5.3 msg 5–6)". |

### Tổng hợp vòng 5
- R-48 … R-53: 4 mục đã sửa (R-48, R-49, R-50, R-52), 2 mục chấp nhận và chuyển cho user làm trên VP (R-51, R-53).
- QA-17, QA-18: đã sửa.
- Finding mới: Blocker 0 · Major 0 · Minor 0 · Nit 4 (R-54 … R-57). Cả 4 chỉ là sửa chữ, không đổi số msg.
- Số đếm ở `specs/2.5` khớp `import/2.5.*.txt` và ảnh. File 2.5.6 cũ đã xóa sạch.
- Việc của user trước khi nộp quyển: R-17 (thử import tuần tự trên VP), R-11 (`ref`), R-23 (đường tự tham chiếu), R-18 (văn bản 2.2.4, 2.2.5, 2.3, 2.4), R-51, R-53.

### Kết luận: **Đạt**
Bộ thiết kế Chương 2 đạt để chụp hình cho quyển và bảo vệ. Không còn Blocker, Major hay Minor. 4 Nit sửa trong lần chỉnh văn bản tiếp theo, không cần thêm vòng review.

## Phản hồi của agent dev — sau review vòng 5 (R-54 … R-57) và góp ý cuối của hội đồng

- R-54: Q-4 sửa thành "2.5.2 msg 28". R-55: `specs/2.5` mục 2.5.4 tả đúng thứ tự (tăng `cache_epoch`, hủy đệm, rồi kích hoạt; khóa nhóm trước). R-56: nhãn msg 5 ở 2.5.1–2.5.3 "Đọc lịch sử hội thoại (chưa có thì tạo hội thoại mới; không thuộc sinh viên thì báo lỗi; bỏ các lượt bị từ chối)". R-57: `specs/2.7` giải thích nhãn (1) giữ chữ Hình 1.
- Góp ý hội đồng vòng 5: `specs/2.5` quyết định 5 thêm quy tắc lưu sau kiểm (kể cả khi ngắt) và lỗi LLM chỉ lưu thông báo `error`; mục 2.5.2 bước (5) ghi trạng thái tài liệu đọc từ CSDL; mục 2.5.3 ghi quy tắc hai ngưỡng. `chuan-bi-bao-ve.md` sửa Q-3, Q-9, Q-17, Q-18, Q-20, Q-26.
- Đã sinh lại 2.5.1–2.5.3, xem lại toàn bộ ảnh; số message không đổi (18/46/28).


---

## Review vòng 6 — Tech lead (GVHD): bảng cấu hình (2026-11-18)

- Thay đổi user đã chốt (không chất vấn lại): cờ thực nghiệm lưu ở `app_config_overrides`, admin sửa ở màn Cấu hình; mô hình chọn từ `model_profiles`. Hai bảng vào ERD, đứng riêng, không khóa ngoại. Thay đổi này khớp `human-workspace/spec/02-ke-hoach-chuong-2-thiet-ke.md` d.224–225, d.236 và thay quyết định cũ "không vẽ bảng cấu hình".
- Đã đọc: `import/2.6-csdl.sql` d.191–212, d.273–281; `specs/2.6` d.5, d.22–23, d.53, d.61–62; `specs/2.7` d.20–27; `specs/truy-vet.md` d.30; `README.md` d.20, d.51; `chuan-bi-bao-ve.md` Q-14 (d.96–103). Đã xem **toàn bộ** ảnh `demo/2.6.2-erd.png`.
- **Đếm lại.** SQL: `CREATE TABLE` 14, `FOREIGN KEY` 15, `CHECK (` 13. ERD XML (chia đôi model/shape): 14 `DBTable`, 15 `DBForeignKeyConstraint`, 13 `DBCheckConstraint`. Ảnh ERD: 14 bảng, đủ tên, không đè nhau. `app_config_overrides` và `model_profiles` ở cột trái, không có đường nối. Cả hai đều có PK, `model_profiles` có biểu tượng UQ trên `kind`/`name`. **Khớp** `specs/2.6` d.5 (14 bảng), d.53 (thêm `model_profiles.kind` vào danh sách CHECK), `README.md` d.20, d.51.
- **SQL:** kiểu dữ liệu VP đọc được (`VARCHAR`, `TEXT`, `UUID`, `TIMESTAMP WITH TIME ZONE`; JSON ghi `TEXT`, cùng quy ước d.4). PK `key` VARCHAR(100), UQ(`kind`, `name`), `CHECK kind IN ('llm','embedding','reranker')` hợp lệ. Có COMMENT cho từng bảng và cột chính, và key ví dụ nêu đủ cờ của Bảng 6: `NORMALIZATION_ENABLED`, `FOLLOW_UP_REWRITE_ENABLED`, `RETRIEVAL_MODE`, `RERANKER_ENABLED`, `CACHE_ENABLED`, `CHUNK_STRATEGY`.
- **Thống nhất:** `specs/2.7` d.21, `truy-vet.md` d.30, `chuan-bi-bao-ve.md` Q-14 cùng nói cờ lưu ở `app_config_overrides` và mô hình ở `model_profiles`. 2.7.1 đã có API quản trị → CSDL (ghi cấu hình) và API hỏi đáp → CSDL (đọc cấu hình), nên không cần thêm phụ thuộc. Không còn chữ "tệp cấu hình của máy chủ, không lưu CSDL" ở đâu.

### Finding mới

| Mã | Mức độ | File:dòng | Vấn đề | Căn cứ ĐA | Đề xuất |
|---|---|---|---|---|---|
| R-58 | Minor | `specs/2.7-kien-truc.md` d.21–22, d.27; `chuan-bi-bao-ve.md` d.101 (câu nối tiếp Q-14) | Cờ ở `app_config_overrides` là cấu hình **toàn hệ thống**: API hỏi đáp đọc cùng một bộ cờ cho mọi yêu cầu. Khi admin đặt `RETRIEVAL_MODE = vector`, `CHUNK_STRATEGY = fixed` để đo RAG cơ bản, sinh viên thật đang hỏi lúc đó cũng nhận câu trả lời của RAG cơ bản, và hội thoại thật cũng bị lẫn vào số đo p50/p95. Câu nối tiếp ở Q-14 lại khẳng định "hội thoại thật của sinh viên luôn chạy cấu hình đầy đủ", mâu thuẫn với chính thiết kế. | Mục 5 "bật/tắt độc lập trên cùng một kho"; mục 2 (phục vụ sinh viên) | Thêm một câu ở `specs/2.7` d.22: thực nghiệm chạy trên một phiên bản máy chủ riêng, dùng bản sao cùng CSDL (cùng kho, cùng `chunks`), hoặc chạy khi hệ thống không phục vụ. Hệ thống phục vụ sinh viên giữ cấu hình đầy đủ. Sửa câu nối tiếp Q-14 theo đúng câu đó. Không cần thêm bảng hay cột. |
| R-59 | Minor | `specs/2.2-usecase.md` (2.2.3); `specs/truy-vet.md`; `specs/2.7` d.21 | Thiết kế nay có màn **Cấu hình** mà quản trị viên thao tác (sửa cờ, chọn mô hình), nhưng không có use case ở 2.2.3 và không có dòng truy vết. ĐA Bảng 5 không có chức năng này (CN07–CN09). Hội đồng dễ hỏi: "Admin làm được việc này ở UC nào, có phải ngoài phạm vi không?" | ĐA Bảng 2, Bảng 5; mục 5 (thực nghiệm) | Chọn một cách và ghi rõ. (a) Coi đây là công cụ phục vụ thực nghiệm (ĐA mục 5, Bảng 6), không phải chức năng nghiệp vụ, nên không vẽ use case. Ghi một câu ở `specs/2.2` mục Quy ước chung và một dòng "Cấu hình thực nghiệm" ở `truy-vet.md`. (b) Hoặc thêm UC "Quản lý cấu hình thực nghiệm" ở 2.2.3, ghi chú là bổ sung ngoài Bảng 5. Khuyến nghị (a), vì không đổi số đếm use case. |
| R-60 | Nit | `import/2.6-csdl.sql` d.191–197 | `value` và `encrypted_value` cùng cho phép NULL nhưng không ràng buộc nào bảo đảm đúng một trong hai có giá trị. Một dòng có thể rỗng cả hai, hoặc có cả hai. | — | Thêm `CONSTRAINT ck_app_config_value CHECK ((value IS NULL) <> (encrypted_value IS NULL))`. Cập nhật số CHECK thành 14 ở `specs/2.6` và README nếu có ghi. Hoặc ghi quy tắc ở COMMENT. |
| R-61 | Nit | `specs/2.6-csdl.md` d.61–62 | Mục "Đối chiếu baseline" chưa nhắc hai bảng mới. Theo kế hoạch d.224–225, hai bảng này đã có trên baseline (✅ migration `0006`, `0007`), nên nên ghi là có sẵn, không phải 🆕. | — | Thêm "`app_config_overrides` (`0006`), `model_profiles` (`0007`) giữ nguyên từ baseline". |

### Kết luận: **Đạt**
Thay đổi được thể hiện đúng và nhất quán. Số đếm khớp: 14 bảng, 15 FK, 13 CHECK. ERD đủ tên bảng, không đè nhau. Không có Blocker hay Major. Nên sửa R-58 và R-59 trước khi bảo vệ, vì hội đồng sẽ hỏi đúng chỗ này: thực nghiệm có ảnh hưởng sinh viên thật không, và màn Cấu hình thuộc UC nào. Cả hai chỉ cần thêm câu spec, không đổi biểu đồ. R-60, R-61 sửa khi chỉnh văn bản.

## Phản hồi của agent dev — vòng 6 (bảng cấu hình)
| Mã | Xử lý |
|---|---|
| R-58 | Đã sửa. `specs/2.7` mục "Cấu hình thực nghiệm": thực nghiệm chạy trên máy chủ riêng dùng bản sao CSDL; hệ thống phục vụ sinh viên giữ cấu hình đầy đủ. Câu nối tiếp Q-14 trong `chuan-bi-bao-ve.md` sửa theo. |
| R-59 | Đã sửa. `specs/2.2` ghi màn Cấu hình là công cụ thực nghiệm (ĐA mục 5), không vẽ use case; `truy-vet.md` dòng Bảng 6–7 thêm ý này. |
| R-60 | Ghi quy tắc "mỗi khóa chỉ dùng một trong hai cột, API kiểm khi lưu" ở `specs/2.7`; không thêm CHECK để giữ nguyên schema baseline và ảnh ERD (13 CHECK). |
| R-61 | Đã sửa. `specs/2.6` "Đối chiếu baseline" ghi ✅ hai bảng có sẵn (migration `0006`, `0007`). |
Không đổi biểu đồ, không đổi số đếm.
