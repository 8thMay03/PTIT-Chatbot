# Verification: 2026-10-21-uiux-redesign-context

- Verifier: `opencode-primary` (self-verification)
- Trạng thái tổng: `passed`
- Bản được kiểm tra: working tree — file `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md`
- Môi trường: Windows 11, PowerShell; đo trực tiếp trên `frontend/src/styles/*.css` và `frontend/src/**/*.jsx`

## Kiểm chứng tiêu chí

### V-01 — AC-01: Brief bao phủ đủ 12 mục

- Người thực hiện / thời gian: `opencode-primary` / `2026-10-21T00:00:00+07:00`.
- Loại: kiểm tra tài liệu đối chiếu yêu cầu.
- Thao tác: đọc lại mục lục brief, đối chiếu bảng "Nội dung" trong `task.md` (3 quyết định đã chốt) và danh sách màn hình từ `App.jsx`/`ChatView.jsx`/`DatasetView.jsx`/`DocumentView.jsx`/`ConfigView.jsx`/`ModelsView.jsx`/`SettingsView.jsx`.
- Kỳ vọng: mỗi màn hình trong mã nguồn có mục đặc tả tương ứng; mỗi quyết định đã chốt có mục riêng.
- Kết quả thực tế: có 12 mục §0–§12 + 2 phụ lục. Tất cả 7 màn (S-1…S-7) có đặc tả riêng. Quyết định "thiết kế UI trước, backend sau" → §11.3 + cột fallback trong §5. Quyết định "học vụ hiện đại" → §8. Quyết định "cân bằng, đầy đủ, tiếng Việt" → toàn bộ copy UI trong brief là tiếng Việt.
- Trạng thái: `passed`.
- Bằng chứng: `docs/design/PTIT-Chatbot-UI-UX-Redesign-Brief.md` §1–§12, Phụ lục A–B.

### V-02 — AC-02: Mọi khẳng định kỹ thuật có bằng chứng cụ thể

- Người thực hiện / thời gian: `opencode-primary` / `2026-10-21T00:00:00+07:00`.
- Loại: kiểm tra tài liệu đối chiếu mã nguồn.
- Thao tác: đọc trực tiếp các dòng CSS/JSX được trích dẫn trong §7.1, §7.2, §7.3 bằng `Get-Content` với `Select-Object -Skip` và `Select-String`.
- Kết quả thực tế — các mục đã kiểm chứng trực tiếp, tất cả khớp:

| Khẳng định trong brief | Kết quả đọc mã nguồn |
|---|---|
| `.chat-header` nền `rgba(255,255,255,0.72)` | `chat.css:21` → khớp |
| `.bubble-actions` chỉ hiện khi hover | `chat.css:279-288` (`opacity:0` → `.bubble-wrap:hover { opacity:1 }`) → khớp |
| `.dataset-search-field:focus-within` chỉ đổi `--border` → `--border-strong` | `dataset.css:78-80` → khớp |
| `.number-input-box:focus` không có ring | `config.css:301-304` (`border-color` + `outline:none`) → khớp |
| `.conv-group-label` `rgba(255,255,255,0.45)` | `layout.css:228` → khớp |
| `.conv-actions` có `:focus-within` (điểm tốt) | `layout.css:301-303` → khớp |
| `font-weight: 650` | `models.css:69` → khớp |
| `.mdl-choice:has(input:focus-visible)` (điểm tốt) | `models.css:217-219` → khớp |
| `.mdl-input:focus` dùng `:focus` không `:focus-visible` | `models.css:347` → khớp |
| `--header-h: 60px` | `tokens.css:128` → khớp |
| `.config-card-icon.purple` không dùng màu tím | `config.css:192-195` → khớp |
| Skip link `base.css:81-100` | khớp (`.skip-link` z-index 100, `:focus-visible` translate) |
| `.toast-close` 22×22 | `components.css:164-169` → khớp |
| z-index sidebar 45 > modal backdrop 40 | `responsive.css:35` vs `components.css:62` → khớp |
| Font mono hard-code 2 nơi | `document.css:336`, `config.css:253` → khớp |
| `parsePulse` keyframes | `dataset.css:301` → khớp |
| 6 gradient hard-code trong `chat.css` | dòng `121, 125, 159, 452, 515, 571` → khớp |
| Khối dark lặp 2 lần | `tokens.css:220` và `tokens.css:292` → khớp |
| Bảng → card list ở ≤640px | `responsive.css:167-181` (`tr { display:block }`) → khớp |
| `formatSize` không có GB | `lib/format.js:28-34` → chỉ B/KB/MB → khớp |
| `localStorage.removeItem("ptit_added_providers")` | `ModelsView.jsx:961` → khớp |
| `.modal { text-align: center }` | `components.css:79` → khớp |
| 2 luồng `PUT /config` độc lập | `ConfigView.jsx:155` và `ModelsView.jsx:513` → khớp |

