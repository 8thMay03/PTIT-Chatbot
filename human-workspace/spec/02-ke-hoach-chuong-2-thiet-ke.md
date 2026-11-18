# Kế hoạch chi tiết — Chương 2: Phân tích và thiết kế hệ thống

**Nguyên tắc:**
1. **Bài toán là chuẩn:** mọi nội dung bám theo `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md` (gọi tắt là **ĐA**): tác nhân Bảng 2, miền tri thức Bảng 3, quy tắc QT1–QT7 Bảng 4, chức năng CN01–CN14 Bảng 5, cải tiến Bảng 6, chỉ số Bảng 7, Hình 1.
2. **Baseline code là tham chiếu** (`dev @ 92aa804`, cập nhật 2026-11-09; bản trước dựa trên `main`, đã cũ): phần nào code đã có thì thiết kế mô tả đúng như code; phần nào chưa có thì thiết kế theo bài toán và đánh dấu **[CẦN BỔ SUNG]** để code theo sau.
3. Thiết kế phải **thống nhất** giữa các mục: tên bảng ở 2.6 = tên thực thể trong biểu đồ tuần tự 2.5 = thành phần ở 2.7.

**Ký hiệu trạng thái:** ✅ baseline đã có, mô tả theo code · 🟡 có một phần · ❌ chưa có, thiết kế mới.

**Người viết:** **Ngọc** phụ trách bản thiết kế (Bảng 8 công việc 3); Khánh review và cung cấp nội dung cho phần lõi RAG CN10, CN11, CN12, CN14 (đánh dấu 👤K). CN13 (bộ nhớ đệm) do Ngọc thiết kế.

**Công cụ vẽ đề xuất:** draw.io hoặc StarUML cho use case và tuần tự (UML chuẩn); dbdiagram.io cho lược đồ CSDL; giữ bản nguồn (`.drawio`, `.dbml`) trong repo để sửa lại được.

---

## 2.1. Xác định tác nhân

### 2.1.1. Danh sách và mô tả các tác nhân
- **Nội dung:** bảng tác nhân lấy từ ĐA Bảng 2, mở rộng thêm cột "Cách tương tác với hệ thống".

| Tác nhân | Loại | Mô tả | Tương tác |
|---|---|---|---|
| Sinh viên | Chính | SV đại học chính quy cơ sở miền Bắc | Khung chat web trên điện thoại (trong ứng dụng vỏ) hoặc trình duyệt |
| Quản trị viên | Chính | Cán bộ quản lý nguồn tri thức | Trang quản trị trên máy tính |
| Dịch vụ LLM | Phụ (hệ thống ngoài) | Sinh câu trả lời từ ngữ cảnh | Hệ thống gọi qua API |
| Ứng dụng vỏ (đề xuất) | Phụ | Mô phỏng app di động của trường, truyền danh tính SV | WebView + cầu nối truyền token |

- **Baseline:** 🟡 code đã phân biệt người dùng (cookie `ptit_user`, đăng nhập email), admin (cookie `ptit_admin`, tài khoản từ env) và khách ẩn danh (`ptit_sid`); chưa có mã SV/khóa/ngành. Tác nhân "Ứng dụng vỏ" là **đề xuất**, cần nhóm chốt có đưa vào biểu đồ use case không (ĐA CN01 có nhắc "danh tính do ứng dụng vỏ truyền sang").

### 2.1.2. Bảng thuật ngữ
- **Nội dung:** bảng 3 cột *Thuật ngữ — Viết tắt/tiếng Anh — Giải thích*, sắp xếp theo vần.
- **Danh sách đề xuất:** RAG; LLM; đoạn văn bản (chunk); đoạn cha/đoạn con (parent/child chunk); vector nhúng (embedding); tìm kiếm ngữ nghĩa; BM25; tách từ tiếng Việt; tìm kiếm lai (hybrid retrieval); hợp nhất thứ hạng RRF; xếp hạng lại (reranking); cross-encoder; truy vấn đa hướng (multi-query); viết lại câu hỏi (query rewriting); chuẩn hóa câu không dấu; bộ nhớ đệm (cache); trích dẫn (citation); Điều/Khoản/Điểm; đối tượng áp dụng; phiên bản tài liệu; hiển thị dần (streaming); TTFT; p50/p95; Recall@k; Precision@k; MRR; Faithfulness; Answer relevancy; chèn lệnh (prompt injection); kiểm soát phạm vi (guardrail); ngưỡng tin cậy (confidence gate); OCR; WebView; ứng dụng vỏ; cookie phiên HttpOnly / token ký HMAC; scrypt; dataset (kho tài liệu); search_text; pgvector; HNSW.
- **Nguồn:** ĐA mục 5 + Bảng 7 đã định nghĩa sẵn phần lớn chỉ số → dùng nguyên văn.

