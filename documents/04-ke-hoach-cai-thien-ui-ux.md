# Kế hoạch cải thiện UI/UX — PTIT RAG Chatbot

> Phạm vi: toàn bộ 5 màn hình (Chat, Dataset, Document, Cấu hình, Mô hình).
> Định hướng: **giữ nhận diện thương hiệu PTIT, chuẩn hóa lại hệ thống thiết kế**.
> Bắt buộc: dark mode thật · responsive · accessibility · dọn UI giả + lịch sử chat.

---

## 1. Hiện trạng (kết quả audit)

### 1.1 Quy mô

| Hạng mục | Số liệu |
|---|---|
| Tổng mã nguồn frontend | 9.074 dòng |
| `styles.css` (một file duy nhất) | 4.803 dòng |
| Mã hex cứng trong CSS | ~500 lượt |
| Lượt dùng design token `var()` | ~130 lượt |
| `@media` query | 3 (trên 4.803 dòng) |
| `:focus-visible` | 0 |
| `prefers-reduced-motion` | 0 |
| CSS cho dark mode | 0 dòng |

### 1.2 Lỗi chức năng phát hiện được

| # | Vấn đề | Vị trí |
|---|---|---|
| B1 | **Nút dark mode không hoạt động.** State `theme` tồn tại nhưng không bao giờ được gắn vào DOM, và CSS không có bộ token tối. | `App.jsx:46`, `App.jsx:166` |
| B2 | **Phân trang bảng Files không có tác dụng.** Bảng render `filtered.map(...)`, bỏ qua hoàn toàn `currentPage`/`pageSize`. | `DatasetView.jsx:632` |
| B3 | **Lưu cấu hình thất bại vẫn báo thành công.** `catch` hiển thị toast xanh "Đã lưu cấu hình cục bộ" dù không có cơ chế lưu cục bộ nào. | `ConfigView.jsx:141` |
| B4 | **Modal "Edit Document" là giả.** Nút Save chỉ hiện thông báo, không gọi API (backend cũng chưa có endpoint tương ứng). | `DatasetView.jsx:1235` |
| B5 | **Tải cấu hình lỗi bị nuốt im lặng**, người dùng thấy giá trị mặc định mà tưởng là giá trị thật của hệ thống. | `ConfigView.jsx:81` |
| B6 | `DocumentView` tải **toàn bộ** chunk (batch 500, vòng lặp không giới hạn) rồi mới phân trang phía client. | `DocumentView.jsx:64` |

### 1.3 UI giả / nội dung sai

| # | Vấn đề | Vị trí |
|---|---|---|
| F1 | Dropdown ngôn ngữ không có menu — chỉ là chữ + mũi tên. | `App.jsx:145` |
| F2 | Link Discord/GitHub trỏ tới `discord.com` / `github.com`. | `App.jsx:118-136` |
| F3 | Tab **Logs** dùng dữ liệu hardcode (3 dòng log giả, timestamp `10/08/2026`). | `DatasetView.jsx:78` |
| F4 | Tab **Configuration** của Dataset là văn bản tĩnh hoàn toàn. | `DatasetView.jsx:1180` |
| F5 | Mô tả Retrieval testing nhắc tên sản phẩm khác: **"RAGFlow"**. | `DatasetView.jsx:875` |
| F6 | `ModelsView` seed sẵn 2 provider giả với API key giả (`sk-proj-••••89ab`, tên `test`/`test111`) và ghi thẳng vào localStorage. | `ModelsView.jsx:165` |
| F7 | Giá trị dự phòng bịa: dung lượng `"527 KB"`, ngày `"10/08/2026"`, tên file `"so-tay-sinh-vien-d21.md"`. | `DatasetView.jsx:159`, `DocumentView.jsx:181` |
| F8 | Nhiều nút không làm gì: "Filter chunks", "Add chunk", `page-size-selector`, "Filter test results". | `DocumentView.jsx:270`, `DatasetView.jsx:868` |
| F9 | Chọn nhiều dòng (checkbox) nhưng **không có hành động hàng loạt** nào. | `DatasetView.jsx:620` |
| F10 | Toggle "Enable" của document/chunk chỉ lưu trong state, mất khi reload. | `DatasetView.jsx:205` |

