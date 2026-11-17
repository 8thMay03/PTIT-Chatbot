# Review: 2026-11-15-settings-nav-retrieval-test

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (chỉ một agent trong phiên; vòng 3 do phiên mới thực hiện,
  không dựa vào kết luận các vòng trước).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/settings-nav-retrieval-test`, working tree trên `f69d4a0` có
  bản sửa R-03/R-04/R-06 chưa commit (mã nguồn gốc như `7e38924`; tách từ `dev` `08f90bb`).
- Cập nhật lúc: `2026-11-17T21:27:01+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01` … `AC-07`; `S-01` … `S-05`.
- File/thay đổi đã đọc: toàn bộ diff `dev..7e38924` (backend config store/route/schema
  và test; route/SettingsView/SettingsNav/ConfigView/ModelsView/RetrievalTestPanel/
  gateDecision/retrieval API/CSS và test; ảnh chụp).
- Bằng chứng kiểm chứng: `verification.md` V-01 … V-07, gồm test tự động, đo Chromium
  và ảnh 1366/1024/390 sáng/tối.
- Điểm đánh giá: tương thích hash cũ; không trộn hai kiểu lưu; luật gate frontend khớp
  backend; huỷ request; a11y danh mục/drawer; bundle trang chat; nguồn `updated_at` khi
  xoá dòng/reset; giữ bản nháp khi đổi mục.

## Nhận xét

### R-01 — Luật gate phía client là bản sao có chủ đích

- Vị trí: `frontend/src/lib/gateDecision.js`.
- Vấn đề: luật AND và thứ tự lý do được sao chép từ
  `backend/app/generation/confidence.py`; nếu backend đổi luật mà frontend không đổi,
  kết luận "Bản nháp" sẽ lệch.
- Tác động: chỉ ảnh hưởng phần so ngưỡng nháp, không ảnh hưởng câu trả lời thật.
- Mức độ: `low`; bắt buộc sửa: không.
- Cách giảm thiểu đã có: comment chéo tới file backend, bộ ca `gateDecision.test.js`
  chép từ `test_retrieval_confidence.py`, và verification chạy cả hai bộ.
- Trạng thái: `deferred` — nếu luật gate thay đổi thường xuyên, chuyển phần tính bản
  nháp sang backend (đã ghi trong rủi ro của `plan.md`).

### R-02 — Ảnh chụp dùng API giả lập

- Vị trí: `docs/design/assets/settings-nav-retrieval-test/`.
- Vấn đề: Chromium chặn `/api/**` bằng dữ liệu giả thay vì chạy pipeline thật.
- Tác động: ảnh chứng minh bố cục, trạng thái và tương tác, không chứng minh chất lượng
  truy xuất thật.
- Mức độ: `low`; bắt buộc sửa: không.
- Trạng thái: `deferred` — cùng cách làm của task `settings-gate-savebar`; kiểm tra
  truy xuất thật cần môi trường có dữ liệu/embedding và tốn chi phí.

### R-03 — Bấm mục trong danh mục không cuộn khi route không đổi

- Vị trí: `frontend/src/ConfigView.jsx:143-149` (effect cuộn phụ thuộc
  `[activeSection, loading]`), `frontend/src/SettingsView.jsx` (`activeSection={section ?? "retrieval"}`),
  `frontend/src/admin/AdminShell.jsx` (`openSettingsSection`).
- Vấn đề: chỉ cuộn khi giá trị `activeSection` đổi. Hai trường hợp bấm mục mà không cuộn:
  - Đang ở `#settings` (vào từ thanh bên luôn mở `section: null`), cuộn xuống rồi bấm "Truy
    xuất": `section` đổi `null` → `retrieval` nhưng `activeSection` vẫn là `"retrieval"`.
  - Đang ở `#settings/<key>`, cuộn sang mục khác (scrollspy đã đổi `aria-current`) rồi bấm lại
    đúng mục `<key>`.
  - Cả hai trường hợp vẫn `pushState` một mục lịch sử trùng hash, nên Back phải bấm nhiều lần.
- Bằng chứng: test tạm (đã xoá) render `SettingsView` với `section` lần lượt `null` →
  `retrieval` → `gate` → `gate`, theo dõi `Element.prototype.scrollIntoView`. Kết quả:
  `["settings-section-retrieval" (lúc mount), "settings-section-gate"]`. Không có lần cuộn nào
  cho `null → retrieval` và `gate → gate`.
- Tác động: trái `AC-01` ("bấm mục thì cuộn tới anchor"). Lỗi gặp ở đường vào phổ biến nhất
  (thanh bên → Settings).
- Mức độ: `medium`; bắt buộc sửa: có (lệch tiêu chí nghiệm thu).
- Hướng sửa gợi ý: cuộn theo yêu cầu thay vì theo giá trị. Ví dụ `SettingsView` tăng một bộ
  đếm `scrollRequest` mỗi lần `handleSelect` gọi cho mục anchor rồi truyền xuống `ConfigView`;
  `openSettingsSection` bỏ qua `pushState` khi hash không đổi. Thêm test cho hai trường hợp trên.
- Người xử lý: `claude-agent`. Xác nhận: test component mới và kiểm tra lại trong Chromium.
- Phản hồi (`2026-11-17T21:22:14+07:00`, `claude-agent`): sửa theo hướng gợi ý; chi tiết trong
  `implementation.md` ("Sửa sau review vòng 3"). Hai test mới thất bại trên mã cũ và đạt sau
  khi sửa. Chromium xác nhận bấm "Truy xuất" từ `#settings` và bấm lại cùng mục đều cuộn về
  đầu, không thêm lịch sử (`verification.md` V-01).
- Trạng thái: `resolved` — reviewer xác nhận ở vòng 4.

### R-04 — Scrollspy ghi đè mục vừa bấm ở cuối form

- Vị trí: `frontend/src/ConfigView.jsx:153-175` (`rootMargin: "-12% 0px -70% 0px"`).
- Vấn đề: bấm "Sinh câu trả lời" (mục cuối). Nếu form không đủ dài để đưa mục này lên dải
  12–30% trên cùng của khung cuộn, observer sẽ chọn mục đầu tiên còn nằm trong dải (ví dụ
  "Ngưỡng tin cậy"). Khi đó `aria-current` lệch với hash `#settings/generation`.
- Bằng chứng: lúc mở nhận xét chỉ suy ra từ mã. Đã tái hiện ở vòng 4 (Chromium 1366×820,
  `verification.md` V-01): bấm "Sinh câu trả lời" → hash `#settings/generation` nhưng
  `aria-current` ở "Ngưỡng tin cậy".
- Mức độ: `medium` (nâng từ `low` sau khi tái hiện); bắt buộc sửa: có. Lý do: lệch `AC-01`
  (mục đang xem phải được đánh dấu bằng `aria-current`), và trình đọc màn hình báo sai mục.
- Hướng sửa gợi ý: khi cuộn tới cuối khung (`scrollTop + clientHeight >= scrollHeight - 1`)
  thì chọn mục cuối; hoặc tạm khoá scrollspy trong lúc cuộn do người dùng bấm.
- Phản hồi (`2026-11-17T21:27:01+07:00`, `claude-agent`): theo hướng thứ nhất. Thay `IntersectionObserver` bằng
  hàm thuần `pickActiveSection` (`settings/scrollSpy.js`, có test), chạy theo sự kiện cuộn; chi tiết
  trong `implementation.md` ("Sửa sau review vòng 4"). Chromium: bốn mục đều đánh dấu đúng khi
  bấm; cuộn tay theo đúng thứ tự (`verification.md` V-01).
- Trạng thái: `resolved` — reviewer xác nhận ở vòng 5.

### R-05 — Drawer giữ trạng thái mở khi nới rộng lên ≥1280px

- Vị trí: `frontend/src/settings/RetrievalTestPanel.jsx` (effect focus trap phụ thuộc `open`),
  `frontend/src/SettingsView.jsx` (`testOpen`).
- Vấn đề: mở drawer ở chiều rộng dưới 1280px rồi nới cửa sổ lên ≥1280px. `open` vẫn là `true`,
  nên cột phải mang `role="dialog"`/`aria-modal="true"`, phím Tab bị giữ trong cột và Esc bị
  chặn ở capture phase. Scrim và nút đóng bị CSS ẩn, nên người dùng không thấy đang ở chế độ
  modal.
- Mức độ: `low`; bắt buộc sửa: không.
- Hướng sửa gợi ý: dùng `matchMedia("(min-width: 1280px)")` để tự đóng drawer khi vượt mốc,
  hoặc chỉ gắn trap/role khi đang ở chế độ drawer.
- Trạng thái: `open`.

### R-06 — Ghi chú cuối bảng thử mâu thuẫn về Top-K

- Vị trí: `frontend/src/settings/RetrievalTestPanel.jsx`, đoạn ghi chú cuối kết quả.
- Vấn đề: ghi chú nói "thay đổi Top-K, tỷ trọng hay xếp hạng lại cần lưu rồi chạy lại". Thực tế
  request gửi `top_k` lấy từ bản nháp (comment `NEEDS_SAVED_RUN_KEYS` và AC-04 cũng nói vậy).
  Ngoài ra comment `DEFAULT_GATE_THRESHOLDS` trong `lib/gateDecision.js` ghi "mọi tín hiệu bật"
  trong khi vector và rerank là `null`.
- Mức độ: `low`; bắt buộc sửa: không (nên sửa cùng R-03 vì sửa nhanh).
- Phản hồi (`2026-11-17T21:22:14+07:00`, `claude-agent`): sửa cả hai ghi chú trong bảng thử ("riêng Top-K
  lấy theo bản nháp"; danh sách cần lưu là tỷ trọng, mở rộng câu hỏi, xếp hạng lại) và comment
  `DEFAULT_GATE_THRESHOLDS`.
- Trạng thái: `resolved` — reviewer đã đọc lại diff ở vòng 4.

### R-07 — "Lần lưu gần nhất" còn đổi theo thao tác ở mục Mô hình

- Vị trí: `backend/app/core/config_store.py` (`save_overrides` luôn ghi `SAVED_AT_KEY`);
  `backend/app/core/model_profiles.py:384-431` (dùng chung `settings_transaction`).
- Vấn đề: chọn, sửa hoặc xoá profile mô hình cũng cập nhật mốc. Mốc này lại chỉ hiện ở header
  nhóm "Hệ thống trả lời". Quản trị viên có thể hiểu nhầm là form RAG vừa được lưu.
- Tác động: chỉ là cách hiện thông tin; dữ liệu không sai nếu hiểu mốc là "lần đổi cấu hình
  gần nhất".
- Mức độ: `low`; bắt buộc sửa: không. Cần người dùng quyết định: giữ nghĩa "mọi thay đổi cấu
  hình" và đổi nhãn/hiện cả ở mục Mô hình, hay chỉ ghi mốc trong `apply_config_update` và
  `reset_config`.
- Trạng thái: `open`.

### R-08 — Trang mục trên mobile là cả form cuộn tới anchor

- Vị trí: `frontend/src/SettingsView.jsx`, `frontend/src/styles/config.css` (`@media (max-width: 1023px)`).
- Vấn đề: dưới 1024px, chọn "Ngưỡng tin cậy" mở cả form "Hệ thống trả lời" rồi cuộn tới
  anchor, không phải trang chỉ có mục đó. Cách này vẫn đạt chữ của AC-01 (có nút quay lại, Back
  hoạt động) và giữ một thanh lưu. Tuy vậy tiêu đề trang vẫn là "Hệ thống trả lời", không phải
  tên mục đã chọn.
- Mức độ: `low`; bắt buộc sửa: không. Ghi lại để người dùng xác nhận đây là hành vi mong muốn.
- Trạng thái: `open`.

## Lịch sử các vòng review

- `2026-11-17T21:11:00+07:00` — vòng 1, `self_review` trên bản `7e38867` (nay là
  `7e38924` sau khi thêm dấu "—"): đối chiếu `AC-01` … `AC-07`, đọc diff và bằng chứng;
  không có nhận xét bắt buộc. Kết luận `approved`.
- `2026-11-17T21:13:30+07:00` — vòng 2, `self_review` trên `7e38924`: chỉ thêm dấu
  "—" giữa tên mô hình và link "Đổi mô hình →" cho đúng AC-03; đọc lại dòng mô hình,
  chạy lại `npm test`/`npm run build`/`npm run check:bundle` (đều đạt), không phát sinh
  nhận xét. Giữ kết luận `approved`.
- `2026-11-17T21:18:04+07:00` — vòng 3, `self_review` của một phiên mới trên `f69d4a0`:
  - Đọc lại toàn bộ diff `dev..f69d4a0`. Đối chiếu `gateDecision.js` với `assess_context`/
    `thresholds_from_settings` trong `confidence.py`: khớp.
  - Chạy lại `npx vitest run` (42 file, 343/343 passed) và `pytest` cho `test_config_api.py`,
    `test_config_persistence.py`, `test_model_profiles.py`, `test_retrieval_confidence.py`
    (82 passed).
  - Tái hiện R-03 bằng test tạm, đã xoá sau khi chạy.
  - Phát sinh R-03 (`medium`, bắt buộc) và R-04 … R-08 (`low`). Chuyển `approved` →
    `changes_requested`.
- `2026-11-17T21:22:14+07:00` — vòng 4, `self_review` trên working tree có bản sửa R-03/R-06:
  - Đọc diff sửa (`SettingsView.jsx`, `ConfigView.jsx`, `AdminShell.jsx`, `RetrievalTestPanel.jsx`,
    `gateDecision.js`, hai file test).
  - Đối chiếu `verification.md` V-01/V-07: 345/345 test, build, bundle đạt; Chromium xác nhận R-03.
  - R-03, R-06 → `resolved`.
  - Chromium tái hiện R-04, nâng lên `medium`, bắt buộc. Giữ `changes_requested`.
- `2026-11-17T21:27:01+07:00` — vòng 5, `self_review` trên working tree có bản sửa R-03/R-04/R-06:
  - Đọc `settings/scrollSpy.js`, test của nó và effect scrollspy mới trong `ConfigView.jsx`.
    Listener được gỡ khi unmount hoặc đổi `loading`, và frame đang chờ được huỷ.
  - Đối chiếu V-01 (Chromium: bốn mục bấm và cuộn tay đều đúng) và V-07 (350/350, build, bundle).
  - R-04 → `resolved`. Không còn nhận xét bắt buộc. Kết luận `approved`.

## Kết luận

- Kết luận: `approved` (vòng 5, `self_review`, working tree trên `f69d4a0` + bản sửa chưa commit).
- Nhận xét bắt buộc còn mở: không.
- Nhận xét đã xử lý: `R-03`, `R-04`, `R-06`.
- Nhận xét không bắt buộc còn mở: `R-05`, `R-07`, `R-08`. `R-07` và `R-08` cần người dùng quyết định.
- Nhận xét hoãn lại: `R-01`, `R-02` (không bắt buộc, đã có hướng theo dõi).
- Phần chưa review / giới hạn: không chạy `POST /retrieval/test` với backend thật và dữ
  liệu thật; không kiểm tra trình duyệt ngoài Chromium.
- Bước tiếp theo: commit bản sửa khi người dùng yêu cầu. Nếu commit chỉ gồm đúng các file đã
  review thì giữ `approved`, chỉ cập nhật mã commit.