---

## 2.2. Yêu cầu chức năng

### 2.2.1. Biểu đồ use case tổng quát
- **Vẽ:** 1 biểu đồ, ranh giới hệ thống "Hệ thống hỏi đáp hỗ trợ sinh viên".
- **Use case (đặt mã UC trùng CN để dễ đối chiếu):**
  - Sinh viên: UC01 Đăng nhập · UC02 Hỏi đáp · UC03 Xem nguồn trích dẫn · UC04 Chọn câu hỏi gợi ý · UC05 Quản lý lịch sử hội thoại · UC06 Đánh giá câu trả lời.
  - Quản trị viên: UC01 Đăng nhập · UC07 Quản lý tài liệu tri thức · UC08 Cập nhật phiên bản tài liệu · UC09 Xem phản hồi.
  - Dịch vụ LLM: liên kết với UC02 (sinh câu trả lời).
- **Quan hệ:** UC02, UC05, UC06 `<<include>>` UC01 (cần đăng nhập); UC03 và UC04 `<<extend>>` UC02; UC08 `<<extend>>` UC07.
- **Lưu ý:** CN10–CN14 là xử lý nội bộ, **không** vẽ thành use case của tác nhân; trình bày ở 2.2.4.

### 2.2.2. Chức năng dành cho sinh viên
- **Nội dung:** với mỗi CN01–CN06: mô tả ngắn, đầu vào/đầu ra, quy tắc liên quan; kèm **biểu đồ use case phân rã** cho UC05 (xem/mở lại/đổi tên/xóa).
- **Đối chiếu baseline:**

| CN | Baseline | Ghi chú cho quyển |
|---|:-:|---|
| CN01 | 🟡 | Mô tả theo code: đăng ký/đăng nhập email + mật khẩu (scrypt), cookie HttpOnly ký HMAC, admin đăng nhập chung `/login`; **[CẦN BỔ SUNG]** mã SV, khóa/ngành, danh tính từ ứng dụng vỏ |
| CN02 | ✅ | Mô tả theo code: NDJSON streaming (`start/step/reasoning/delta/error/done`), hỏi nối tiếp qua lịch sử, nút dừng giữ phần đã sinh |
| CN03 | 🟡 | Có tên văn bản + Điều/Khoản/Điểm, phân biệt nguồn được trích / nguồn liên quan; **[CẦN BỔ SUNG]** đoạn trích + xem đoạn gốc |
| CN04 | 🟡 | Có gợi ý tĩnh; **[CẦN BỔ SUNG]** gợi ý phổ biến từ dữ liệu + câu hỏi liên quan |
| CN05 | ✅ | Có CRUD, lọc theo tài khoản/phiên; đổi sang mã SV khi CN01 hoàn thiện |
| CN06 | ❌ | **[CẦN BỔ SUNG]** |

### 2.2.3. Chức năng dành cho quản trị viên
- **Nội dung:** CN07–CN09 như trên; biểu đồ use case phân rã cho UC07 (tải lên kèm metadata / xem danh sách / xem các đoạn / kiểm tra nội dung trích xuất bản scan / xóa).
- **Đối chiếu baseline:** CN07 🟡 (đã có dataset bật/tắt, upload chạy nền có tiến trình, chọn parser, tách parse/chia đoạn, sửa Markdown, xem file gốc; thiếu ngày ban hành/hết hạn/đối tượng, trạng thái duyệt bản scan) · CN08 ❌ (upload trùng tên chỉ thay file) · CN09 ❌ (chỉ có API admin xem mọi hội thoại).

### 2.2.4. Chức năng xử lý của hệ thống 👤K
- **Nội dung:** CN10–CN14, mỗi CN một đoạn: mục đích, đầu vào/đầu ra, vị trí trong luồng (Hình 1), cải tiến tương ứng trong Bảng 6.
- **Đối chiếu baseline:**