### 1.4 Vấn đề hệ thống thiết kế

- **Hai thang xám bị trộn**: `slate` (`#0f172a`, `#64748b`, `#e2e8f0`) và `gray` (`#111827`, `#6b7280`, `#e5e7eb`) dùng lẫn lộn giữa các màn.
- **Hai màu brand**: `#972635` (maroon PTIT, 18 lượt) và `#dc2626` (đỏ tươi) — không rõ màu nào là chính.
- **Màu accent lạc lõng**: `#14b8a6` (teal) làm màu hành động ở Dataset, không liên quan nhận diện PTIT.
- CSS đầy comment `/* Pixel-Perfect Matching image.png */` → style bám ảnh mẫu chứ không theo hệ thống.
- Ngôn ngữ giao diện trộn Việt–Anh ngay trong cùng một màn ("Files", "Add file", "Cuộc trò chuyện mới", "Chunk result").

### 1.5 Accessibility

- Không có `:focus-visible` → điều hướng bàn phím vô hình.
- Modal không có `role="dialog"`, không focus trap, không đóng bằng `Esc`.
- Chat streaming không có `aria-live` → trình đọc màn hình không đọc câu trả lời.
- Không có `prefers-reduced-motion`.
- `ChatView` dùng `hidden` nhưng vẫn mounted → nội dung ẩn vẫn nằm trong cây a11y nếu CSS ghi đè.
- Nhiều nút chỉ có icon mà thiếu `aria-label`.

### 1.6 Responsive

Chỉ 3 breakpoint. Các layout sau sẽ vỡ dưới 900px:
- `dataset-wrapper` (sidebar cố định + bảng 8 cột)
- `doc-view-split-layout` (2 cột)
- `retrieval-two-col-layout` (2 cột)
- `config-two-col-grid`, `model-mgmt-layout`

---

## 2. Kiến trúc CSS mục tiêu

Tách `styles.css` thành thư mục `frontend/src/styles/`, **giữ vanilla CSS** (không thêm dependency):

```
styles/
├── index.css        — điểm vào, @import toàn bộ
├── tokens.css       — primitive + semantic token, bảng sáng & tối
├── base.css         — reset, typography, focus-visible, reduced-motion
├── components.css   — button, input, switch, modal, toast, table, pagination, empty state
├── layout.css       — app shell, header, sidebar
├── chat.css
├── dataset.css
├── document.css
├── config.css
├── models.css
└── responsive.css   — breakpoint tập trung
```

### Quy ước token

Hai tầng rõ ràng:

1. **Primitive** — giá trị thô, không đổi theo theme: `--brand-600`, `--gray-200`, `--green-500`…
2. **Semantic** — ý nghĩa sử dụng, **đổi theo theme**: `--bg`, `--surface`, `--surface-raised`, `--text`, `--text-muted`, `--border`, `--accent`, `--danger`…

Quy tắc: **mọi màu trong file component chỉ được dùng token semantic.** Không hex cứng.

Dark mode kích hoạt theo 3 trạng thái:
- `:root` → bảng sáng (mặc định).
- `@media (prefers-color-scheme: dark)` có guard `:root:not([data-theme="light"])` → theo hệ điều hành.
- `:root[data-theme="dark"]` → người dùng chọn tay, thắng cả hai.

### Thống nhất màu

| Vai trò | Trước | Sau |
|---|---|---|
| Brand chính | `#972635` và `#dc2626` lẫn lộn | `--brand-600: #972635` (maroon PTIT) làm màu chính duy nhất |
| Thang xám | `slate` + `gray` trộn | Một thang `--gray-*` duy nhất |
| Accent hành động | `#14b8a6` teal | `--accent` dẫn xuất từ brand |
| Trạng thái | rải rác | `--success` / `--warning` / `--danger` / `--info` |

---

## 3. Các giai đoạn triển khai

