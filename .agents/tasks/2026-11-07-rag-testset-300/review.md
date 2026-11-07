# Review: 2026-11-07-rag-testset-300

- Reviewer: vòng 1 `agent-opencode` (`self_review`); vòng 2 chưa chỉ định — cần reviewer độc lập.
- Hình thức: vòng 2 `independent` (bắt buộc vì task có subagent).
- Trạng thái: `pending`.
- Bản được review: vòng 1 — commit `fb63f46`; vòng 2 — diff `fb63f46..HEAD` nhánh `feat/rag-testset-300` (fixture, `backend/tests/test_rag_testset_300.py`, hồ sơ task).
- Cập nhật lúc: `2026-11-08T00:10:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-04 và nhiệm vụ S-01..S-06.
- File/thay đổi cần đọc: `backend/tests/fixtures/ptit_rag_300.json` (toàn bộ 300 cases), 4 file staging `drafts/*.json`, diff so với `dev` (chỉ thêm file mới, không sửa pipeline).
- Bằng chứng kiểm chứng: `verification.md` V-01..V-04 (tất cả `passed`).
- Điểm cần đánh giá: tính đúng đắn schema, chất lượng `expected_terms` (verbatim, độ đặc hiệu), phủ nội dung Sổ tay, tương thích `eval_retrieval.py`.

## Nhận xét

### R-01 — Hai cases terms tần suất cao trong corpus

- Vị trí: `ptit_rag_300.json` — `d26_g2_045`, `d26_g3_050`.
- Liên quan: `AC-02`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: terms `Giáo dục thể chất`, `tiến trình học tập chuẩn` xuất hiện hàng chục lần trong corpus (lặp lại ở các bảng kế hoạch), nên hit@1 gần như đương nhiên với 2 cases này — làm đẹp chỉ số nhẹ, ảnh hưởng không đáng kể trên 300 cases.
- Đề nghị xử lý: đã thêm term `kỹ năng mềm` cho `d26_g2_045`; `d26_g3_050` giữ nguyên vì câu hỏi về khái niệm chung.
- Người xử lý: `agent-opencode`.
- Phản hồi/cách sửa: đã áp dụng trước khi finalize; quét lại 0 fails.
- Bằng chứng sau sửa: log `fails after fix: 0`.
- Xác nhận của reviewer: đã xác nhận.

### R-02 — Chưa chạy eval retrieval full trên DB

- Vị trí: phạm vi kiểm chứng V-04.
- Liên quan: `AC-04`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: mới verify tương thích ở mức unit-test + quét terms, chưa đo hit@k/MRR thực tế trên index (cần DB + embedding API).
- Đề nghị xử lý: ghi nhận giới hạn; chạy `eval_retrieval --mode hybrid` khi có môi trường DB trong task tiếp theo.
- Người xử lý: `agent-opencode`.
- Phản hồi/cách sửa: đã ghi vào verification (mục chưa chạy) và implementation (hạn chế bàn giao).
- Bằng chứng sau sửa: `verification.md` mục "Chưa chạy".
- Xác nhận của reviewer: đã xác nhận.
- Nếu deferred: theo dõi ở lần chạy baseline 300 cases đầu tiên (so với baseline 100 cũ trong `documents/rag-eval/README.md`).

## Nhận xét vòng 2 (từ code review commit `fb63f46`)

### R-03 — Term khớp vào giữa từ

- Vị trí: `d26_g4_018`, `d26_g4_013/014/016`, `d26_g4_011`.
- Liên quan: `AC-05`.
- Mức độ: `high`.
- Bắt buộc sửa: có.
- Trạng thái: `open` (đã sửa ở S-07, chờ reviewer vòng 2 xác nhận).
- Vấn đề và tác động: `điểm R` khớp `điểm rèn luyện` (27 vùng), `điểm I`/`điểm M`/`Thang điểm 10` khớp giữa từ khác; chunk sai phần vẫn tính hit@1.
- Phản hồi/cách sửa: thay bằng câu quy định đầy đủ (ví dụ `Điểm R và điểm M không được tính vào điểm trung bình chung học kỳ`); test assert số lần khớp nguyên từ bằng số lần khớp chuỗi con.
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

### R-04 — Số ngắn khớp vào số lớn hơn

- Vị trí: `d26_g4_001..009`, `d26_g3_004/019/020/024`, `d26_g6_015`.
- Liên quan: `AC-05`.
- Mức độ: `high`.
- Bắt buộc sửa: có.
- Trạng thái: `open` (đã sửa ở S-07, chờ reviewer vòng 2 xác nhận).
- Vấn đề và tác động: `0,0` khớp `10,0`, `4,0` khớp `4,00`, `20%`/`30%` khớp vào `120%`/`130%`; các case thang điểm không đo được việc lấy bảng Điều 25.
- Phản hồi/cách sửa: giữ khoảng điểm 10 (`9,0 - 10,0`...) và thay số thang 4 bằng `Tương ứng với 4,0`...; phần trăm gắn với cụm câu nguồn; test chặn term < 6 ký tự.
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

### R-05 — Term quá phổ biến

- Vị trí: 15+ case, ví dụ `d26_g4_025` (`giảng viên`), `d26_g3_054` (`Giám đốc Học viện`), `d26_g2_040`, `d26_g4_023`, `d26_g3_050/053/055`, `d26_g4_019`, `d26_g6_011`, `d26_g3_023`, `d26_g1_036`.
- Liên quan: `AC-05`.
- Mức độ: `high`.
- Bắt buộc sửa: có.
- Trạng thái: `open` (đã sửa ở S-07, chờ reviewer vòng 2 xác nhận).
- Vấn đề và tác động: chỉ cần một term trúng nên một term xuất hiện hàng chục lần khiến hit@k gần như tự động; R-01 vòng 1 chỉ ghi 2 case.
- Phản hồi/cách sửa: bỏ term phổ biến hoặc thay bằng cụm câu đặc hiệu; test giới hạn ≤ 3 vùng trong Sổ tay (lặp < 1000 ký tự tính một vùng).
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

### R-06 — Cách sửa R-01 làm case dễ hơn

- Vị trí: `d26_g2_045`.
- Liên quan: `AC-05`.
- Mức độ: `medium`.
- Bắt buộc sửa: có.
- Trạng thái: `open` (đã sửa ở S-07, chờ reviewer vòng 2 xác nhận).
- Vấn đề và tác động: thêm term `kỹ năng mềm` (68 vùng) chỉ mở rộng tập chunk tính là trúng.
- Phản hồi/cách sửa: thay 3 term phổ biến bằng một câu: `sinh viên phải hoàn thành các môn học Giáo dục thể chất, Giáo dục quốc phòng, kỹ năng mềm`.
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

### R-07 — Case trùng mục tiêu

- Vị trí: `d26_g5_018`/`d26_g2_048`; `d26_g3_031`/`d26_g3_043`.
- Liên quan: `AC-05`.
- Mức độ: `medium`.
- Bắt buộc sửa: có.
- Trạng thái: `open` (đã sửa ở S-07, chờ reviewer vòng 2 xác nhận).
- Vấn đề và tác động: paraphrase vòng 1 vẫn giữ cùng đáp án và cùng đoạn bằng chứng duy nhất; cặp `d26_g3_031/043` trùng hẳn bộ term. Bộ 300 thực tế ít mục tiêu hơn.
- Phản hồi/cách sửa: đổi `d26_g5_018` sang khoản 5.b (thời điểm đăng ký địa điểm thực tập); tách term học kỳ chính/phụ cho `d26_g3_031/043`; test chặn trùng câu hỏi và trùng bộ term.
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

### R-08 — Term trùng mục lục

- Vị trí: `d26_g4_017`, `d26_g4_031`, `d26_g5_001`, `d26_g1_047`, `d26_g3_051`, `d26_g1_041..046`.
- Liên quan: `AC-05`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open` (đề xuất `deferred`/không sửa riêng — chờ reviewer vòng 2 quyết định).
- Vấn đề và tác động: code review lo chunk mục lục được tính là trúng.
- Phản hồi/cách sửa: `clean_text` của chunker đã lọc bảng mục lục D26 nên rủi ro thấp; các term vừa trùng mục lục vừa phổ biến đã thay theo R-05; test bỏ mục lục khi đếm, không thêm điều kiện riêng.
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

### R-09 — `drafts/` lỗi thời

- Vị trí: `.agents/tasks/2026-11-07-rag-testset-300/drafts/*.json`.
- Liên quan: `AC-05`.
- Mức độ: `low`.
- Bắt buộc sửa: có.
- Trạng thái: `open` (đã sửa ở S-07, chờ reviewer vòng 2 xác nhận).
- Vấn đề và tác động: bản sao staging của 300 case, 2 case đã khác fixture — hai nguồn sự thật.
- Phản hồi/cách sửa: xóa `drafts/`.
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

### R-10 — Hồ sơ task không nhất quán

- Vị trí: `task.md`, `review.md`.
- Liên quan: `AC-05`.
- Mức độ: `medium`.
- Bắt buộc sửa: có.
- Trạng thái: `open` (đã sửa ở S-07, chờ reviewer vòng 2 xác nhận).
- Vấn đề và tác động: task `done` nhưng mọi AC chưa tích, trạng thái hiện tại còn ghi đang draft; self_review không hợp lệ khi có subagent; AC-04 không chạy trên fixture mới.
- Phản hồi/cách sửa: đưa task về `in_review`, tích AC có bằng chứng, thêm AC-05 và `tests/test_rag_testset_300.py`; review vòng 2 cần reviewer độc lập.
- Bằng chứng sau sửa: `verification.md` V-05 vòng 2.
- Xác nhận của reviewer: chưa.

## Lịch sử các vòng review

- 2026-11-07T14:45:00+07:00 — agent-opencode — toàn bộ dataset + V-01..V-04 — kết luận `approved`, R-01/R-02 `resolved` (low, không bắt buộc).
- 2026-11-08T00:10:00+07:00 — code review (`/code-review`) trên `fb63f46` — kết luận vòng 1 không còn hiệu lực: R-01 đánh giá thấp phạm vi (R-05), cách sửa R-01 sai hướng (R-06); thêm R-03..R-10. Review về `pending` chờ reviewer độc lập cho bản sau S-07.

## Kết luận

- Kết luận: `pending` (vòng 2).
- Nhận xét bắt buộc còn mở: R-03, R-04, R-05, R-06, R-07, R-09, R-10 — đã sửa ở S-07, chờ reviewer xác nhận.
- Nhận xét hoãn lại: R-02 (eval full trên DB) vẫn theo dõi ở lần chạy baseline 300 đầu tiên.
- Phần chưa review / giới hạn: hit@k/MRR thực tế chỉ xác nhận được khi chạy eval full trên DB.
- Bước tiếp theo: user/coordinator chỉ định reviewer độc lập; reviewer đọc diff `fb63f46..HEAD`, xác nhận hoặc mở lại R-03..R-10, rồi kết luận.
