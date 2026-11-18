# Chuẩn bị bảo vệ — Đáp án câu hỏi phản biện phần thiết kế (Chương 2)

> Nguồn câu hỏi: `issues/C2_hoi-dong_2026-11-17.md` mục 3 (Q-1…Q-33). Q-26…Q-33 ở mục "Chấm lại vòng 3". Đáp án bám thiết kế **sau vòng 4** (đã sửa QA-1…QA-16).
> Chuẩn: ĐA = `documents/Mô tả bài toán và phạm vi đồ án nhóm 5.docx.md`. Điểm nào thiết kế **chưa có** thì nói rõ là **hướng phát triển**, không hứa.
> Cách dùng: mỗi câu có câu trả lời nói trong khoảng 1 phút, dẫn chứng để mở đúng hình/bảng, câu hỏi nối tiếp có thể gặp.

## Phần A — 5 câu khó nhất (theo hội đồng chấm lại vòng 3)

### Q-26. Sinh viên đã đọc câu trả lời chưa có căn cứ (2.5.2 msg 29–32) rồi câu đó mới bị thay (msg 39). Nếu chụp màn hình hoặc mất mạng trước lệnh thay thì QT1 còn bảo đảm không?
**Trả lời.** Đây là đánh đổi có chủ đích, nhóm nêu trước: giữ streaming để giảm thời gian chờ token đầu (Bảng 6 dòng cuối), đổi lại câu chưa có căn cứ có thể hiện trên màn hình vài giây. Rủi ro thấp vì câu trả lời chỉ được sinh sau khi qua cổng đủ căn cứ (7) và prompt chỉ cho dùng k đoạn. Quy tắc lưu: máy chủ chỉ lưu hội thoại **sau** bước kiểm trích dẫn (2.5.2 msg 41 hoặc 45), kể cả khi khung chat đã ngắt kết nối (ghi ở `specs/2.5` quyết định 5, sẽ đưa vào 2.2.5), nên lịch sử luôn là bản đã kiểm (`no_context` nếu bị thay); mở lại hội thoại vẫn thấy thông báo đúng. Baseline hiện lưu phần đã sinh khi client ngắt, phải sửa theo thiết kế này khi cài đặt. Nhóm sẽ **đo tỷ lệ câu bị thay** trên tập kiểm tra. Nếu tỷ lệ cao thì chuyển sang kiểm trích dẫn ngay trong lúc stream; đây là hướng phát triển.
**Dẫn chứng.** `demo/2.5.2` msg 25–26 (cổng căn cứ), 29–32, 35–41, 45; `demo/2.7.2a` ◇ sau (8); `specs/2.7` mục 2.7.2a bước 7.
**Câu nối tiếp.**
- "Sao không chờ kiểm tra xong mới hiển thị?" → Khi đó TTFT bằng toàn bộ thời gian sinh, mất cải tiến tốc độ đã cam kết.
- "Khung chat hiển thị gì khi mất mạng?" → Lúc mở lại, khung chat tải hội thoại từ máy chủ và thấy bản đã thay.

### Q-1. Hạn chế thứ ba của S-Link (giao diện, "bị cắt, lộ mã định danh nội bộ 8/48") thể hiện ở đâu?
**Trả lời.** Ở mức thiết kế có ba điểm. Một, câu trả lời hiển thị dần theo streaming (2.5.2 loop) thay vì chờ trọn câu. Hai, trích dẫn được ánh xạ sang tên văn bản, ngày ban hành, Điều/Khoản (msg 34), người dùng không thấy mã đoạn nội bộ; bấm vào xem đoạn gốc (CN03). Ba, khung chat mobile-first nhúng WebView và câu hỏi gợi ý khi mở hội thoại (2.5.0, CN04). Chỉ tiêu giao diện được so sánh với S-Link theo bảng tiêu chí khảo sát (ĐA mục Đánh giá); giao diện chi tiết trình bày ở Chương 3.
**Dẫn chứng.** `demo/2.5.2` msg 29–34; `demo/2.5.0` msg 14–18; `demo/2.7.1` Tầng giao diện; ĐA Bảng 1 dòng cuối, mục "Đánh giá".
**Câu nối tiếp.**
- "Lỗi 'bị cắt' là do đâu, sao biết không lặp lại?" → Khung chat hiển thị markdown đầy đủ, không giới hạn độ dài; kiểm bằng cùng 48 câu khảo sát khi so sánh với S-Link.

