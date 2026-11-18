# Checklist — Ngọc: Frontend + Backend (trừ lõi RAG), ứng dụng vỏ, thiết kế

**Baseline:** `dev @ 92aa804`, cập nhật 2026-11-09 (bản 2026-11-08 dựa trên `main`, đã cũ).
**Phân công (chốt 2026-11-08):** Ngọc làm **toàn bộ frontend và toàn bộ backend không thuộc RAG**: auth, API CN01–CN09, CSDL + migration, bộ nhớ đệm CN13, đo thời gian, triển khai Docker. Khánh chỉ làm lõi RAG (`03-checklist-khanh-rag.md`).
Phạm vi code của Ngọc: `frontend/`, `mobile-shell/`, `backend/app/{api,core,db,main.py}`, `backend/alembic/`, module cache mới, Docker/compose/nginx.
Ký hiệu: `[x]` đã có trên `dev` · `[ ]` còn phải làm. Mục 🔗 là **hợp đồng với Khánh**.

**Cập nhật 2026-11-18 theo thiết kế Chương 2 đã Đạt (GVHD + hội đồng):** nguồn chuẩn là `documents/chuong-2/` (`import/2.6-csdl.sql`, `specs/2.5`–`2.7`, `chuan-bi-bao-ve.md`). Mục đánh dấu 🆕 là việc mới từ thiết kế; mục ghi ⚠️ là đã đổi so với bản 2026-11-09.

---

## 0. Thiết kế (công việc 3) — làm trước
- [x] Chương 2 — **biểu đồ** (15 hình: use case, tuần tự, ERD 14 bảng, kiến trúc, hoạt động) Đạt GVHD + hội đồng mô phỏng 2026-11-18 (`documents/chuong-2/`).
- [ ] Chương 2 — việc trên VP trước khi chụp hình:
  - [ ] R-17: thử import tuần tự (`Project > Import > Text Based Sequence Diagram`, 8 file `import/2.5.*.txt`); xem VP có nhận `title`, `autonumber`, `alt`, `opt`, `loop`, `note`. Sau import đổi Sinh viên, Quản trị viên, Dịch vụ LLM → Actor; CSDL, Kho tệp → Database.
  - [ ] R-11: khung `ref` "Nạp tài liệu (2.5.4)" ở 2.5.5 msg 15.
  - [ ] R-23: kéo tay đường tự tham chiếu `documents.supersedes_id` trên ERD.
  - [ ] R-51: kéo hai nhãn `<<extend>>` ở 2.2.2 ra khỏi mép elip.
  - [ ] R-53: 2.5.2 (rộng 4377 px) đặt trang ngang hoặc tách 2 hình (bước 1–26, 27–46).
  - [ ] Đổi nhãn 2.5.0 msg 9 thành "(ứng dụng vỏ mô phỏng)"; R-22: tab tên gói ở 2.7.1 trống khi import, chỉnh tay nếu cần.
- [ ] Chương 2 — văn bản 2.2.4, 2.2.5, 2.3, 2.4 (R-18); 2.2.5 đưa vào quy tắc: lưu sau bước kiểm, hai ngưỡng QT2, khóa trong câu hỏi là hướng phát triển.
- [ ] 🔗 Chốt với Khánh: `prepare_query()` + `answer_stream()`, `answer_status`, nguồn có `chunk_id`/`document_id`, cột cần thêm cho `chunks` (mục 0 của `03-checklist-khanh-rag.md`).
- [x] D3 (cache trong Postgres, khóa theo khóa/ngành), D4 (đăng nhập theo mã SV + ứng dụng vỏ), D7 (`knowledge_groups`) — chốt theo thiết kế 2026-11-18.
- [ ] Chốt D2 (công nghệ ứng dụng vỏ), D8 (landing + chat ẩn danh — thiết kế yêu cầu đăng nhập để hỏi). D6 đã chốt theo code.