| CN | Baseline | Ghi chú cho quyển |
|---|:-:|---|
| CN10 | 🟡 | Parser text/Docling/LlamaParse, chuẩn hóa heading, giữ bảng; parse và chia đoạn tách bước, admin sửa Markdown ở giữa; **[CẦN BỔ SUNG]** OCR theo từng file + trạng thái chờ duyệt |
| CN11 | 🟡 | Rule viết tắt + follow-up đơn giản; **[CẦN BỔ SUNG]** chuẩn hóa không dấu đặt **trước** kiểm tra phạm vi |
| CN12 | 🟡 | pgvector HNSW + BM25 trên `search_text` + RRF + parent-child, lọc dataset bật; **[CẦN BỔ SUNG]** tách từ tiếng Việt, cross-encoder mặc định, lọc hiệu lực |
| CN13 | ❌ | **[CẦN BỔ SUNG]** — Ngọc thiết kế và viết (bảng cache, tra cache sau `prepare_query()`, hủy theo tài liệu) |
| CN14 | 🟡 | Scope gate + injection + confidence gate đã hiệu chỉnh (bm25_norm, vector, cross-encoder) + nhận diện câu từ chối; **[CẦN BỔ SUNG]** chỉ phòng ban, phân loại trạng thái, sửa lỗi câu không dấu |

### 2.2.5. Quy tắc nghiệp vụ
- **Nội dung:** chép Bảng 4 (QT1–QT7), thêm 2 cột: *Chức năng áp dụng* và *Cách hệ thống đảm bảo*.

| QT | Chức năng áp dụng | Cách hệ thống đảm bảo (thiết kế) |
|---|---|---|
| QT1 | CN02, CN14 | System prompt bắt buộc citation + kiểm tra hậu sinh (không còn citation hợp lệ → từ chối) |
| QT2 | CN14 | Câu từ chối có tên phòng ban theo nhóm tri thức (bảng ánh xạ) |
| QT3 | CN08, CN12 | Lọc `status = active` và `expiry_date` khi truy xuất |
| QT4 | CN07, CN12, CN02 | Metadata đối tượng áp dụng trên đoạn; prompt yêu cầu trình bày theo từng trường hợp |
| QT5 | CN02 | Thêm khuyến cáo theo nhóm tri thức (học phí, hạn nộp, tốt nghiệp) |
| QT6 | CN08, CN13 | Hủy cache theo bảng liên kết cache–tài liệu |
| QT7 | CN14 | Guardrail phạm vi + phát hiện chèn lệnh, chạy sau bước chuẩn hóa |

---

## 2.3. Yêu cầu phi chức năng
Mỗi mục: bảng *Mã — Yêu cầu — Chỉ tiêu đo được — Cách kiểm chứng*. **Các con số dưới đây là đề xuất, nhóm cần chốt** (ĐA chưa nêu con số mục tiêu; số S-Link đang được đo).

### 2.3.1. Hiệu năng
- Thời gian đến token đầu (TTFT) p50 ≤ 2 s; thời gian phản hồi đầy đủ p95 ≤ 8 s (không cache).
- Câu hỏi trúng cache: p95 ≤ 1 s.
- Cross-encoder làm tăng thời gian không quá X ms (đo và ghi lại, ĐA Bảng 6).
- So sánh với thời gian của S-Link trên cùng tập kiểm tra.
- **Baseline:** 🟡 có `elapsed_ms` từng bước trong event `step` và metadata tin nhắn; **[CẦN BỔ SUNG]** `latency_ms`, `ttft_ms`, `from_cache` + script đo p50/p95.

### 2.3.2. Độ tin cậy của câu trả lời
- 100% câu trả lời có nội dung kèm ≥1 trích dẫn hợp lệ (QT1).
- Faithfulness ≥ 0,9; tỷ lệ từ chối đúng ≥ 90% trên nhóm câu kiểm tra biên.
- Không dùng văn bản hết hiệu lực (QT3): 0 trường hợp trên tập kiểm tra có tài liệu bị thay thế.
- **Baseline:** 🟡 Ragas (số cũ trong README, cần chạy lại); hit@k/MRR/coverage@k trên 300 câu D26 và đo gate trên 56 câu không trả lời được (`documents/rag-eval/`).

### 2.3.3. Bảo mật
- Xác thực bằng cookie HttpOnly ký HMAC (đã có); phân quyền SV/admin; SV chỉ đọc được hội thoại của mình (đã có).
- Chống chèn lệnh ở câu hỏi, lịch sử và nội dung tài liệu (đã có).
- Không lộ system prompt, khóa API, mã định danh nội bộ trong câu trả lời (S-Link lộ mã nội bộ 8/48 câu).
- Mật khẩu băm scrypt; khóa API LLM chỉ ở máy chủ, mã hóa khi lưu DB; CORS giới hạn; giới hạn tần suất câu hỏi; chống dò mật khẩu.
- **Baseline:** ✅ phần lớn đã có (auth, `require_admin`, rate limit theo phiên + IP, mã hóa key, security headers nginx); 🟡 trạng thái in-memory chỉ đúng với 1 worker.

