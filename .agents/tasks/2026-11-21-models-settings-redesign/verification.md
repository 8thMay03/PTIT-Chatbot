# Verification: 2026-11-21-models-settings-redesign

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree trên `feat/models-settings-redesign` (nền `2948dc0`), chưa commit; lần cuối sau S-04.
- Môi trường: Windows 11, Node 24.14.0, Vitest (jsdom), Vite build. Ảnh chụp bằng `playwright-core` + Chromium 1234
  với `/api/**` giả lập (kho 3 LLM, 2 embedding có lựa chọn chờ khởi động lại, 1 reranker).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-agent / `2026-11-21T21:08:24+07:00`.
- Loại: test tự động + ảnh chụp.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; test `ModelsView › thẻ khâu hiện mô hình đang dùng…`,
  `SettingsView › tab Mô hình mở đúng panel…`; ảnh `#settings/models-llm`, `-embedding`, `-reranker` ở 1440px.
- Kỳ vọng: ba thẻ là link `#settings/models-*`, `aria-current="page"` đúng loại, tên/trạng thái theo dữ liệu, bấm thẻ
  gọi `onKindSelect`; không còn `.settings-kind-item`.
- Kết quả thực tế: test đạt. Ảnh: thẻ "Sinh câu trả lời · GPT-4.1 mini · Đang chạy", "Nhúng văn bản · e5-large · Chờ
  khởi động lại", "Xếp hạng lại · BGE reranker v2 · Đang bật"; thẻ đang xem nền thương hiệu. Ở 1024px chip không xuống
  dòng, nhãn không bị cắt (sau khi sửa vị trí chip, xem mục lỗi).
- Trạng thái: `passed`.
- Bằng chứng: ảnh `after/desk-llm-light.png`, `desk-emb-light.png`, `desk-rr-dark.png`, `desk-1024-llm-light.png`
  (scratchpad phiên).

### V-02 — AC-02

- Người thực hiện / thời gian: claude-agent / `2026-11-21T21:08:24+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: `ModelsView › thêm LLM qua ngăn kéo rồi bấm Dùng…`, `› chỉ mở panel…` (không còn `select`).
- Kỳ vọng: hàng `.env` đang dùng ban đầu. "Dùng gpt-4.1" gửi `{kind:"llm", profile_id:"p1"}` và hàng chuyển `is-active`.
  Hàng đang dùng không có nút Dùng và không xoá được. "Dùng Cấu hình máy chủ" gửi `profile_id: null`.
- Kết quả thực tế: đạt.
- Trạng thái: `passed`.
- Bằng chứng: output `npx vitest run` (47 file, 393 test đạt).

### V-03 — AC-03

- Người thực hiện / thời gian: claude-agent / `2026-11-21T21:08:24+07:00`.
- Loại: test tự động + ảnh chụp.
- Lệnh / thao tác: `ModelsView › embedding: khoá Dùng khi sai số chiều…`, `› xoá mô hình không dùng…`.
- Kỳ vọng: "Dùng Large" (3072 chiều) bị khoá. "Dùng Small" mở Modal có "Nạp lại toàn bộ"; Huỷ thì không gọi API, xác
  nhận thì gọi `activate`. Sau đó hiện cảnh báo khởi động lại, hàng hiện "Đã chọn", hàng `.env` hiện "Đang chạy".
- Kết quả thực tế: đạt. Ảnh embedding: cảnh báo vàng đầu card, "Đã chọn" ở e5-large, "Đang chạy" ở OpenAI small.
- Trạng thái: `passed`.
- Bằng chứng: output test; ảnh `after/desk-emb-light.png`, `mobile-emb-dark.png`.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-agent / `2026-11-21T21:08:24+07:00`.
- Loại: test tự động + ảnh chụp.
- Lệnh / thao tác: `ModelsView › ngăn kéo: Esc đóng khi chưa đổi…`; test thêm mô hình kiểm tra focus vào
  `#mdl-llm-form-name`, `role="dialog"`, key không còn trong `document.body` sau khi lưu; ảnh bấm "Sửa GPT-4.1 mini".
- Kỳ vọng: Esc đóng và trả focus về nút Sửa khi form chưa đổi. Sau khi nhập thì Esc và scrim không đóng, hiện "Có thay
  đổi chưa lưu"; Huỷ đóng.
- Kết quả thực tế: đạt. Ảnh: ngăn kéo 520px, nhà cung cấp lưới 2×2, footer Kiểm tra kết nối / Huỷ / Lưu thay đổi (sáng,
  tối). Ở 390px ngăn kéo rộng hết màn và nhà cung cấp xếp một cột.