## 0b. Backend nền tảng
- [x] Migration `0003`–`0008`: `chunks.search_text`, `documents.parsed_text`, `users`, `app_config_overrides`, `model_profiles`, `datasets`.
- [ ] 🆕 Migration theo `documents/chuong-2/import/2.6-csdl.sql` (12 bảng nghiệp vụ + 2 bảng cấu hình giữ nguyên) và `import/2.6-csdl-chi-muc.sql` (HNSW, chỉ mục bộ phận, FK ghép `audiences`, UNIQUE bộ phận `supersedes_id`, nhóm mặc định). Ánh xạ: `datasets` → `knowledge_groups` (+ `department`, `contact`, `is_default`, `cache_epoch`); `parsed_text` ≈ `extracted_text`; thêm `audiences`, `feedback`, `answer_cache`, `answer_cache_sources`, `suggested_questions`; 13 CHECK. Thứ tự: `CREATE EXTENSION vector` → DDL → chỉ mục.
- [ ] Bỏ `Base.metadata.create_all` trong `init_db()` (`backend/app/db/session.py:59`) để chỉ dùng migration (đã gây lỗi ở `0005_users`, commit `d115421`).
- [ ] Tách `backend/app/api/routes.py` (**1821 dòng**) thành router: `auth`, `admin_auth`, `chat`, `conversations`, `documents`, `datasets`, `config`, `model_profiles`, `parse_jobs`.
- [x] Cấu hình runtime chỉ admin sửa (`require_admin`), lưu Postgres, API key mã hóa (`core/config_store.py`, `core/config_crypto.py`); kho mô hình (`core/model_profiles.py`).
- [x] Rate limit chat theo phiên + IP, giới hạn độ dài tin nhắn (`core/rate_limit.py`); LLM retry một tầng, deadline theo lượt (`llm/budget.py`); giải phóng DB session trước khi stream.
- [x] Nginx production: upload, streaming, security headers (`frontend/nginx/`).
- [ ] Trạng thái in-memory (parse job, rate limit, chống dò mật khẩu) chỉ đúng khi chạy 1 worker — ghi rõ trong quyển hoặc chuyển sang DB.
- [ ] **Đo thời gian:** `latency_ms`, `ttft_ms`, `from_cache` cho mỗi câu trả lời (hiện chỉ có `elapsed_ms` từng `step` trong metadata).
- [ ] Docker: thêm phụ thuộc Khánh cần (sentence-transformers, thư viện tách từ); `mobile-shell/`.

## 0c. CN13 — Bộ nhớ đệm
- [ ] ⚠️ Bảng `answer_cache` + `answer_cache_sources` (theo đoạn, không phải `answer_cache_documents`); `cohort`, `major`, `expires_at` NOT NULL.
- [ ] ⚠️ Trong API chat: đọc lịch sử theo mã hội thoại → `prepare_query()` 🔗 → bị từ chối thì trả ngay → tra cache theo băm(câu đã viết lại, **khóa, ngành**); SV chưa có khóa/ngành thì bỏ qua đệm → trúng thì stream lại (`from_cache = true`) → không trúng thì `answer_stream()` 🔗.
- [ ] ⚠️ Chỉ lưu câu `answered` có ≥1 nguồn hợp lệ; **không** lưu câu từ chối/bị thay/lỗi; ghi trong một giao dịch, khóa `FOR SHARE` dòng `knowledge_groups` rồi `documents` nguồn, chỉ ghi khi nguồn còn `active` và `cache_epoch` chưa đổi so với lúc truy xuất (QT6).
- [ ] ⚠️ `expires_at` = min(`created_at` + 7 ngày, 00:00 ngày sau `chunks.expiry_date` sớm nhất của đoạn nguồn, giờ Việt Nam).
- [ ] ⚠️ Hủy đệm theo **nhóm tri thức**: giao dịch tăng `cache_epoch` trước (khóa nhóm), xóa `answer_cache` có nguồn thuộc nhóm (`answer_cache_sources → chunks → documents.group_id`), rồi mới đổi trạng thái tài liệu. Gọi khi nạp mới, cập nhật phiên bản, xóa mềm (và khi sửa Markdown + chia đoạn lại, tắt nhóm). Hết hạn tự xử lý bằng `expires_at`.
- [ ] Cờ `CACHE_ENABLED` (lưu `app_config_overrides`). Đổi bất kỳ cờ thực nghiệm nào thì xóa toàn bộ `answer_cache`.