### Q-27. Khóa đệm gồm (câu hỏi, khóa, ngành), hạn 7 ngày, cả nhóm bị hủy mỗi lần nạp. Tỷ lệ trúng thực tế còn bao nhiêu? Đo bằng lượt nóng có phải tự tạo kết quả đẹp?
**Trả lời.** Đệm phục vụ câu **lặp lại** trong cùng khóa, ngành. Câu hỏi gợi ý (CN04) và chuẩn hóa, viết lại làm các câu hội tụ. Báo cáo tách hai số: (1) độ trễ khi trúng đệm (lượt nóng, tách bằng `from_cache`); (2) tỷ lệ trúng ước lượng trên tập có câu lặp theo tỷ lệ thực tế, không phải chạy lại 100% câu. Nhóm chấp nhận tỷ lệ trúng thấp hơn để không trả nhầm đối tượng (QT4), đây là lựa chọn đã ghi trong thiết kế.
**Dẫn chứng.** `specs/2.5` quyết định 2; `specs/2.7` mục "Cấu hình thực nghiệm"; `messages.from_cache`; ĐA Bảng 6 dòng cuối.
**Câu nối tiếp.** "Tỷ lệ câu lặp lấy ở đâu?" → Từ khảo sát câu hỏi thực tế của sinh viên khi xây bộ đánh giá; nêu rõ đây là ước lượng.

### Q-30. "Trích dẫn hợp lệ" (2.5.2 msg 35) là gì? LLM gắn `[1]` cho một câu bịa thì có qua không?
**Trả lời.** Thiết kế kiểm ở mức **cấu trúc**: mỗi mã trích dẫn phải trỏ tới một trong k đoạn đã đưa vào LLM, và câu trả lời có ít nhất một mã như vậy. Mã trỏ ra ngoài k đoạn thì bị bỏ: danh sách nguồn gửi về khung chat (msg 42–43) chỉ gồm mã hợp lệ, nên mã lạ đã hiện trong lúc stream không có liên kết nguồn (khung chat hiển thị như chữ thường, chi tiết cài đặt). Không còn mã hợp lệ nào thì thay cả câu trả lời bằng thông báo không đủ căn cứ. Việc nội dung câu có đúng với đoạn hay không do chỉ số Faithfulness (Bảng 7) đo, có chấm tay một mẫu. Vì vậy câu bịa gắn `[1]` có thể qua bước kiểm này, nhưng sẽ bị Faithfulness phát hiện. Kiểm độ trùng nội dung giữa câu và đoạn được trích là hướng phát triển.
**Dẫn chứng.** `demo/2.5.2` msg 34–35, 42–43; ĐA QT1, Bảng 7.
**Câu nối tiếp.** "Vậy QT1 có phải hình thức?" → QT1 yêu cầu có nguồn; tính đúng của nội dung được giảm rủi ro bằng cổng căn cứ (7), prompt chỉ dùng k đoạn, và được đo bằng Faithfulness.

### Q-9. Ứng dụng vỏ truyền danh tính. Ai đó tự mở URL WebView với mã SV người khác thì sao? Ký gì, khóa ở đâu, hết hạn, chống phát lại?
**Trả lời.** Ở 2.5.0, Khung chat không tự tin danh tính: nó gửi danh tính tới API xác thực, API **kiểm tra chữ ký trước**, hợp lệ mới tạo/cập nhật tài khoản và cấp cookie phiên. Không có chữ ký đúng thì không đăng nhập được, nên tự gõ mã SV vào URL không đủ. Chữ "mô phỏng" ở 2.5.0 msg 9 nghĩa là **ứng dụng vỏ** do nhóm tự viết để thay ứng dụng thật của trường (ĐA mục 2); còn bước kiểm tra chữ ký là kiểm tra thật. Cơ chế: danh tính là chuỗi ký HMAC bằng khóa bí mật dùng chung giữa máy chủ ứng dụng vỏ và API xác thực, kèm thời điểm phát hành. Khi vẽ bản chính trên VP, nhãn msg 9 sẽ ghi "(ứng dụng vỏ mô phỏng)" để khỏi hiểu là kiểm tra giả. Đề xuất cài đặt ở Chương 3: token hạn 60 giây, kèm mã dùng một lần (nonce) được API ghi nhớ tới khi token hết hạn để chống phát lại.
**Dẫn chứng.** `demo/2.5.0` nhánh "Mở trong ứng dụng vỏ" (msg 7–9) và nhánh "Không hợp lệ"; `users.auth_source = shell`; `specs/2.5` mục 2.5.0; ĐA mục 2 "Nền tảng".
**Câu nối tiếp.**
- "Nếu khóa bị lộ?" → Đổi khóa ở cấu hình máy chủ, mọi token cũ mất hiệu lực. Khóa không nằm trong mã nguồn khung chat.
- "Truyền qua URL có bị lộ trong log?" → Đề xuất truyền qua header hoặc `postMessage` của WebView, token hạn ngắn; đây là chi tiết cài đặt, **chưa** vẽ trong 2.5.0.
- "Trường thật có tích hợp được không?" → Tích hợp S-Link là ngoài phạm vi (ĐA mục 2); ứng dụng vỏ chứng minh khung chat nhúng được và nhận danh tính.