### Giai đoạn 1 — Nền tảng token & dark mode
1. Viết `tokens.css` với bộ primitive + semantic đầy đủ cho cả hai theme.
2. Tách `styles.css` thành các file theo bảng ở mục 2.
3. Thay toàn bộ hex cứng bằng token semantic.
4. Gắn theme vào DOM: `document.documentElement.dataset.theme`, lưu `localStorage`, mặc định theo `prefers-color-scheme`, cập nhật `<meta name="color-scheme">`.
5. Sửa nút toggle để hiển thị đúng icon (hiện đang ngược logic).

**Kết quả:** dark mode hoạt động thật trên cả 5 màn. (Xử lý **B1**)

### Giai đoạn 2 — Accessibility nền
1. `:focus-visible` thống nhất toàn hệ thống bằng token `--ring`.
2. `@media (prefers-reduced-motion: reduce)` tắt mọi animation/transition.
3. Component `Modal` dùng chung: `role="dialog"`, `aria-modal`, focus trap, đóng bằng `Esc`, trả focus về nút mở.
4. `aria-live="polite"` cho vùng câu trả lời đang stream; `aria-busy` khi đang tải.
5. Bổ sung `aria-label` cho mọi nút chỉ có icon; `aria-current` cho tab/nav đang chọn.
6. Skip link "Tới nội dung chính".
7. Kiểm tra tương phản đạt WCAG AA (4.5:1 cho chữ thường) ở cả hai theme.

### Giai đoạn 3 — Responsive
Breakpoint thống nhất: `1200px` (desktop hẹp) · `900px` (tablet) · `640px` (điện thoại).

| Thành phần | Xử lý |
|---|---|
| Sidebar chat | Thành drawer trượt, mở bằng nút hamburger |
| Sidebar dataset | Thu thành thanh tab ngang phía trên |
| Bảng Files 8 cột | Dưới 900px chuyển sang danh sách card |
| Layout 2 cột (document, retrieval, config, models) | Xếp chồng 1 cột |
| Thanh nhập chat | Bám đáy, tránh vùng an toàn iOS |
| Header | Gom link phụ vào menu "thêm" |

### Giai đoạn 4 — Dọn UI giả
- **F1** Dropdown ngôn ngữ: bỏ hẳn (hệ thống chỉ có tiếng Việt), thay bằng nhãn tĩnh — tránh hứa hẹn tính năng chưa có.
- **F2** Link Discord/GitHub: trỏ đúng repo dự án, hoặc bỏ nếu chưa có.
- **F3** Tab Logs: chuyển sang nhật ký thao tác thật trong phiên (upload/parse/xóa/reindex), trạng thái rỗng rõ ràng khi chưa có sự kiện, ghi rõ "chỉ trong phiên này".
- **F4** Tab Configuration của Dataset: đọc số liệu thật từ `GET /api/config`, hoặc gộp vào màn Cấu hình.
- **F5** Xóa mọi nhắc tới "RAGFlow", viết lại mô tả theo hệ thống PTIT.
- **F6** Bỏ provider seed giả; trạng thái mặc định là danh sách rỗng có hướng dẫn.
- **F7** Bỏ giá trị dự phòng bịa, thay bằng dấu `—` hoặc skeleton.
- **F8** Nút không có chức năng: bỏ, hoặc hiện thực (dropdown page size là hiện thực được).
- **F9** Thêm thanh hành động hàng loạt khi có dòng được chọn (xóa nhiều, parse nhiều).
- **F10** Toggle Enable: nêu rõ phạm vi cục bộ, hoặc bỏ tới khi backend hỗ trợ.
- **B2** Nối phân trang vào bảng thật.
- **B3/B5** Toast lỗi phải đúng loại; tải cấu hình lỗi phải hiện banner cảnh báo.
- **B4** Modal sửa tiêu đề: bỏ hoặc bổ sung endpoint backend.

### Giai đoạn 5 — Lịch sử hội thoại
Backend hiện chỉ có `POST /chat` và `POST /chat/stream`, chưa có API liệt kê hội thoại.