- Trạng thái: `passed`.
- Bằng chứng: output đọc file nêu trong bảng; đã lưu các số liệu đếm ở V-03.

### V-03 — AC-02 (bổ sung): Số liệu thống kê trong §7.2 phải đo được

- Người thực hiện / thời gian: `opencode-primary` / `2026-10-21T00:00:00+07:00`.
- Loại: kiểm tra tự động bằng script đếm trên `frontend/src/styles/*.css`.
- Thao tác: PowerShell `Select-String` / `[regex]::Matches` trên 11 file CSS (không tính `tokens.css` khi đo màu/spacing/shadow/radius).
- Kết quả thực tế:

| Số liệu | Giá trị trong brief (sau đính chính) | Giá trị đo được |
|---|---|---|
| `rgba()` hard-code ngoài `tokens.css` | 31 | **31** (hex thô = 0) |
| Giá trị bo góc raw ngoài token | 15 | **15** (trong tổng 22 giá trị distinct) |
| `box-shadow` khai báo / giá trị raw | 43 / 19 | **43 / 19** |
| `padding`/`margin`/`gap` dùng px thô | 241/282 (85%) | **241/282 (85%)** — 41 khai báo dùng `var(--space-*)` |
| Token chết | 19 | **19** (142 token được định nghĩa; regex có lookahead `(?![a-z0-9-])` để `--space-1` không khớp `--space-10`) |

- Ghi chú: 5 số liệu ban đầu lấy từ báo cáo audit của subagent đã **sai** (37 / 14 / 13 / 87% / 22) và đã được sửa theo số đo trực tiếp.
- Trạng thái: `passed`.
- Bằng chứng: output PowerShell ghi ở phiên làm việc; giá trị đã ghi vào bảng §7.2 của brief.

### V-04 — AC-03: Brief tự đủ, không cần mở repo

- Người thực hiện / thời gian: `opencode-primary` / `2026-10-21T00:00:00+07:00`.
- Loại: rà soát nội dung bằng mắt đối chiếu từng mục.
- Thao tác: đọc lại brief từ đầu, hỏi từng phần "người đọc có cần mở repo không?".
- Kết quả thực tế: mọi tham chiếu mã nguồn đều kèm **mô tả hành vi** kèm theo (không chỉ số dòng) → người đọc hiểu vấn đề mà không cần mở file. Kiến trúc RAG được diễn giải thành bảng "hành vi backend → hệ quả UI". Danh sách API đầy đủ 22 endpoint kèm body/response. Copy UI tiếng Việt đầy đủ ở Phụ lục B.
- Trạng thái: `passed`.
- Bằng chứng: brief §1.2, §11.1, Phụ lục B.

### V-05 — AC-04 & AC-05: Ràng buộc kỹ thuật và thiết kế song song cho API chưa có

- Người thực hiện / thời gian: `opencode-primary` / `2026-10-21T00:00:00+07:00`.
- Loại: đối chiếu nội dung brief với `frontend/package.json` và `backend/app/api/routes.py`.
- Thao tác: xác nhận `package.json` không có UI library/Tailwind/router/state manager; xác nhận không có route `PATCH /documents` hay endpoint bật/tắt chunk trong `routes.py`.
- Kết quả thực tế:
  - `package.json` chỉ có `react`, `react-dom`, `lucide-react`, `vite`, `@vitejs/plugin-react` → brief §3 mục 1–2 và §12.3 khẳng định đúng.
  - `routes.py` có `POST/GET/DELETE /documents…` nhưng **không** `PATCH /documents/{id}` và **không** endpoint toggle chunk → brief §7.3 C1, C2 và §11.3 đề xuất `PATCH /documents/{id}`, `PATCH /documents/{id}/chunks/{chunk_id}` là đúng nhu cầu.
  - Brief §11.3 có cột "UI cần hỗ trợ" mô tả rõ cả 2 trạng thái (đã có API / fallback phiên) → thoả AC-05.
  - Brief §11.2 liệt kê 22 ràng buộc tương thích ngược (không đổi tên field, giữ hợp đồng NDJSON `start→delta→done` / nhánh `error` không có `done`, không render lại citation ở client) → đối chiếu với `routes.py:387-454` và `ChatView.jsx:280-314` → khớp.