## Phần B — Các câu còn lại (theo số thứ tự)

### Q-2. "hp k22 cntt dong khi nao": từ điển viết tắt lưu ở đâu? Khôi phục dấu sai thì sao?
**Trả lời.** Bộ chuẩn hóa (msg 8 ở 2.5.1–2.5.3) dùng từ điển viết tắt là tệp cấu hình của CN11, không phải bảng CSDL vì ít thay đổi và không thuộc nghiệp vụ quản trị. Khôi phục dấu có thể sai; khi đó câu sai được lưu lại để soi lỗi và đo, không có cơ chế tự sửa. Câu viết lại lưu ở `messages.rewritten_question` để soi lỗi. Kiểm chứng bằng cặp câu có dấu/không dấu (Bảng 6 dòng 1).
**Dẫn chứng.** `demo/2.5.1` msg 7–10; `messages.rewritten_question`; ĐA Bảng 6.
**Câu nối tiếp.** "Có dùng mô hình học máy khôi phục dấu không?" → Có thể, là lựa chọn cài đặt của CN11; thiết kế chỉ cố định vị trí bước.

### Q-3. Viết lại câu hỏi (2) đứng trước kiểm tra chèn lệnh (3). Nếu dùng LLM để viết lại thì câu chèn lệnh tới LLM trước khi bị chặn?
**Trả lời.** Thứ tự (2) rồi (3) lấy đúng Hình 1 và ĐA mục 5, vì câu không dấu, viết tắt phải được chuẩn hóa thì kiểm tra phạm vi mới đúng (đây là lỗi 5/5 của S-Link). Trong thiết kế, Bộ chuẩn hóa **không gọi Dịch vụ LLM**: ở 2.7.1 chỉ Bộ sinh câu trả lời phụ thuộc Dịch vụ LLM. Chuẩn hóa và viết lại câu nối tiếp chạy theo luật (từ điển viết tắt, khôi phục dấu, ghép ngữ cảnh từ lịch sử), nên câu chèn lệnh không tới LLM ở bước (2). Bộ kiểm soát ở bước (3) nhận câu đã viết lại; câu viết lại theo luật chủ yếu thêm ngữ cảnh từ lịch sử, ít khi bỏ bớt từ, nên mẫu chèn lệnh thường vẫn còn để phát hiện. Nhóm sẽ kiểm bằng các câu chèn lệnh trong bộ đánh giá (tỷ lệ từ chối đúng, Bảng 7).
**Dẫn chứng.** `demo/2.7.1` (Bộ chuẩn hóa không nối Dịch vụ LLM); `demo/2.5.2` msg 7–11; `demo/2.7.2a` (2)→(3); ĐA mục 5, Bảng 6 dòng 1.
**Câu nối tiếp.**
- "Viết lại theo luật thì câu nối tiếp phức tạp có hỏng không?" → Đo bằng tập câu nối tiếp trong bộ đánh giá; `messages.rewritten_question` lưu câu viết lại để soi lỗi. Viết lại bằng LLM là **hướng phát triển**; khi đó Bộ kiểm soát xét **cả câu gốc và câu viết lại**, và prompt coi đầu vào là dữ liệu.
- "Vậy chèn lệnh trong lịch sử hội thoại?" → Lịch sử do API tự đọc từ CSDL theo mã hội thoại (2.5.2 msg 5–6), chỉ khi hội thoại thuộc sinh viên, và **bỏ các lượt bị từ chối**; client không gửi hay sửa được lịch sử. Phần lịch sử còn lại được ghép vào câu độc lập nên cũng đi qua bước (3).

