# Verification: 2026-11-08-fe15-chat-composer

- Verifier: `claude-fe15`.
- Trạng thái tổng: `not_run` cho V-02; còn lại `passed` (V-03 phần admin `not_run`).
- Bản được kiểm tra: working tree nhánh `feat/chat-composer-ime-stop` (từ `dev` @ `6be857f`) lúc `2026-11-08T09:26+07:00`, trước commit; nội dung commit trùng bản này.
- Môi trường: Windows 11 Pro 10.0.26200, Node + vitest 3 + jsdom (frontend), Python `.venv` + pytest (backend), compose dev (backend + PostgreSQL + LLM thật; bind-mount mã nguồn) cho kiểm tra trình duyệt qua Claude in Chrome.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (IME, vitest)

- Người thực hiện / thời gian: `claude-fe15`, `2026-11-08T09:23+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh: `npx vitest run src/lib/keyboard.test.js src/api/chat.test.js src/landing/HeroComposer.test.jsx src/ChatView.test.jsx`.
- Kết quả thực tế: 4 file, 20 test pass. Ô chat: Enter `isComposing`/`keyCode 229`/Shift+Enter không gọi `fetch`, Enter của IME không bị `defaultPrevented`, Enter thường gọi. Ô hero: tương tự với `transitionTo`.
- Trạng thái: `passed`.

### V-02 — AC-02 (IME thật)

- Người thực hiện / thời gian: chưa chạy.
- Loại: kiểm tra thủ công.
- Thao tác (Windows 11): Settings › Time & language › Language & region › thêm "Tiếng Việt" + bàn phím "Vietnamese Telex"; chuyển bộ gõ bằng Win+Space. Mở `/chat` trên Chrome và Edge, gõ `hocj phis` (thấy gạch chân composition), nhấn Enter một lần → chữ được chốt thành "học phí", **không** gửi; nhấn Enter lần nữa → gửi. Lặp lại ở ô hero của landing (`/`). Thử nhanh với Unikey/EVKey nếu có (không phải IME, không được hồi quy).
- Thao tác (macOS, nếu có máy — Q-05): bộ gõ "Vietnamese – Telex" hệ thống, Safari và Chrome, cùng các bước.
- Kết quả thực tế: chưa chạy — tự động hoá trình duyệt (CDP/extension) không sinh được sự kiện composition của bộ gõ hệ điều hành; cần người yêu cầu thao tác.
- Trạng thái: `not_run`. macOS: `not_run` theo Q-05 (không có máy; vitest phủ nhánh `keyCode 229` của Safari).

### V-03 — AC-03 (top_k)

- Người thực hiện / thời gian: `claude-fe15`, `2026-11-08T09:24+07:00`.
- Loại: test tự động + kiểm tra trình duyệt.
- Kết quả thực tế:
  1. vitest: `chat.test.js` — body không có `top_k` khi không truyền, có khi truyền số; `ChatView.test.jsx` — body `{message, conversation_id}`. `passed`.
  2. Trình duyệt (`localhost:5173/chat`, bọc `window.fetch` để ghi body): body thật `{"message":"Điều kiện xét tốt nghiệp đối với sinh viên là gì?","conversation_id":null}` — không có `top_k`. `passed`.
  3. Đổi top_k mặc định ở màn Cấu hình admin rồi xem `selected_count` của step `rerank`: chưa chạy (cần đăng nhập admin). Phía server không đổi: `ChatRequest.effective_top_k` dùng `retrieval_default_top_k` khi `top_k` là `null`. `not_run`.
- Trạng thái: `passed` (phần client); bước 3 `not_run`.

### V-04 — AC-04 (Dừng, khôi phục, sidebar)

- Người thực hiện / thời gian: `claude-fe15`, `2026-11-08T09:20–09:26+07:00`.
- Loại: pytest + vitest + kiểm tra trình duyệt.
- Kết quả thực tế:
  1. `pytest tests/test_chat_db_lifecycle.py` — 14 passed (GET sau khi ngắt giữa stream có `interrupted: true`; ngắt trước delta có `content: ""`, `interrupted: true`).
  2. vitest: Dừng sau delta → giữ text + "Đã dừng"; Dừng trước delta → "Đã dừng trước khi có câu trả lời."; `onConversationSaved("c-1")` gọi ngay ở `start` (1 lần) và lần 2 ở `done`; mở lại hội thoại `interrupted` hiện nhãn và bubble dừng sớm.
  3. Trình duyệt, hội thoại mới: bấm Dừng khi đã có chữ → nhãn "Đã dừng" hiện (opacity 1, không cần hover), sidebar có ngay hội thoại "Điều kiện xét tốt nghiệp…" không cần tải lại; `GET /api/conversations/{id}` trả assistant `interrupted: true` (726 ký tự). Tải lại trang, mở hội thoại từ sidebar → cùng câu hỏi, phần trả lời và nhãn "Đã dừng".
  4. Trình duyệt, Dừng ngay khi panel suy luận có bước đầu (chưa có delta): bubble "Đã dừng trước khi có câu trả lời."; server lưu assistant rỗng `interrupted: true`; tải lại, mở hội thoại → cùng bubble (ảnh chụp màn hình trong phiên).
- Trạng thái: `passed`.

### V-05 — AC-05 (tin lỗi khi mở lại, Thử lại)

- Người thực hiện / thời gian: `claude-fe15`, `2026-11-08T09:23+07:00`.
- Loại: pytest + vitest.
- Kết quả thực tế: pytest — lỗi retrieval: GET trả `error: {type: "retrieval", request_id}`, response không chứa `error_class`/`RuntimeError`; test metadata phòng thủ (8 dạng) đạt ở cả route người dùng và admin. vitest — mở lại tin lỗi rỗng → bubble "Câu trả lời bị gián đoạn" + "Mã tham chiếu: abc123", mọi hàng assistant đều có bubble; "Thử lại" trên tin lỗi đã lưu gửi lại "Câu 3" với `conversation_id` hiện tại, giữ cặp cũ; "Thử lại" sau event `error` giữ cặp lỗi và thêm cặp mới (2 câu hỏi user, 1 bubble lỗi). Chưa tái hiện lỗi LLM thật trên trình duyệt.
- Trạng thái: `passed`.

### V-06 — AC-06 (429/422, bộ đếm)

- Người thực hiện / thời gian: `claude-fe15`, `2026-11-08T09:23–09:25+07:00`.
- Loại: vitest + kiểm tra trình duyệt.
- Kết quả thực tế:
  - vitest: 429 (hạn mức, đang bận), 422 (`message_too_long`), 429 giữa hội thoại đang mở → không thêm cặp tin, ô nhập có lại câu hỏi, `composer-alert` `role="alert"` đúng câu chữ, không có "Vượt quá giới hạn gọi mô hình"/"message:", alert ẩn khi sửa ô nhập; bộ đếm 1599 ẩn, 1600 hiện "1600/2000 ký tự", 2001 → `is-over`, `aria-invalid`, nút gửi `disabled`, Enter không gọi `fetch`.
  - Trình duyệt: (a) 2001 ký tự → "2001/2000 ký tự · Rút gọn câu hỏi để gửi", màu `rgb(185, 28, 28)`, nút gửi `disabled`; 1700 → "1700/2000 ký tự", nút bật. (b) 422: bọc `fetch` để gửi message 2001 ký tự → alert "Chưa gửi được câu hỏi / Câu hỏi quá dài (tối đa 2000 ký tự)." không có `message:`, số hàng tin không đổi (2 → 2), ô nhập giữ câu hỏi. (c) 429 "đang bận": giữ khoá lượt bằng một stream khác cùng phiên rồi gửi từ UI → alert "Chưa gửi được câu hỏi / Câu trả lời trước vẫn đang được tạo…", số hàng tin không đổi, ô nhập giữ câu hỏi, không có "Vượt quá giới hạn gọi mô hình". (d) 429 hạn mức: chỉ vitest (không hạ `CHAT_RATE_OWNER_PER_MINUTE` trên dev).
- Trạng thái: `passed`.

### V-07 — AC-07 (bộ test, build)

- Người thực hiện / thời gian: `claude-fe15`, `2026-11-08T09:19–09:26+07:00`.
- Loại: test tự động.
- Kết quả thực tế: `backend/`: `.venv/Scripts/python -m pytest -q` — 1273 passed, 24 skipped (69 s). `frontend/`: `npm test` — 31 file, 211 test pass; `npm run build` — thành công; `npm run check:bundle` — đạt (tổng gzip 83.35 kB, mốc 128.41 kB). Chạy lại `test_chat_db_lifecycle.py` (14 passed) và toàn bộ vitest (211 passed) sau lần sửa cuối (bỏ `aria-live` ở bộ đếm).
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu `ChatView.test.jsx` có 2 test sai do helper so `textContent` cả hàng (gồm avatar "B" và nút "Sao chép") — sửa helper đọc bubble; và cảnh báo `act(...)` ở hai test Dừng — click bằng `act` bất đồng bộ. Sau sửa: 13/13 pass, không cảnh báo.
- Chưa xác minh: V-02 (IME thật), V-03 bước 3 (admin top_k), 429 hạn mức trên trình duyệt, lỗi LLM thật khi mở lại.
- Dữ liệu dev phát sinh: vài hội thoại thử trong DB dev (phiên ẩn danh của trình duyệt kiểm thử).

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-04, AC-05, AC-06, AC-07; AC-03 phần client.
- Tiêu chí chưa xác minh: AC-02 (`not_run`, cần người yêu cầu); AC-03 bước admin (`not_run`).
- Đề xuất: người yêu cầu chạy V-02; nếu đạt thì đóng task và mở PR.