### 2.3.4. Khả năng sử dụng trên điện thoại
- Hiển thị tốt từ màn rộng 360 px; vùng chạm ≥ 44 px; không tràn ngang.
- Hoạt động trong WebView Android/iOS; bàn phím ảo không che ô nhập.
- Câu trả lời hiển thị dần; nguồn trích dẫn mở dạng bottom-sheet; hiển thị trạng thái mất kết nối.
- Tiêu chí so sánh giao diện với S-Link (ĐA mục đánh giá: "theo bảng tiêu chí khảo sát").
- **Baseline:** 🟡 `/chat` đã tách khỏi `/admin`, có responsive; ❌ chưa thiết kế mobile-first, chưa có WebView.

---

## 2.4. Đặc tả một số use case quan trọng
**Mẫu bảng cho mỗi use case:** Mã/Tên · Tác nhân · Mô tả · Tiền điều kiện · Hậu điều kiện · Luồng sự kiện chính · Luồng thay thế · Ngoại lệ · Quy tắc nghiệp vụ liên quan · Chức năng liên quan.

### 2.4.1. Use case Hỏi đáp (UC02)
- **Tiền điều kiện:** SV đã đăng nhập. **Hậu điều kiện:** câu hỏi và câu trả lời được lưu vào hội thoại; câu trả lời có căn cứ được lưu cache.
- **Luồng chính:** SV nhập câu hỏi hoặc chọn câu gợi ý → hệ thống chuẩn hóa câu hỏi → kiểm tra phạm vi/chèn lệnh → tra cache → (không có) viết lại câu hỏi nối tiếp → truy xuất lai → xếp hạng lại → kiểm tra căn cứ → LLM sinh câu trả lời → hiển thị dần kèm nguồn → hiển thị câu hỏi liên quan → lưu hội thoại, lưu cache.
- **Luồng thay thế:** A1 trúng cache → trả ngay; A2 câu hỏi nối tiếp → viết lại thành câu độc lập; A3 câu hỏi chưa rõ khóa/ngành → trả lời theo từng trường hợp (QT4).
- **Ngoại lệ:** E1 ngoài phạm vi/chèn lệnh → câu từ chối cố định (QT7); E2 không đủ căn cứ → thông báo + phòng ban phụ trách (QT2); E3 LLM lỗi/quá thời gian → thông báo lỗi, cho phép gửi lại.
- **QT:** QT1, QT2, QT3, QT4, QT5, QT7. **CN:** CN02, CN04, CN11–CN14.

### 2.4.2. Use case Xem nguồn trích dẫn (UC03)
- **Luồng chính:** SV bấm số trích dẫn [n] trong câu trả lời hoặc thẻ nguồn → hệ thống hiển thị tên văn bản, Điều/Khoản/mục, ngày ban hành, đoạn trích → SV bấm "Xem đoạn gốc" → hệ thống tải và hiển thị đoạn văn bản đầy đủ, làm nổi phần trích.
- **Ngoại lệ:** tài liệu đã bị thay thế sau khi trả lời → vẫn hiển thị đoạn gốc kèm nhãn "Văn bản đã được thay thế".
- **Baseline:** 🟡 có thẻ nguồn, nhãn nguồn trích dẫn/liên quan; ❌ chưa có đoạn trích và xem đoạn gốc (admin đã có trình xem file gốc, có thể tái dùng).

### 2.4.3. Use case Đánh giá câu trả lời (UC06)
- **Luồng chính:** SV bấm "Hữu ích" hoặc "Không hữu ích" dưới câu trả lời → (nếu không hữu ích) hệ thống hiện ô góp ý → SV nhập và gửi → hệ thống lưu đánh giá.
- **Luồng thay thế:** SV đổi đánh giá → cập nhật bản ghi cũ (mỗi SV một đánh giá cho một câu trả lời).
- **Hậu điều kiện:** đánh giá xuất hiện trong màn Xem phản hồi (UC09).
- **Baseline:** ❌.

### 2.4.4. Use case Quản lý tài liệu tri thức (UC07)
- **Luồng chính (tải lên):** admin chọn file (PDF/DOCX/scan) và nhập nhóm tri thức, nguồn, ngày ban hành, ngày hết hạn, đối tượng áp dụng → hệ thống kiểm tra định dạng → trích xuất nội dung → chia đoạn → nhúng vector → lập chỉ mục → báo thành công.
- **Luồng thay thế:** A1 bản scan → trạng thái "chờ kiểm tra"; admin xem, sửa nội dung trích xuất rồi duyệt thì mới lập chỉ mục. A2 xem danh sách/lọc. A3 xem các đoạn đã chia. A4 xóa tài liệu → xóa đoạn, hủy cache liên quan.
- **Ngoại lệ:** file lỗi/rỗng → báo lỗi, giữ nguyên dữ liệu cũ (baseline đã làm đúng: parse ở vùng tạm trước khi ghi).
- **Baseline:** 🟡 có chọn dataset, upload chạy nền có tiến trình, chọn parser, parse → (sửa Markdown) → chia đoạn, xem/xóa/chuyển dataset; ❌ chưa có metadata nghiệp vụ và trạng thái duyệt bản scan (luồng sửa Markdown giữa hai bước có thể dùng làm bước duyệt).