1. Thêm `GET /api/conversations` (danh sách, phân trang), `GET /api/conversations/{id}` (chi tiết tin nhắn), `DELETE /api/conversations/{id}`.
2. Sidebar chat hiển thị danh sách hội thoại, nhóm theo thời gian (Hôm nay / 7 ngày qua / Cũ hơn).
3. Nhấp vào một hội thoại → khôi phục tin nhắn, giữ nguyên citation.
4. Đổi tên / xóa hội thoại.
5. Giữ khối "Mẹo sử dụng" ở dạng thu gọn phía dưới.

### Giai đoạn 6 — Hoàn thiện từng màn
- **Chat**: markdown hỗ trợ bảng + code block + blockquote; thông báo lỗi phân loại (mất mạng / backend chết / chưa ingest) kèm nút thử lại; skeleton khi tải; nút cuộn xuống cuối; citation có tooltip xem trước.
- **Dataset**: skeleton cho bảng; trạng thái rỗng/lỗi thống nhất; drag-drop có phản hồi rõ; toast thay banner.
- **Document**: tải chunk theo trang từ server thay vì tải hết (**B6**); nút Filter hoạt động hoặc bị bỏ.
- **Cấu hình**: cảnh báo "có thay đổi chưa lưu" khi rời màn; nút Reset dùng modal thay `window.confirm`.
- **Mô hình**: API key không bao giờ lộ; trạng thái test kết nối rõ ràng.
- **Toàn hệ thống**: một hệ thống toast duy nhất thay 3 cơ chế thông báo hiện tại (toast, banner, `window.confirm`).

---

## 4. Thứ tự ưu tiên

| Ưu tiên | Giai đoạn | Lý do |
|---|---|---|
| P0 | 1 — Token & dark mode | Nền tảng cho mọi việc sau; sửa lỗi người dùng nhìn thấy ngay |
| P0 | 4 — Dọn UI giả | Dữ liệu giả làm mất niềm tin vào hệ thống |
| P1 | 2 — Accessibility | Yêu cầu bắt buộc, chi phí thấp khi làm cùng lúc với tách CSS |
| P1 | 3 — Responsive | Sinh viên chủ yếu dùng điện thoại |
| P2 | 5 — Lịch sử hội thoại | Cần thay đổi backend |
| P2 | 6 — Hoàn thiện | Đánh bóng sau khi nền tảng ổn định |

---

## 5. Tiêu chí nghiệm thu

- [ ] Bật/tắt dark mode đổi được toàn bộ 5 màn, không còn mảng sáng sót lại; lựa chọn được ghi nhớ sau khi tải lại trang.
- [ ] `grep -E "#[0-9a-fA-F]{3,6}" styles/*.css` chỉ còn kết quả trong `tokens.css`.
- [ ] Duyệt toàn bộ giao diện chỉ bằng bàn phím, mọi điểm dừng đều có vòng focus nhìn thấy được.
- [ ] Mọi modal đóng được bằng `Esc` và giữ focus bên trong.
- [ ] Ở bề rộng 390px, không màn nào cuộn ngang.
- [ ] Không còn dữ liệu bịa trên giao diện; mọi số liệu đến từ API hoặc hiện `—`.
- [ ] Mọi nút hiển thị đều có chức năng thật.
- [ ] Tương phản chữ đạt WCAG AA ở cả hai theme.

---

## 6. Trạng thái triển khai

Toàn bộ 6 giai đoạn đã được thực hiện. Phần dưới ghi lại kết quả đo được sau khi hoàn thành.

### 6.1 Kiến trúc CSS

| Chỉ số | Trước | Sau |
|---|---|---|
| Số file CSS | 1 | 11 |
| Tổng số dòng | 4.803 | 5.462 |
| Mã màu cứng ngoài `tokens.css` | ~500 | **0** |
| Biến CSS không tồn tại | — | **0** |
| Selector chết | 111 | **0** |
| `@media` query | 3 | 4 breakpoint tập trung |
| `:focus-visible` | 0 | toàn hệ thống |
| `prefers-reduced-motion` | 0 | có |