### Q-4. Chèn lệnh nằm **trong tài liệu** thì xử lý ở đâu?
**Trả lời.** Tài liệu chỉ do quản trị viên nạp từ nguồn chính thức (ĐA mục 2, 2.5.4), bản scan có bước kiểm tra nội dung. Yêu cầu gửi LLM tách rõ chỉ dẫn và k đoạn ngữ cảnh, chỉ dùng k đoạn làm dữ liệu (2.5.2 msg 28). Sau sinh còn kiểm tra trích dẫn (QT1). Loại đoạn có mẫu chèn lệnh trước khi gửi LLM là **hướng phát triển** (baseline đã có), chưa vẽ thành bước riêng.
**Dẫn chứng.** `demo/2.5.4` msg 1, opt bản scan; `demo/2.5.2` msg 28, 35.
**Câu nối tiếp.** "Admin nạp nhầm tài liệu độc hại?" → Xóa mềm tài liệu, hủy đệm theo tài liệu (`specs/2.6` quy tắc dữ liệu).

### Q-5. Hai văn bản mâu thuẫn nhưng không thay thế nhau (quy chế mới cho K2024, quy chế cũ vẫn cho K2021–2023)?
**Trả lời.** Đây không phải cập nhật phiên bản, vì CN08 chỉ thay văn bản **cùng đối tượng áp dụng** (2.5.5 msg 8). Quản trị viên nạp quy chế mới như tài liệu mới với `audiences` = K2024; bản cũ giữ `active` với `audiences` = K2021–2023. Khi truy xuất, đoạn được ưu tiên theo khóa, ngành của sinh viên (2.5.2 msg 21), và khóa đệm luôn gồm khóa, ngành nên không trả chéo. Nếu chưa rõ đối tượng, LLM được yêu cầu trình bày theo từng khóa (QT4, msg 28).
**Dẫn chứng.** `demo/2.5.5` alt "Khác đối tượng áp dụng"; `demo/2.5.4`; bảng `audiences` (`specs/2.6`); `specs/2.5` quyết định 2; ĐA Bảng 4 QT4.
**Câu nối tiếp.**
- "Lúc nạp bản cũ, admin ghi đối tượng là 'mọi khóa' thì sao?" → Thiết kế hiện **chưa có** thao tác sửa `audiences` của tài liệu đã nạp; đây là hạn chế, hướng phát triển là cho phép sửa thông tin tài liệu (CN07) và hủy đệm cùng nhóm khi sửa.
- "Nạp quy chế mới có làm đệm cũ sai không?" → Nạp tài liệu mới hủy đệm có nguồn cùng nhóm tri thức (2.5.4 msg 24).

### Q-6. Thông báo lịch thi hết hạn giữa chừng: đệm, lịch sử, câu nối tiếp?
**Trả lời.** Đệm: `expires_at` = min(7 ngày, 00:00 ngày sau hạn sớm nhất của các đoạn nguồn), NOT NULL, nên tự hết hạn đúng lúc tài liệu hết hiệu lực. Truy xuất bỏ tài liệu hết hạn (msg 21, QT3). Lịch sử giữ nguyên vì là bản ghi tại thời điểm hỏi. Câu nối tiếp chỉ dùng lịch sử để viết lại câu hỏi; căn cứ luôn truy xuất lại, nên văn bản hết hạn không vào ngữ cảnh.
**Dẫn chứng.** `specs/2.6` quy tắc "Hết hạn"; `answer_cache.expires_at`; `demo/2.5.2` msg 21.
**Câu nối tiếp.** "Mở lại hội thoại cũ có thấy nguồn đã hết hạn?" → Có, vì đoạn được giữ (xóa mềm); gắn nhãn "đã hết hạn/bị thay thế" khi xem nguồn là hướng phát triển.

### Q-7. Sinh viên không có khóa/ngành hỏi học phí?
**Trả lời.** Câu trả lời trình bày theo từng khóa, ngành (QT4 vế 2, msg 28). Sinh viên chưa có khóa, ngành thì **không đọc, không ghi** bộ nhớ đệm, nên không có trùng khóa. Vào qua ứng dụng vỏ luôn có khóa, ngành (2.5.0 msg 7).
**Dẫn chứng.** `demo/2.5.2` msg 13, 46; `specs/2.5` quyết định 2; `answer_cache.cohort/major` NOT NULL.
**Câu nối tiếp.** "Vậy SV đăng nhập trình duyệt chậm hơn?" → Đúng với câu hỏi lặp; đổi lại không bao giờ trả nhầm đối tượng.