- Trạng thái: `passed`.
- Bằng chứng: `frontend/package.json`, `backend/app/api/routes.py:360-460`, `frontend/src/ChatView.jsx:280-314`.

### V-06 — AC-06…AC-09: Tài liệu context hệ thống v2.0

- Người thực hiện / thời gian: `opencode-primary` / `2026-10-21T00:00:00+07:00`.
- Loại: kiểm tra tài liệu — rà soát nội dung + đối chiếu mã nguồn cho các khẳng định còn lại.
- Bản được kiểm tra: `docs/design/PTIT-Chatbot-System-Context.md` (689 dòng).

**AC-06 — Không mô tả giao diện hiện tại.** Rà soát toàn văn bằng cách tìm các dấu hiệu của mô tả UI cũ:

| Dấu hiệu cần loại bỏ | Kết quả |
|---|---|
| Sơ đồ ASCII khung ứng dụng / bố cục màn | 0 (đã gỡ §4.1) |
| Tên class CSS (`.app-shell`, `.bubble`, `.mdl-*`, `.doc-*`…) | 0 (đã gỡ §6.5) |
| Tên file CSS/JSX cụ thể | 0 (chỉ còn `src/styles/tokens.css` trong §6.1 vì đó là **ràng buộc kỹ thuật**, không phải mô tả UI) |
| Bảng token hiện tại, breakpoint hiện tại | 0 (đã gỡ §6.2–6.4) |
| Danh sách lỗi CSS/a11y kèm số dòng | 0 (đã gỡ §7.1–7.2) |
| "Vấn đề hiện tại cần giải quyết" của từng màn | 0 (đã gỡ §5) |
| Mô tả widget cụ thể ("pill-switch 18px", "5 icon button trần") | 0 |

Riêng §6.1 mục 10 vẫn nêu tên class Markdown (`doc-h1`…`doc-blockquote`) — đây là **hợp đồng dữ liệu bắt buộc** do `renderMarkdownHtml()` sinh ra, không phải mô tả giao diện → giữ lại là đúng.

**AC-07 — Đủ thông tin để thiết kế.** Đối chiếu từng khía cạnh:

| Khía cạnh | Có ở đâu | Nội dung |
|---|---|---|
| Sản phẩm & nguyên tắc | §1.1 | 3 nguyên tắc + hệ quả bắt buộc cho giao diện |
| Kiến trúc & trạng thái hệ thống | §1.2, §5 | sơ đồ RAG + 4 nhóm trạng thái phải biểu diễn |
| Tech stack | §1.3 | React 18, Vite 5, CSS thuần, lucide-react, không UI library |
| Đặc điểm kho tài liệu | §1.4 | 13 tài liệu, file 36MB, nhiều bảng, Điều/Khoản/Điểm, hundreds chunk |
| Người dùng & công việc | §2.1, §2.2, §2.3 | 2 nhóm + bảng nhu cầu → khả năng → việc giao diện phải làm |
| Phạm vi chức năng | §3.1–3.8 | 8 nhóm năng lực, 13 bảng tham số |
| Mô hình dữ liệu | §4 | 6 entity + trường + ghi chú hành vi |
| Hợp đồng API | §6.2–6.4 | 22 endpoint + NDJSON + ràng buộc dữ liệu |
| API còn thiếu + fallback | §6.5 | 6 năng lực, kèm hành vi khi chưa có API |
| Giới hạn sản phẩm | §7 | 9 giới hạn |
| Hướng thiết kế | §8 | nguyên tắc, tính cách thị giác, **danh sách tự do quyết định** |
| A11y / giọng văn | §9 | WCAG 2.2 AA + giọng trợ lý + giọng UI + mẫu lỗi |
| Đầu ra mong muốn | §10 | 7 bắt buộc + 4 nên + 3 không cần |

**AC-08 — Câu lệnh tường minh.** Kiểm tra phần đầu tài liệu: có khối cảnh báo *"Tài liệu này mô tả HỆ THỐNG, không mô tả giao diện hiện tại… Bạn hoàn toàn tự do đề xuất kiến trúc thông tin, bố cục và hệ thống giao diện."* + §0 mục 1 ("§3 là phạm vi chức năng, không phải mô tả các màn hình cũ") + §8.3 ("Những gì bạn hoàn toàn tự do quyết định") + §10.1 mục 1 ("đề xuất cách tổ chức **khác** với hiện tại nếu thấy có lý do"). → Đạt.