Số dòng tăng vì đã bổ sung bảng token tối đầy đủ, quy tắc responsive và các component
dùng chung (toast, modal, skeleton, trạng thái rỗng) — trong khi 466 dòng CSS chết
và 111 selector không dùng đã bị loại bỏ.

### 6.2 Tương phản màu (WCAG AA)

16 cặp chữ/nền thực tế được kiểm tra tự động ở cả hai theme:

| Theme | Số cặp không đạt | Tỷ lệ thấp nhất |
|---|---|---|
| Sáng | 0 | 4,83:1 |
| Tối | 0 | 4,83:1 |

Ba lỗi được phát hiện và sửa trong quá trình kiểm tra:
- Chữ mờ trên nền chìm ở theme sáng chỉ đạt 4,34:1 → làm đậm `--gray-500`.
- Chữ trắng trên nút "Nạp lại toàn bộ" nền xanh chỉ đạt 2,54:1 → thêm token `--success-solid`.
- Chữ trắng trên nút xóa ở theme tối chỉ đạt 3,76:1 → `--danger` dùng sắc đỏ đậm hơn.

### 6.3 Thay đổi backend

Bổ sung 4 endpoint cho lịch sử hội thoại (dữ liệu đã có sẵn trong bảng
`conversations` / `messages`, chỉ thiếu API):

| Method | Đường dẫn | Chức năng |
|---|---|---|
| `GET` | `/api/conversations` | Danh sách, phân trang, bỏ qua hội thoại rỗng |
| `GET` | `/api/conversations/{id}` | Chi tiết kèm tin nhắn và citation |
| `PATCH` | `/api/conversations/{id}` | Đổi tên |
| `DELETE` | `/api/conversations/{id}` | Xóa (cascade sang messages) |

Ngoài ra, citation công khai nay được lưu vào `messages.metadata`. Trước đây chỉ có
`message_sources` (chunk_id, score, excerpt) được lưu — không đủ để dựng lại
trích dẫn kèm Điều/Khoản/Điểm khi mở lại hội thoại cũ.

Đã kiểm chứng trên dữ liệu thật: 6 hội thoại có sẵn hiển thị đúng, và một câu hỏi
mới ("Điều kiện xét tốt nghiệp là gì?") lưu rồi khôi phục lại được đủ 3 citation
kèm locator đầy đủ.

### 6.4 Bảo mật

- `format.js` chỉ escape `&`, `<`, `>`; dấu nháy lọt qua và bộ render chấp nhận
  **mọi scheme** trong link Markdown. Một link `javascript:` trong tài liệu tải lên
  hoặc trong câu trả lời của LLM sẽ chạy được mã trong trang. Đã escape thêm dấu
  nháy và giới hạn scheme ở `http`, `https`, `mailto`.
- `ModelsView` ghi **API key dạng plaintext** xuống `localStorage`. Đã chuyển sang
  chỉ lưu phần đã che cùng metadata; khóa thật giữ trong bộ nhớ phiên.

### 6.5 Những gì chưa làm và lý do

- **Chưa kiểm thử trực quan trên thiết bị thật.** Các quy tắc responsive được
  viết theo breakpoint đã thống nhất và build sạch, nhưng chưa mở trên trình duyệt
  ở khổ 390px để xác nhận không cuộn ngang. Cần một lượt kiểm tra bằng mắt.
- **Bật/tắt từng tài liệu và từng đoạn đã bị gỡ bỏ.** Backend không có trường
  `enable`; công tắc cũ chỉ lưu trong state và mất sau khi tải lại trang. Nếu cần
  tính năng này, phải bổ sung cột trong cơ sở dữ liệu trước.
- **Sửa tiêu đề tài liệu đã bị gỡ bỏ.** Không có endpoint tương ứng; nút Save cũ
  chỉ hiện thông báo mà không lưu gì.
- **Nhật ký vẫn chỉ trong phiên.** Máy chủ chưa có bảng log thao tác. Giao diện
  nói rõ điều này thay vì hiển thị dữ liệu giả như trước.