### Q-8. SV D22 hỏi "học phí K20": ưu tiên khóa trong câu hay trong hồ sơ?
**Trả lời.** Thiết kế hiện truyền khóa, ngành **của sinh viên** để ưu tiên đoạn (msg 15, 21). Chữ "K20" vẫn nằm trong câu hỏi độc lập nên BM25 và vector vẫn khớp với đoạn của K20, và LLM được yêu cầu nêu đối tượng áp dụng (msg 28) nên câu trả lời ghi rõ đang nói về K20. Khóa đệm gồm cả câu hỏi (có "K20") nên không lẫn với câu "học phí" không nêu khóa. Tách thực thể khóa/ngành trong câu để ưu tiên hơn hồ sơ là **hướng phát triển**, sẽ ghi ở 2.2.5.
**Dẫn chứng.** `demo/2.5.2` msg 7–10, 15, 21, 28; ĐA QT4; Bảng 1 lỗi 3/4.
**Câu nối tiếp.** "Vậy có lúc ưu tiên nhầm đoạn D22?" → Có thể khi điểm của đoạn D22 cao hơn; đây là trường hợp được đo trong tập câu phụ thuộc khóa, ngành (Bảng 6 dòng 3).

### Q-10. Tài khoản SV đăng nhập bằng mật khẩu được tạo từ đâu?
**Trả lời.** Không tích hợp hệ thống quản lý đào tạo (ĐA mục 2), nên tài khoản được nạp sẵn hoặc tạo khi sinh viên vào qua ứng dụng vỏ lần đầu (`auth_source = shell`, 2.5.0 msg 12). Không có use case đăng ký vì ĐA không yêu cầu. Giả định này ghi ở 2.2.4.
**Dẫn chứng.** `demo/2.5.0`; `users.auth_source`; ĐA Bảng 5 CN01.

### Q-11. Bộ nhớ đệm dùng chung có lộ thông tin giữa sinh viên?
**Trả lời.** Đệm chỉ lưu câu trả lời có căn cứ từ văn bản công khai. Câu hỏi dữ liệu cá nhân bị từ chối ở (3). `answer_cache` không có `user_id`, không lưu lịch sử hay danh tính; chỉ có câu hỏi, khóa, ngành.
**Dẫn chứng.** `import/2.6-csdl.sql` bảng `answer_cache`; `specs/2.5` quyết định 4.

### Q-12. TTFT đo ở đâu? Vì sao trúng đệm vẫn trả theo streaming?
**Trả lời.** Máy chủ lưu `latency_ms`, `ttft_ms`. Số đo đầu-cuối đúng định nghĩa ĐA do script thực nghiệm đo phía client trên tập kiểm tra. Trúng đệm vẫn dùng cùng giao thức streaming để giao diện đồng nhất và so p50/p95 công bằng; `from_cache` tách nhóm.
**Dẫn chứng.** `messages.latency_ms`, `ttft_ms`, `from_cache`; `demo/2.5.1` msg 16; ĐA Bảng 7.

### Q-13. Khóa đệm là băm câu đã viết lại; hỏi khác nhau thì không trúng. Đệm có ý nghĩa?
**Trả lời.** Chuẩn hóa không dấu, viết tắt và viết lại làm câu hội tụ hơn. Câu hỏi gợi ý (CN04) khiến nhiều sinh viên gửi đúng một chuỗi. Hiệu quả đo theo Bảng 6 dòng cuối trên tập có câu lặp. Sau vòng 3, khóa luôn gồm khóa, ngành nên tỷ lệ trúng thấp hơn, đổi lại không trả nhầm đối tượng. Đệm ngữ nghĩa có rủi ro trả nhầm nên để hướng phát triển.
**Dẫn chứng.** `specs/2.5` quyết định 2; ĐA Bảng 6.