### 2.4.5. Use case Cập nhật phiên bản tài liệu (UC08)
- **Luồng chính:** admin chọn tài liệu đang hiệu lực → chọn "Cập nhật phiên bản" → tải văn bản mới (cùng đối tượng áp dụng) và nhập ngày ban hành → hệ thống trích xuất, lập chỉ mục bản mới → chuyển bản cũ sang "đã thay thế" → hủy các câu trả lời trong cache dùng bản cũ → báo thành công.
- **Ngoại lệ:** bản mới lỗi → giữ nguyên bản cũ đang hiệu lực (giao dịch nguyên tử).
- **QT:** QT3, QT6. **Baseline:** ❌.

---

## 2.5. Thiết kế một số use case quan trọng (biểu đồ tuần tự)
**Thành phần (lifeline) dùng chung, trùng tên với kiến trúc 2.7:**
`Sinh viên` · `Khung chat (Web/WebView)` · `API Gateway (FastAPI router)` · `Dịch vụ xác thực` · `Bộ chuẩn hóa câu hỏi` · `Bộ kiểm soát (Guardrail)` · `Bộ nhớ đệm` · `Bộ viết lại câu hỏi` · `Bộ truy xuất lai` · `Bộ xếp hạng lại` · `Bộ sinh câu trả lời` · `Dịch vụ LLM` · `CSDL (PostgreSQL + pgvector)`.

### 2.5.1. Hỏi đáp khi câu trả lời đã có trong bộ nhớ đệm
1. SV gửi câu hỏi → Khung chat gọi `POST /api/chat/stream` (kèm cookie phiên).
2. API → Dịch vụ xác thực: xác minh phiên, kiểm rate limit.
3. API → Bộ chuẩn hóa: chuẩn hóa (dấu, viết tắt, khoảng trắng).
4. API → Guardrail: kiểm tra phạm vi, chèn lệnh → hợp lệ.
5. API → Bộ nhớ đệm: tra theo câu đã chuẩn hóa → **trúng**, còn hạn.
6. API → Khung chat: stream câu trả lời + nguồn (`from_cache = true`).
7. API → CSDL: lưu tin nhắn (câu hỏi, câu trả lời, nguồn, thời gian).
- **Baseline:** ❌ chưa có cache. **Lưu ý thiết kế:** với câu hỏi nối tiếp, khóa cache phải là câu **sau khi viết lại** (đã độc lập), nếu không sẽ trả nhầm.

### 2.5.2. Hỏi đáp khi phải truy xuất và sinh câu trả lời
1–4 như 2.5.1. 5. Bộ nhớ đệm: **không trúng**.
6. Bộ viết lại: dùng lịch sử hội thoại → câu độc lập.
7. Bộ truy xuất lai: vector (pgvector) ‖ BM25 (văn bản đã tách từ) → hợp nhất RRF → lọc tài liệu hiệu lực/đối tượng áp dụng.
8. Bộ xếp hạng lại (cross-encoder) → top-k đoạn.
9. Guardrail: kiểm tra đủ căn cứ (confidence gate), loại đoạn chứa chèn lệnh.
10. Bộ sinh câu trả lời → Dịch vụ LLM (stream) → từng phần câu trả lời về Khung chat.
11. Chuẩn hóa trích dẫn; kiểm tra QT1; thêm khuyến cáo QT5; sinh câu hỏi liên quan (CN04).
12. Lưu tin nhắn + nguồn; lưu cache kèm liên kết tài liệu nguồn.
- **Baseline:** ✅ bước 6–10 (rewrite rule-based, hybrid + RRF lọc theo dataset, reranker heuristic, confidence gate đã hiệu chỉnh, stream kèm event `step`); 🟡 bước 11 (đánh số trích dẫn, bỏ nguồn khi từ chối); ❌ bước 3 (chuẩn hóa không dấu — hiện guardrail chạy trên câu gốc), 5, lọc hiệu lực ở 7, cross-encoder mặc định ở 8, QT1/QT5/câu hỏi liên quan ở 11, cache ở 12.