## 1. Khung frontend
- [x] Tách trang theo path: `/` landing, `/login` (SV + admin), `/register`, `/chat`, `/admin` (lazy load) — `src/lib/appRoute.js`, `src/main.jsx`.
- [x] Lớp API dùng chung `src/api/` (client, errors, stream NDJSON, từng nhóm endpoint) + TanStack Query; `fetch` trực tiếp chỉ còn ở `admin/AdminApp.jsx`, `ModelsView.jsx`.
- [x] Tách component: `datasets/`, `models/`, `auth/`, `landing/`; `ModelsView.jsx` còn 192 dòng.
- [x] Test giao diện bằng Vitest + jsdom (nhiều file `*.test.jsx`).
- [ ] TypeScript (hiện toàn bộ là `.jsx`/`.js`, không có `tsconfig.json`) — hoặc chốt ghi JS trong quyển.
- [ ] ESLint + Prettier; chuyển `vite`, `@vitejs/plugin-react` sang `devDependencies` (vẫn ở `dependencies`).
- [ ] Component còn lớn: `DatasetView.jsx` 1099 dòng, `DocumentView.jsx` 815, `ChatView.jsx` 784, `models/ModelKindPanel.jsx` 716, `ConfigView.jsx` 700.
- [ ] Màu hard-code còn lại: 7 chỗ `rgba(255…)` ở `styles/chat.css`, 10 chỗ ở `styles/layout.css` (đã có `tokens.css`).

## 2. API — CN01 Đăng nhập
- [x] Bảng `users` (email, full_name, password_hash scrypt, last_login_at); `POST /api/auth/register|login|logout`, `GET /api/auth/me`; cookie HttpOnly `ptit_user` ký HMAC (`core/user_auth.py`).
- [x] Admin đăng nhập chung `/login` bằng `ADMIN_EMAIL`/`ADMIN_PASSWORD` → cookie `ptit_admin`; `POST /api/admin/login|logout`, `GET /api/admin/session`; mọi route quản trị có `require_admin`; fail closed khi chưa cấu hình.
- [x] Chống dò mật khẩu theo IP (`TRUSTED_PROXY_IPS`), phiên ẩn danh `ptit_sid`; `user_id` không còn lấy từ body.
- [ ] Theo đồ án: đăng nhập **bằng mã SV**; thêm `student_code`, `auth_source` (`password`/`shell`), `cohort` (khóa), `major` (ngành), `role`/`is_active`; seed tài khoản SV mô phỏng; tắt đăng ký tự do (D4).
- [ ] ⚠️ Cầu nối nhận danh tính từ ứng dụng vỏ (2.5.0): token ký HMAC bằng khóa dùng chung, **hạn 60 giây + nonce dùng một lần** (đã hứa ở Q-9), truyền qua header/`postMessage` (không qua URL); kiểm chữ ký **trước**, rồi tạo/cập nhật tài khoản `auth_source = shell`, cấp cookie HttpOnly.
- [ ] (Tùy chọn) admin lưu DB thay vì một tài khoản trong env.
- [ ] Route quản trị chưa có tiền tố `/api/admin/` thống nhất (`/api/documents`, `/api/datasets`, `/api/config`… vẫn ở gốc) — quyết định giữ hay đổi khi tách router.