### Q-14. ĐA yêu cầu bật/tắt **độc lập** từng cải tiến trên cùng kho. Kiến trúc hỗ trợ ở đâu?
**Trả lời.** Mỗi cải tiến của Bảng 6 là một thành phần riêng ở 2.7.1: Bộ chuẩn hóa, Bộ truy xuất lai, Bộ xếp hạng lại, Bộ nhớ đệm. API hỏi đáp đọc **cấu hình thực nghiệm** (bảng `app_config_overrides`, admin bật/tắt ở màn Cấu hình; mô hình chọn từ `model_profiles`) gồm các cờ bật/tắt, `retrieval_mode = vector | bm25 | hybrid` (đủ 3 cấu hình của Bảng 6 dòng 4) và chiến lược chia đoạn; tắt cờ nào thì bỏ qua thành phần đó. Cùng một kho, mỗi tài liệu có hai bộ đoạn trong `chunks`: `fixed` cho RAG cơ bản và `legal` theo Điều/Khoản. Recall@k, Precision@k, MRR do script gọi thẳng Bộ chuẩn hóa → Bộ truy xuất lai → Bộ xếp hạng lại để lấy k mã đoạn theo thứ tự, rồi so `start_offset`/`end_offset` của đoạn với phần văn bản gán nhãn, nên dùng được với mọi cách chia. Mỗi lần đổi cấu hình thì xóa bộ nhớ đệm để số đo không lẫn.
**Dẫn chứng.** `specs/2.7` mục "Cấu hình thực nghiệm"; `import/2.6-csdl.sql` (`chunks.chunk_strategy`, `start_offset`, `end_offset`); `demo/2.5.4` msg 18; ĐA mục 5 "Mốc so sánh kỹ thuật", "Đánh giá", Bảng 6, Bảng 7.
**Câu nối tiếp.**
- "Vì sao không lưu cấu hình vào từng câu trả lời?" → Thực nghiệm chạy bằng script ngoại tuyến, mỗi lần một cấu hình cố định, kết quả ghi vào báo cáo. Cờ là cấu hình toàn hệ thống nên thực nghiệm chạy trên máy chủ riêng dùng bản sao CSDL; hệ thống phục vụ sinh viên luôn giữ cấu hình đầy đủ (`specs/2.7`).
- "Admin lỡ đổi cấu hình giữa lúc đo?" → Quy tắc: không đổi trong lúc đo, đổi thì xóa bộ nhớ đệm; `app_config_overrides.updated_at` để đối chiếu với thời điểm chạy.
- "Bật/tắt bộ nhớ đệm đo thế nào?" → So p50/p95 có và không có đệm trên tập có câu lặp; `messages.from_cache` tách nhóm.

### Q-15. Vì sao Đăng nhập là include? Vì sao CN10–CN14 không là use case? Dịch vụ LLM gắn Hỏi đáp có đúng?
**Trả lời.** Include là phần bắt buộc: Hỏi đáp cần danh tính để lấy khóa, ngành. CN10–CN14 không có tác nhân khởi phát nên không là use case; truy vết ở `truy-vet.md`. Dịch vụ LLM là tác nhân phụ của Hỏi đáp theo Bảng 2. Đặc tả 2.4 sẽ ghi thêm "đã đăng nhập" ở tiền điều kiện.
**Dẫn chứng.** `specs/2.2` quy ước; `demo/2.2.1`; ĐA Bảng 2.

### Q-16. Vì sao đệm trong PostgreSQL, không dùng Redis?
**Trả lời.** Hủy đệm cần join `answer_cache_sources` → `chunks` → `documents` **trong cùng giao dịch** với kích hoạt phiên bản (2.5.5). Quy mô một trường, tra theo khóa UNIQUE đủ nhanh, có chỉ mục `answer_cache(expires_at)`. Lý lẽ mạnh nhất: chặn ghi đệm cũ sau khi hủy dùng `cache_epoch` + khóa `FOR SHARE` trên `knowledge_groups`, `documents`; cơ chế này chỉ làm được khi đệm nằm **cùng CSDL giao dịch** với tài liệu. Dùng Redis phải ghi hai nơi, không bảo đảm được QT6.
**Dẫn chứng.** `demo/2.5.5` note giao dịch; `specs/2.6` quy tắc "Không ghi đệm cũ sau khi đã hủy", mục 2.6.3.

### Q-17. BM25 trong bộ nhớ: nhiều worker, vừa nạp tài liệu mới thì sao?
**Trả lời.** Chỉ mục BM25 dựng từ `chunks.tokenized_text`. Tính đúng không phụ thuộc chỉ mục có mới hay không: trạng thái, hạn của tài liệu được đọc từ CSDL cùng truy vấn vector (2.5.2 msg 19–20) và tra cho các đoạn chỉ có ở nhánh BM25, rồi bước hợp nhất (msg 21) bỏ bản bị thay hoặc hết hạn, dù chỉ mục cũ còn chứa. Tài liệu mới chỉ thiếu trong nhánh BM25 cho tới lần dựng lại; nhánh vector đọc thẳng CSDL nên vẫn tìm thấy. Cách dựng lại (theo chu kỳ hoặc khi số tài liệu đổi) là chi tiết cài đặt. Chuyển sang chỉ mục toàn văn của PostgreSQL là hướng phát triển.
**Dẫn chứng.** `demo/2.5.2` msg 18–21; `specs/2.5` mục 2.5.2 bước (5); `documents.status`.

### Q-18. LLM lỗi hoặc quá thời gian giữa lúc stream?
**Trả lời.** Khung chat báo lỗi và gỡ phần đã hiển thị. Máy chủ chỉ lưu thông báo lỗi với `answer_status = error`, **không** lưu phần đã sinh vì phần đó chưa qua kiểm trích dẫn (QT1), và không lưu đệm. Nhánh này không vẽ trong 2.5.2 để biểu đồ gọn, quy tắc ghi ở `specs/2.5` quyết định 5; có thể bổ sung `break` nếu hội đồng yêu cầu.
**Dẫn chứng.** `ck_messages_answer_status` có `error`; `specs/2.5` quyết định 5.