### 2.5.3. Hỏi đáp khi câu hỏi bị từ chối
- **Nhánh a — ngoài phạm vi/chèn lệnh:** sau bước 4, Guardrail trả `out_of_scope`/`prompt_injection` → API stream câu từ chối cố định → lưu tin nhắn với `answer_status`, **không** lưu cache.
- **Nhánh b — không đủ căn cứ:** sau bước 9, confidence gate không đạt → câu thông báo + phòng ban phụ trách (QT2) → lưu với `answer_status = no_context` (dữ liệu cho CN09).
- **Baseline:** ✅ cả hai nhánh từ chối; ❌ phòng ban phụ trách, `answer_status`.

### 2.5.4. Nạp tài liệu tri thức
Lifeline: `Quản trị viên` · `Trang quản trị` · `API` · `Dịch vụ xác thực` · `Bộ trích xuất (Docling/OCR)` · `Bộ chia đoạn` · `Dịch vụ nhúng` · `CSDL` · `Chỉ mục BM25`.
1. Admin chọn dataset, file, parser + nhập metadata → `POST /api/documents` → trả `parse job` (202), client theo dõi `GET /api/parse-jobs/{id}`.
2. Xác thực cookie admin.
3. Lưu tạm file → Bộ trích xuất (text/Docling/LlamaParse) → Markdown (giữ tiêu đề, bảng) → lưu `documents.parsed_text`.
4. Admin xem/sửa Markdown (`PUT /api/documents/{id}/markdown`); (bản scan) trạng thái `needs_review` → chờ duyệt.
5. `POST /api/documents/{id}/chunk` → Bộ chia đoạn theo Chương/Điều/Khoản/Điểm, sinh `search_text` → gắn metadata (nhóm, khóa/ngành, năm học).
6. Dịch vụ nhúng → vector.
7. CSDL: ghi tài liệu + đoạn + vector trong **một giao dịch**; đưa file vào kho.
8. Đánh dấu chỉ mục BM25 cũ hết hạn (dựng lại lần tìm kiếm sau).
- **Baseline:** ✅ bước 2, 3, 6, 7, 8, tách bước 1→3 và 5, sửa Markdown ở 4; 🟡 bước 5 (đã chia theo Điều/Khoản/Điểm, chưa gắn khóa/ngành); ❌ metadata nghiệp vụ ở bước 1, trạng thái `needs_review` ở bước 4.

### 2.5.5. Cập nhật phiên bản tài liệu
1. Admin chọn tài liệu cũ → tải bản mới → `POST /api/admin/documents/{id}/versions`.
2. Xác thực admin → trích xuất, chia đoạn, nhúng bản mới (như 2.5.4).
3. CSDL (một giao dịch): thêm bản mới `status = active`, `supersedes_id = id cũ`, `version + 1`; bản cũ `status = superseded`.
4. Bộ nhớ đệm: hủy mọi mục liên kết với tài liệu cũ.
5. Đánh dấu chỉ mục BM25 hết hạn; báo kết quả.
- **Baseline:** ❌ (upload trùng tên trong cùng dataset chỉ thay file, không giữ lịch sử).

---

## 2.6. Thiết kế cơ sở dữ liệu

### 2.6.1. Thông tin các bảng trong cơ sở dữ liệu
Mỗi bảng trình bày: *Tên cột — Kiểu — Ràng buộc — Ý nghĩa*. Trạng thái so với baseline (`backend/app/db/models.py`):