## 3. Giao diện sinh viên — `/chat` (mobile-first)
- [x] Đăng nhập/đăng ký, menu tài khoản (`auth/`, `components/UserMenu.jsx`).
- [x] **CN02:** stream, nút dừng (giữ phần đã sinh — ⚠️ theo thiết kế, phía máy chủ chỉ lưu sau bước kiểm QT1; xem mục 4), IME Enter, panel tiến trình suy luận (`ReasoningPanel.jsx`), hiệu ứng chuyển động.
- [x] **CN05:** danh sách hội thoại (`components/ConversationList.jsx`), theo tài khoản/phiên.
- [ ] **CN01 WebView:** nhận phiên từ ứng dụng vỏ; khi mở từ app thì bỏ landing.
- [ ] **CN02 mobile:** thiết kế lại cho màn 360–430 px (hiện vẫn layout sidebar desktop); ô nhập không bị bàn phím ảo che; safe-area; trạng thái online thật (chat chưa gọi `/api/health`).
- [ ] **CN03:** `[n]` bấm được → bottom-sheet: tên văn bản, Điều/Khoản, ngày ban hành, đoạn trích → "Xem đoạn gốc". Hiện đã có nhãn "Nguồn trích dẫn"/"Nguồn liên quan" (`lib/citations.js`). 🆕 Mã `[n]` không có trong danh sách nguồn hợp lệ hiển thị như chữ thường (Q-30).
- [ ] 🆕 **QT1:** xử lý sự kiện **thay câu trả lời đã hiển thị** bằng thông báo không đủ căn cứ + phòng ban; LLM lỗi giữa chừng thì gỡ phần đã hiển thị, hiện lỗi.
- [ ] ⚠️ Chat chỉ gửi câu hỏi + **mã hội thoại** (không gửi lịch sử — QA-18); mở lại hội thoại thì tải từ máy chủ.
- [ ] **CN04:** câu hỏi phổ biến từ API (bỏ `SUGGESTIONS` cố định ở `ChatView.jsx:24`); chip câu hỏi liên quan.
- [ ] **CN06:** nút Hữu ích / Không hữu ích + ô góp ý.
- [ ] Nhãn "Trả lời từ bộ nhớ đệm" (tùy chọn); câu từ chối có phòng ban (QT2).
- [ ] Yêu cầu mobile (2.3.4): từ 360 px, vùng chạm ≥ 44 px, không tràn ngang.

## 3b. Review giao diện ngày 2026-11-08 — ⚠️ ĐÃ CŨ
Bản review chụp trên `main @ 54a5582` (ảnh `human-workspace/images/fe-review-2026-11-08/`). FE trên `dev` đã được làm lại gần như toàn bộ (landing, auth, admin, datasets, models, API client, theme, motion) nên danh sách lỗi cũ **không còn dùng làm căn cứ**. User quyết định 2026-11-09 không chụp lại.
Những điểm từ bản cũ vẫn kiểm chứng được trong code `dev`:
- [ ] Màu hard-code `rgba(255…)` trong `chat.css`, `layout.css` (mục 1).
- [ ] Nhãn sidebar admin "Dataset", "Settings" bằng tiếng Anh giữa giao diện tiếng Việt (`admin/AdminShell.jsx`).
- [ ] Trạng thái online của chat không dựa trên `/api/health`.
- [ ] `vite`, `@vitejs/plugin-react` nằm trong `dependencies`; chưa có ESLint.
Khi cần review lại: chạy cả backend để xem chat có trích dẫn, modal, màn Dataset có dữ liệu, light mode.

## 4. API phía sinh viên
- [ ] **CN03:** nguồn kèm `chunk_id`, `document_id`, `excerpt`, ngày ban hành 🔗; `GET /api/sources/{chunk_id}` trả đoạn gốc (đoạn cha) + tài liệu. Bảng `message_sources` đã có cột `chunk_id`, `excerpt`.
- [ ] **CN04:** `GET /api/suggestions`; event `related` 🔗.
- [x] **CN05:** `GET/PATCH/DELETE /api/conversations*` lọc theo owner; admin xem mọi hội thoại qua `/api/admin/conversations*`.
- [ ] **CN06:** bảng `feedback`; `PUT /api/messages/{id}/feedback`; 🆕 kiểm câu trả lời **thuộc hội thoại của sinh viên**, không thì báo lỗi (2.5.6a).
- [ ] Event `done` thêm `message_id`, `answer_status`, `from_cache` 🔗 (hiện có `answer`, `sources`, `conversation_id`, `reasoning`, `steps`).
- [ ] Lưu `latency_ms`, `ttft_ms`, `answer_status`, `rewritten_question` vào `messages`.
- [ ] 🆕 API chat: nhận `conversation_id`, tự đọc lịch sử (chưa có thì tạo hội thoại; không thuộc SV thì báo lỗi; bỏ lượt bị từ chối) — 2.5.1–2.5.3 msg 5–6.
- [ ] 🆕 Lưu câu trả lời **sau** bước kiểm QT1, kể cả khi client ngắt; LLM lỗi chỉ lưu thông báo `error` (baseline hiện lưu phần đã sinh khi client ngắt — phải sửa).