- Trạng thái: `passed`.
- Bằng chứng: output test; ảnh `after/desk-edit-light.png`, `desk-edit-dark.png`, `mobile-edit-light.png`.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-agent / `2026-11-21T21:08:24+07:00`.
- Loại: test tự động + ảnh chụp + đo DOM.
- Lệnh / thao tác: `SettingsView › danh sách mục (mobile) hiện mô hình đang dùng…`; ảnh 390×844 `#settings`,
  `#settings/models-llm`, `#settings/models-embedding`; đo `document.documentElement.scrollWidth`.
- Kỳ vọng: mục Mô hình trong danh sách hiện tên mô hình (kèm trạng thái khi cảnh báo); trang loại mô hình không có thẻ
  khâu, không cuộn ngang.
- Kết quả thực tế: test đạt. Ảnh danh sách: "GPT-4.1 mini", "e5-large · Chờ khởi động lại", "BGE reranker v2". Trang
  loại có nút quay lại, không có thẻ khâu; hàng xếp nút xuống dòng hai. `scrollWidth` = 390 ở cả ba ảnh mobile.
- Trạng thái: `passed`.
- Bằng chứng: ảnh `after/mobile-index-light.png`, `mobile-llm-light.png`, `mobile-emb-dark.png`; log script chụp.

### V-06 — AC-06

- Người thực hiện / thời gian: claude-agent / `2026-11-21T21:08:24+07:00`.
- Loại: test tự động + build.
- Lệnh / thao tác: `npx vitest run`; `npx vite build` trong `frontend/`.
- Kỳ vọng: toàn bộ test đạt, build thành công.
- Kết quả thực tế: 47 file, 393 test đạt; `✓ built in 2.25s`.
- Trạng thái: `passed`.
- Bằng chứng: output lệnh trong phiên; ảnh sáng/tối/mobile ở V-01 … V-05.

### V-07 — AC-04 (sau S-04: hộp thoại giữa màn hình)

- Người thực hiện / thời gian: claude-agent / `2026-11-21T21:18:07+07:00`.
- Loại: test tự động + build + ảnh chụp.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; `npx vite build`; ảnh bấm "Thêm mô hình" ở 1440×900 (sáng/tối), 1024×700, 390×844
  và ở loại embedding.
- Kỳ vọng: overlay nằm giữa màn hình, có scrim, `role="dialog"`. Nội dung dài thì thân cuộn, footer luôn thấy. Esc/scrim/
  Huỷ như V-04. Không cuộn ngang.
- Kết quả thực tế: 47 file, 393 test đạt; build đạt. Ảnh: hộp thoại 640px căn giữa trên scrim; ở 1024×700 và 390×844
  thân cuộn, footer "Kiểm tra kết nối / Huỷ / Thêm vào kho" ở đáy. `scrollWidth` bằng viewport ở cả năm ảnh.
- Trạng thái: `passed`.
- Bằng chứng: ảnh `after2/dlg-add-light.png`, `dlg-add-dark.png`, `dlg-add-1024-light.png`, `dlg-add-emb-light.png`,
  `dlg-add-mobile-light.png` (scratchpad phiên).

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy test đầu sau S-01/S-02 có 5 test cũ thất bại (`ModelsView` ×3, `SettingsView` ×1, `SettingsNav` ×1). Các
  test này dựa trên ô select, nút "Dùng mô hình này" và `.settings-kind-item` đã bỏ. S-03 viết lại, chạy lại đạt.
- Test trả focus ban đầu thất bại vì `dispatchEvent("click")` của jsdom không focus nút như trình duyệt. Test giờ focus
  nút trước khi bấm, chạy lại đạt.
- Ảnh 1024px lần đầu: chip "Chờ khởi động lại" xuống hai dòng và nhãn "Nhúng văn bản" bị cắt. Đã chuyển chip sang cạnh
  tên mô hình (`.mdl-kind-head`), chụp lại đạt. Nút "Dùng" ở hàng `.env` lệch cột so với các hàng khác; đã chừa chỗ
  58px, chụp lại thẳng cột.
- Chưa kiểm tra: backend thật (chỉ API giả lập), trình đọc màn hình thật, Safari (không focus nút khi bấm nên focus có
  thể không trả về nút Sửa).
- ESLint không chạy được vì repo không có cấu hình ESLint 9; không coi là đạt.

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-06 (AC-04 kiểm lại ở V-07 sau S-04).
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: bàn giao reviewer (self_review).