| Bảng | Trạng thái | Cột chính (thiết kế) |
|---|:-:|---|
| `users` | 🟡 mở rộng (`0005`) | **có:** id, email (unique), full_name, password_hash (scrypt), created_at, last_login_at. **Thêm:** student_code (mã SV, unique), role (`student`/`admin`), cohort (khóa), major (ngành), is_active |
| `datasets` | ✅ (`0008`) | id, name (unique), description, enabled, created_at, updated_at. **Đề xuất thêm** (nếu dataset = nhóm tri thức, D7): knowledge_group, department, contact (QT2) |
| `documents` | 🟡 mở rộng | **có:** id, dataset_id (FK), source_path, title, file_type, content_hash, status, parsed_text, parsed_at, metadata (JSON), created_at, updated_at. **Thêm:** issuer/source, issued_date, expiry_date, audience (JSON: khóa, ngành), version, supersedes_id (FK documents), is_scanned, review_status |
| `chunks` | 🟡 mở rộng | **có:** id, document_id, chunk_index, text, search_text (`0003`), token_count, vector_id, embedding `vector(1536)` (HNSW), metadata (JSON: parent/child, section_path, legal_article/clauses/points). **Thêm:** audience, tokenized_text (cho BM25 tách từ) |
| `conversations` | 🟡 | **có:** id, user_id (owner key `user:<id>` hoặc `anon:<hash>`), title, created_at, updated_at. **Sửa:** khi bắt buộc đăng nhập thì user_id thành FK `users` |
| `messages` | 🟡 mở rộng | **có:** id, conversation_id, role, content, metadata (JSON: retrieval_debug, steps, reasoning, error, interrupted), created_at. **Thêm:** rewritten_question, answer_status, from_cache, latency_ms, ttft_ms, related_questions (JSON) |
| `message_sources` | ✅ | id, message_id, chunk_id, score, excerpt, created_at (thêm citation_no) |
| `app_config_overrides` | ✅ (`0006`) | key, value (JSON), encrypted_value, updated_at — cấu hình runtime do admin sửa |
| `model_profiles` | ✅ (`0007`) | id, kind (llm/embedding/reranker), name, provider, model, params (JSON), encrypted_api_key, created_at, updated_at |
| `feedback` | ❌ mới | id, message_id (FK), user_id (FK), rating (`helpful`/`not_helpful`), comment, created_at; UNIQUE(message_id, user_id) |
| `answer_cache` | ❌ mới | id, question_key (hash câu đã viết lại), question_text, answer, sources (JSON), created_at, expires_at, hit_count |
| `answer_cache_documents` | ❌ mới | cache_id (FK), document_id (FK) — hủy cache theo tài liệu (QT6) |
| `suggested_questions` | ❌ mới | id, question, dataset_id/knowledge_group, source (`faq`/`admin`), ask_count, is_active |

- **Quyết định cần ghi trong quyển:** vector lưu trực tiếp trong PostgreSQL (pgvector) → một giao dịch cho dữ liệu + vector; cấu hình và API key lưu DB (mã hóa) thay vì file/biến môi trường.
- **Migration:** đã có `0001`–`0008`. Ngọc viết migration mới (`users` mở rộng, metadata `documents`, `messages`, `feedback`, cache, gợi ý); Khánh đưa yêu cầu và review cột `chunks`. Nên bỏ `create_all` trong `init_db()` để chỉ dùng migration.

### 2.6.2. Lược đồ cơ sở dữ liệu hệ thống
- **Vẽ:** ERD đầy đủ các bảng trên, có khóa chính/ngoại, bội số quan hệ:
  users 1–n conversations 1–n messages 1–n message_sources n–1 chunks n–1 documents n–1 datasets; messages 1–n feedback n–1 users; documents 1–n documents (supersedes); answer_cache n–n documents (qua answer_cache_documents); datasets 1–n suggested_questions. `app_config_overrides`, `model_profiles` đứng riêng (không khóa ngoại).
- **Nguồn:** sinh từ SQLAlchemy models sau khi cập nhật (dbdiagram.io), đảm bảo khớp code.

---

## 2.7. Kiến trúc hệ thống

### 2.7.1. Kiến trúc tổng thể
- **Vẽ:** sơ đồ thành phần nhiều tầng:
  - **Tầng client:** Ứng dụng vỏ (Expo + WebView) → Khung chat web `/chat` (React, mobile-first); Trang quản trị `/admin` (React, desktop, lazy load); landing `/`, `/login`, `/register`. Cùng một bundle Vite, tách theo path (`src/lib/appRoute.js`).
  - **Tầng API:** FastAPI — hiện một file `api/routes.py` gồm các nhóm: auth (người dùng + admin), chat/stream, conversations (+ admin), documents, datasets, parse-jobs, config, model-profiles, retrieval test; thêm mới: feedback, sources, suggestions, admin feedback. Lớp lõi `core/`: auth, user_auth, rate_limit, config_store, model_profiles.
  - **Tầng nghiệp vụ RAG:** Bộ chuẩn hóa · Guardrail · Bộ nhớ đệm · Bộ viết lại · Bộ truy xuất lai (vector + BM25) · Bộ xếp hạng lại · Bộ sinh câu trả lời · Bộ kiểm soát câu trả lời.
  - **Tầng nạp dữ liệu:** Hàng đợi parse chạy nền (`ingestion/jobs.py`) · Bộ trích xuất (text/Docling/LlamaParse) · Bộ chia đoạn theo Điều/Khoản · Dịch vụ nhúng.
  - **Tầng dữ liệu:** PostgreSQL 16 + pgvector (dữ liệu nghiệp vụ, vector, cấu hình, kho mô hình, cache); kho file tài liệu `data/` theo dataset.
  - **Dịch vụ ngoài:** LLM (GPT-4o-mini/Gemini/mã nguồn mở), API embedding.
  - **Triển khai:** Docker Compose (postgres, backend, frontend) + Nginx production (upload, streaming, security headers).