## 5. Trang quản trị — `/admin` + API
- [x] Đăng nhập admin; layout desktop; Dataset, Settings (Cấu hình RAG, Mô hình, Giao diện), chat thử.
- [x] **CN07 (một phần):** dataset CRUD + bật/tắt + chuyển tài liệu; upload chạy nền có tiến trình (`/api/documents` → `/api/parse-jobs`); chọn parser + tier LlamaParse; parse lại; chia đoạn riêng; sửa/tải Markdown; xem file gốc (PDF/DOCX/MD/TXT); xem các đoạn; xóa.
- [ ] **CN07 còn thiếu:** cột nguồn/cơ quan ban hành, `is_official`, ngày ban hành, ngày hết hạn, đối tượng áp dụng (`audiences`), cờ bản scan + trạng thái `needs_review` (bất đồng bộ); form và bảng hiển thị; lọc theo hiệu lực; xóa **mềm** (`status = deleted`, giữ đoạn cho lịch sử) → hủy đệm theo nhóm 🔗. Nhóm tri thức có phòng ban, liên hệ, nhóm mặc định.
- [ ] ⚠️ **CN08 API + giao diện** (2.5.5): chỉ cho thay văn bản **cùng đối tượng áp dụng** và **mỗi lần một bản thay** (báo lỗi nếu khác đối tượng hoặc đã có bản thay đang xử lý); lưu tệp → lưu bản mới `processing` (`supersedes_id`, `version + 1`) → trích xuất, chia đoạn như CN07; bản cũ vẫn phục vụ tới khi kích hoạt; kích hoạt = một giao dịch: tăng epoch + hủy đệm nhóm → bản mới `active` → bản cũ `superseded`. Lịch sử phiên bản. Hiện upload trùng tên chỉ thay file.
- [ ] **CN09 API + giao diện:** danh sách đánh giá không hữu ích, câu `no_context`, thống kê theo nhóm tri thức.
- [x] Màn thực nghiệm: Cấu hình RAG + kho mô hình đã có, chỉ admin.
- [ ] Thêm cờ bật/tắt cải tiến mới của Khánh vào màn Cấu hình 🔗 (`app_config_overrides`: `NORMALIZATION_ENABLED`, `FOLLOW_UP_REWRITE_ENABLED`, `RETRIEVAL_MODE`, `RERANKER_ENABLED`, `CHUNK_STRATEGY`, `CACHE_ENABLED`).
- [ ] Quản lý câu hỏi gợi ý (CN04).

## 6. Ứng dụng vỏ — `mobile-shell/`
- [ ] Khởi tạo theo D2 (Expo + `react-native-webview`).
- [ ] Màn đăng nhập mô phỏng → lấy phiên từ API → mở WebView tới `/chat`.
- [ ] Nút back Android, mở liên kết ngoài, mất mạng.
- [ ] Hướng dẫn chạy (Expo Go hoặc APK).

## 7. Kiểm thử và thực nghiệm
- [x] Test backend pytest: khoảng **718 hàm `test_`** trong `backend/tests/` (đếm bằng grep 2026-11-09; chưa chạy được vì máy chưa cài phụ thuộc).
- [x] Test FE Vitest cho auth, admin, datasets, models, landing, API client.
- [x] `scripts/load_chat_stream.py`: kiểm tra tải nhiều stream đồng thời + `/api/health` (không đo p95/TTFT).
- [ ] Test API mới: feedback, versions, cache, đăng nhập mã SV.
- [ ] Kiểm tra trong WebView Android/iOS.
- [ ] ⚠️ Script benchmark p50, p95, TTFT đo phía client: tách nhóm theo `answer_status` (`answered` / `no_context`); có/không đệm chạy trên cấu hình đầy đủ, lượt lạnh (đệm rỗng) rồi lượt nóng, tách bằng `from_cache`; báo cáo thêm tỷ lệ trúng ước lượng trên tập có câu lặp (Q-27, Q-33).
- [ ] Ma trận cấu hình cùng Khánh; so sánh S-Link.

## 8. Tài liệu
- [ ] `README.md` trên `dev` vẫn nhắc ChromaDB (dòng 114, 421) — sửa; thêm cách chạy ứng dụng vỏ.
- [ ] Ảnh chụp cho quyển (chat trên điện thoại, admin, ứng dụng vỏ).