### Q-19. QT4, QT5 chỉ dựa vào prompt. LLM bỏ qua thì sao?
**Trả lời.** Thiết kế đặt QT4, QT5 trong yêu cầu gửi LLM (msg 28). Bảng 7 không có chỉ số riêng cho hai quy tắc này, nên nhóm chỉ ghi nhận khi chấm tay mẫu câu trả lời, không hứa con số. Hậu kiểm tất định (tự nối câu khuyến cáo theo nhóm tri thức), giống cách kiểm QT1, là hướng phát triển và cài đặt rẻ.
**Dẫn chứng.** `demo/2.5.2` msg 28, 35.

### Q-20. QT2 chọn phòng ban theo đoạn điểm cao nhất; đoạn đó có thể không liên quan?
**Trả lời.** Nhánh này chỉ chạy khi không đủ căn cứ, nên dùng **hai ngưỡng** khác nhau. Ngưỡng căn cứ ở (7) cao, quyết định có trả lời hay không. Ngưỡng chọn nhóm thấp hơn, chỉ để đoán chủ đề: điểm đoạn cao nhất vượt ngưỡng này thì lấy phòng ban của nhóm đoạn đó, không thì dùng nhóm mặc định (`is_default`; chỉ mục UNIQUE bộ phận bảo đảm tối đa một nhóm, dữ liệu khởi tạo luôn tạo một nhóm). Hai ngưỡng chọn trên tập điều chỉnh (ghi ở `specs/2.5` mục 2.5.3). Phân loại nhóm tri thức trực tiếp từ câu hỏi là hướng phát triển.
**Dẫn chứng.** `demo/2.5.3` msg 23; `demo/2.5.2` msg 37; `uq_knowledge_groups_default`.

### Q-21. Xóa hội thoại cascade mất dữ liệu CN09 và p50/p95?
**Trả lời.** Đúng, xóa hội thoại xóa cả tin nhắn và đánh giá; đây là quyền của sinh viên (CN05). Thực nghiệm p50/p95 chạy trên tập kiểm tra riêng nên không phụ thuộc hội thoại thật. Xóa mềm hội thoại để giữ thống kê là hướng phát triển.
**Dẫn chứng.** `import/2.6-csdl.sql` FK `ON DELETE CASCADE`.

### Q-22. Câu trả lời đệm bị đánh giá không hữu ích thì admin làm gì?
**Trả lời.** Admin xem ở 2.5.6b. Bộ nhớ đệm có hạn tối đa 7 ngày nên câu sai không tồn tại lâu; nạp tài liệu bổ sung vào nhóm sẽ hủy đệm cùng nhóm (2.5.4). Thao tác hủy riêng một câu đệm từ CN09 (thêm `messages.cache_id`) là hướng phát triển.
**Dẫn chứng.** `demo/2.5.6b`; `demo/2.5.4` msg 24; `answer_cache.expires_at`.

### Q-23. `chunks.expiry_date` trùng `documents.expiry_date`, `audiences.document_id` suy ra từ `chunk_id`: vi phạm 3NF?
**Trả lời.** Phi chuẩn có chủ đích. Một thông báo lịch thi có nhiều mục với hạn khác nhau nên đoạn có hạn riêng, mặc định lấy theo tài liệu. `audiences` cấp tài liệu cần `document_id` khi `chunk_id` rỗng. Tính nhất quán được bảo đảm bằng FK ghép `(chunk_id, document_id)` → `chunks(id, document_id)`.
**Dẫn chứng.** `import/2.6-csdl-chi-muc.sql`; `specs/2.6` quy tắc dữ liệu.

### Q-24. Học phí dạng bảng, học vụ là quy trình nhiều bước: chia theo Điều/Khoản có làm vỡ?
**Trả lời.** Bộ trích xuất giữ tiêu đề, bảng biểu (2.5.4 msg 10). Bộ chia đoạn không cắt giữa bảng hay danh sách bước; `section_path` giữ vị trí; `start_offset`/`end_offset` giữ thứ tự trong văn bản gốc. Quy tắc chi tiết ghi ở 2.2.4.
**Dẫn chứng.** `demo/2.5.4` msg 10, 18; ĐA Bảng 3.