- **Baseline:** ✅ tầng dữ liệu, tầng nạp dữ liệu, phần lớn tầng RAG, auth, tách chat/admin theo path, triển khai; ❌ ứng dụng vỏ, cache, bộ chuẩn hóa không dấu.
- **Cấu trúc thư mục mã nguồn** (phụ lục): `backend/app/{api,core,db,guardrails,generation,retrieval,ingestion,parsers,llm,vectordb,embeddings}`, `frontend/src/{admin,auth,landing,datasets,models,api,components,lib,styles}`, `mobile-shell/` (mới).

### 2.7.2. Luồng nạp dữ liệu và luồng truy vấn
- **Vẽ lại Hình 1 của ĐA** ở độ phân giải cao (bản trong file docx bị mờ), dạng flowchart hai làn: *Luồng truy vấn* (trên) và *Luồng nạp dữ liệu* (dưới), dùng chung CSDL và bộ nhớ đệm.
- **Luồng truy vấn:** câu hỏi → chuẩn hóa → kiểm tra phạm vi/chèn lệnh (từ chối → lưu lịch sử, không cache) → tra cache (trúng → trả lời) → viết lại → truy xuất lai → xếp hạng lại → kiểm tra căn cứ (không đủ → thông báo + phòng ban) → LLM sinh câu trả lời → kiểm soát câu trả lời → lưu cache + lịch sử → hiển thị dần.
- **Luồng nạp dữ liệu:** tài liệu + metadata → trích xuất (OCR nếu scan → admin duyệt) → chia đoạn theo Điều/Khoản + gắn khóa/ngành → nhúng → lưu CSDL + chỉ mục BM25 → (nếu thay thế) ngừng bản cũ + hủy cache.
- **Đối chiếu với code:** đánh số các bước và ghi file/hàm tương ứng (ví dụ `RagChain.retrieve_context` ở `backend/app/generation/rag_chain.py`, `stream_answer_with_llm` ở `generation/llm.py`, `IngestionPipeline` ở `ingestion/pipeline.py`) để Chương 3 tham chiếu lại.

---

## Thứ tự thực hiện và đầu ra

| Bước | Việc | Đầu ra | Phụ thuộc |
|---|---|---|---|
| 1 | Chốt quyết định D1–D8 (file `01-hien-trang-va-huong-di.md` mục 8; D6 đã chốt theo code) | Biên bản chốt | Cả nhóm |
| 2 | Viết 2.1, 2.2 (tác nhân, thuật ngữ, use case tổng quát và phân rã) | Văn bản + 3–4 biểu đồ use case | Bước 1 |
| 3 | Viết 2.6 (CSDL) — làm sớm vì 2.4, 2.5 tham chiếu tên bảng | Bảng mô tả + ERD | Bước 1; Khánh review bảng chunks |
| 4 | Viết 2.7 (kiến trúc + vẽ lại Hình 1) | 2 sơ đồ | Bước 3 |
| 5 | Viết 2.4 (5 đặc tả use case) | 5 bảng đặc tả | Bước 2 |
| 6 | Vẽ 2.5 (5 biểu đồ tuần tự) | 5 biểu đồ | Bước 3, 4, 5; Khánh review phần RAG ở 2.5.2–2.5.4 |
| 7 | Viết 2.3 (phi chức năng) — chốt con số sau khi có số đo S-Link | Bảng chỉ tiêu | Kết quả khảo sát của Khánh |
| 8 | Rà soát chéo: tên thành phần/bảng thống nhất giữa 2.4–2.7; khớp CN/QT | Bản Chương 2 hoàn chỉnh | Tất cả |

**Kiểm tra chất lượng trước khi nộp:**
- [ ] Mọi CN01–CN14 xuất hiện ít nhất một lần trong 2.2 và được truy vết tới use case hoặc thành phần.
- [ ] Mọi QT1–QT7 có "cách hệ thống đảm bảo" và xuất hiện trong ít nhất một đặc tả/biểu đồ tuần tự.
- [ ] Tên lifeline ở 2.5 trùng tên thành phần ở 2.7; tên bảng ở 2.5 trùng 2.6.
- [ ] Các phần **[CẦN BỔ SUNG]** đã có mục tương ứng trong checklist của Ngọc hoặc Khánh.
- [ ] Không mô tả tính năng mà code cuối cùng không có (hoặc ghi rõ là hướng phát triển).