**AC-09 — Tách 2 vai trò.** Kiểm tra tên file + nội dung:
- `PTIT-Chatbot-System-Context.md` — không chứa mô tả UI cũ → dùng cho Claude Design.
- `PTIT-Chatbot-UI-UX-Current-State-Audit.md` — giữ nguyên toàn bộ v1.0 (audit hiện trạng) → dùng khi implement.
Đạt.

**Đối chiếu số liệu còn lại với mã nguồn** (các khẳng định không kèm số dòng trong v2.0):

| Khẳng định | Nguồn | Kết quả |
|---|---|---|
| 13 tài liệu trong `data/` | đếm file `data/` | 13 (11 file + `.gitkeep` + 1 file trùng tên `TB hoan thien thu tuc dau khoa hoc.pdf` ở 2 thư mục con) → khớp |
| `Sổ tay sinh viên D26.pdf` ~36MB | `data/` | 36116.3 KB ≈ 35.3 MiB → khớp |
| `max_top_k` mặc định 10 | `backend/app/api/schemas.py:138` | `max_top_k: int = 10` → khớp |
| `top_k` mặc định 4 | `schemas.py:137` | `top_k: int = 4` → khớp |
| `multi_query_count` mặc định 3 | `schemas.py:135` | `multi_query_count: int = 3` → khớp |
| `hybrid_vector_weight` mặc định 0.65 | `schemas.py:139` | `0.65` → khớp |
| `min_vector_score` 0.30 / `min_bm25_score` 2.0 | `schemas.py:156-157` | `0.30` / `2.0` → khớp |
| Tiêu đề hội thoại = 80 ký tự đầu | `backend/app/api/routes.py:318` | `title=request.message.strip()[:80]` → khớp |
| `RenameConversationRequest` 1–200 ký tự | `schemas.py:292` | `min_length=1, max_length=200` → khớp |
| Hợp đồng NDJSON `start`/`delta`/`done`/`error` | `routes.py:392-453` | khớp |
| Provider LLM: openai, gemini, azure, openai_compatible (+ anthropic, deepseek, cohere, qwen) | `schemas.py:168-174` | `available_providers.llm` liệt kê 8 provider → v2.0 chỉ nêu 4 provider **thực sự có UI cấu hình** trong `ModelsView.jsx` (OpenAI / Gemini / Azure / OpenAI-Compatible) → đúng phạm vi giao diện |
| Embedding provider: openai, sentence-transformers, cohere, gemini | `schemas.py:175` | khớp với §3.5 |
| Câu từ chối ngoài phạm vi | `backend/app/guardrails/patterns.py:1-5` | khớp nguyên văn |
| "Chưa tìm thấy thông tin này trong tài liệu." | `backend/app/api/routes.py:399` | khớp nguyên văn |
| Ragas metrics 0.90 / 0.95 / 0.93 / 0.85 | `README.md:439-442` | khớp |

- Trạng thái: `passed`.
- Bằng chứng: file `docs/design/PTIT-Chatbot-System-Context.md`; đối chiếu mã nguồn tại `backend/app/api/schemas.py`, `backend/app/api/routes.py`, `backend/app/guardrails/patterns.py`, `README.md`, thư mục `data/`.

## Lỗi, kiểm tra lỗi và phần chưa xác minh

- Lỗi đã phát hiện và đã sửa: 5 số liệu thống kê sai ở §7.2 v1.0 (xem V-03). Đã sửa và kiểm chứng lại bằng đo trực tiếp.
- Sai số dòng nhỏ: đã sửa 2 mục (`.toast-close` → `components.css:164-169`; bảng→card → `responsive.css:167-181`).
- Vòng 2: không phát hiện sai lệch nào trong tài liệu context (xem V-06).
- Kiểm tra chưa chạy: **không** có kiểm thử tự động cho brief (task tài liệu, không có mã nguồn ứng dụng được sửa → `npm run build` / `pytest` không liên quan và không được chạy).
- Phần chưa xác minh: brief **không** được kiểm chứng bằng thử nghiệm người dùng thật; độ hiệu quả của hướng thị giác §8 chỉ là đề xuất, chưa được kiểm chứng với stakeholder ngoài người dùng. **Tài liệu context v2.0 chưa được đưa cho Claude Design** nên chưa biết thiết kế sinh ra có đáp ứng kỳ vọng "thiết kế mới" hay không — đây là điểm cần kiểm chứng sau khi người dùng chạy thử.

## Kết luận

- Tiêu chí đạt: AC-01 (V-01), AC-02 (V-02, V-03), AC-03 (V-04), AC-04 + AC-05 (V-05), AC-06…AC-09 (V-06).
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: chuyển sang review; coordinator đóng task khi `review.md` kết luận `approved` trên bản mới nhất.