### Q-25. Hai người làm khối lượng này có khả thi?
**Trả lời.** Nhiều phần đã có trên baseline (`specs/2.5` mục "Đối chiếu baseline": streaming, truy xuất lai, kiểm tra căn cứ, chia Điều/Khoản, parse nền). Phần mới tập trung vào bộ nhớ đệm, phiên bản, phản hồi, ứng dụng vỏ. Phân công theo Bảng 8: Ngọc frontend, backend ngoài RAG, ứng dụng vỏ; Khánh lõi RAG và chỉ số chất lượng. Ứng dụng vỏ chỉ mô phỏng tối thiểu.
**Dẫn chứng.** `specs/2.5`, `specs/2.2` "Đối chiếu baseline"; ĐA Bảng 8.

### Q-28. Span gán nhãn tính trên `extracted_text`. Admin sửa nội dung hoặc cập nhật phiên bản thì nhãn còn đúng không?
**Trả lời.** Bộ đánh giá gắn với một **bản chụp kho** cố định (danh sách mã tài liệu và phiên bản). Trong lúc đo không nạp, không sửa tài liệu. Nhãn lưu theo (mã tài liệu, vị trí bắt đầu, kết thúc) kèm chính đoạn chữ, nên script tự phát hiện lệch: chữ tại vị trí đó khác chữ đã lưu thì báo lỗi nhãn để gán lại.
**Dẫn chứng.** `specs/2.6` (offset tính trên `extracted_text` đã lưu); `specs/2.7` "không nạp tài liệu giữa các lượt đo".

### Q-29. Hai bộ đoạn `fixed` và `legal` gấp đôi vector. Khi vận hành bộ `fixed` để làm gì? Có bị truy xuất nhầm?
**Trả lời.** Truy xuất luôn lọc theo `chunk_strategy` của cấu hình. Vận hành thật dùng `legal`; bộ `fixed` chỉ phục vụ thực nghiệm và có thể xóa sau khi đo. Kho văn bản của một trường nhỏ nên chi phí nhúng không đáng kể. Vì chỉ mục HNSW dùng chung cho hai bộ nên khi tìm vector phải lấy dư ứng viên rồi lọc; đây là chi tiết cài đặt.
**Dẫn chứng.** `import/2.6-csdl.sql` (`chunk_strategy`, `uq_chunks_position`); `import/2.6-csdl-chi-muc.sql` (HNSW).

### Q-31. Bản scan kiểm tra bất đồng bộ (2.5.4, note sau msg 13) nhưng biểu đồ vẽ liền tới msg 27. Yêu cầu tải lên trả về lúc nào? Ai gọi bước chia đoạn?
**Trả lời.** Với bản scan, yêu cầu tải lên kết thúc ở msg 13 "Tài liệu chờ kiểm tra". Từ msg 14 là một yêu cầu khác: quản trị viên mở tài liệu, sửa và gửi nội dung đã kiểm tra (msg 15). Chính yêu cầu này lưu nội dung rồi chạy chia đoạn, lập chỉ mục (msg 16–28). Với PDF/DOCX thì chạy liền một lượt. Biểu đồ gộp hai yêu cầu và đánh dấu bằng note "Bất đồng bộ"; trên VP có thể tách bằng khung `ref`.
**Dẫn chứng.** `demo/2.5.4` msg 12–16 và note; `demo/2.7.2b` (C).

### Q-32. "Ưu tiên nguồn chính thức" (2.5.2 msg 21) làm thế nào? Có đo được không?
**Trả lời.** Thiết kế ghi "ưu tiên", **không lọc bỏ**, để câu chỉ có trong tài liệu tổng hợp (FAQ) vẫn trả lời được. Cơ chế là cộng trọng số cho đoạn có `documents.is_official` khi hợp nhất kết quả; trọng số cụ thể là chi tiết cài đặt. Trích dẫn luôn ghi rõ nguồn để sinh viên tự đối chiếu (QT5). Mục này là yêu cầu nghiệp vụ của Bảng 3, không thuộc các cải tiến Bảng 6 nên không đo riêng.
**Dẫn chứng.** `documents.is_official`; `demo/2.5.2` msg 21; ĐA Bảng 3 dòng Đời sống sinh viên.

### Q-33. Câu bị thay (QA-1) có tính vào p50/p95 và TTFT không?
**Trả lời.** Có tính, vì sinh viên thực tế đã chờ khoảng thời gian đó. Báo cáo tách nhóm theo `answer_status`: p50/p95 cho câu `answered` và báo cáo riêng cho `no_context`. TTFT đầu-cuối do script đo phía client.
**Dẫn chứng.** `messages.answer_status`, `ttft_ms`; `specs/2.7` mục "Cấu hình thực nghiệm".
