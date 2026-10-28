# Task: Animation sống động cho trang landing theo phong cách eduardbodak.com

- ID: `2026-10-28-landing-motion`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng (yêu cầu trực tiếp trong phiên chat)
- Tạo lúc: `2026-10-28T20:48:26+07:00`
- Cập nhật lúc: `2026-10-28T21:07:39+07:00`

## Yêu cầu và kết quả mong muốn

Người dùng muốn trang landing (`/`, task `2026-10-28-landing-figma-redesign`) có animation sống động giống
<https://www.eduardbodak.com/?ref=landing.love>.

Hiện trạng: landing gần như tĩnh — chỉ có transition hover nhẹ cho nút/chip và icon FAQ xoay.

Trang tham chiếu và bài phân tích của tác giả trên Codrops bị chặn mạng trong phiên này (`getaddrinfo
ENOTFOUND`), nên bộ hiệu ứng dựa trên mô tả công khai tìm được qua tìm kiếm: trang làm bằng Webflow + GSAP với
Locomotive Scroll; hiệu ứng chính gồm thẻ lật 3D khi cuộn, thẻ tương tác nghiêng theo chuột, bố cục thẻ vòng
tròn xoay theo cuộn, micro-animation thanh điều hướng, pulse khi click, pixel transition giữa các trang.

Kết quả cần có — áp dụng ngôn ngữ chuyển động đó lên nội dung landing hiện có (không đổi nội dung):

1. Intro: tiêu đề hero hiện theo từng từ trượt lên từ mặt nạ, các khối hero xuất hiện so le.
2. Tiêu đề section lộ theo từ khi cuộn tới; khối nội dung fade-up so le.
3. Thẻ bento lật 3D theo tiến độ cuộn khi vào khung nhìn; nghiêng theo chuột kèm vệt sáng (glare).
4. Vòng thẻ chủ đề 3D xoay theo cuộn ở dải kêu gọi hành động.
5. Dải chủ đề chạy marquee vô hạn; nền chữ mờ "tô sáng" theo từ khi cuộn.
6. Thanh điều hướng dính, thu gọn khi cuộn, ẩn khi cuộn xuống/hiện khi cuộn lên; link nav cuộn chữ khi hover.
7. Nút chính hút theo chuột (magnetic) và pulse khi click.
8. Pixel transition phủ màn hình khi chuyển từ landing sang `/chat`, `/login`, `/register`.
9. Parallax: lớp haze và hai thẻ nghiêng ở hero trôi theo cuộn/chuột.

## Phạm vi

- Bao gồm: `frontend/src/landing/*` (thêm module chuyển động), `frontend/src/styles/landing.css` (hoặc file CSS
  motion mới import từ `index.css`), test landing.
- Ngoài phạm vi: nội dung chữ, màn chat/admin/auth, backend, smooth-scroll chiếm quyền cuộn (Lenis/Locomotive)
  — làm hỏng cuộn bằng bàn phím/trình đọc màn hình và tìm kiếm trong trang; con trỏ chuột tuỳ biến.
- Ràng buộc:
  - Không thêm thư viện animation (giữ D-09 task `landing-user-auth`, giới hạn bundle landing); tự viết bằng
    IntersectionObserver, `requestAnimationFrame`, biến CSS.
  - `prefers-reduced-motion: reduce` → tắt mọi chuyển động (nội dung hiện ngay, điều hướng không chờ hiệu ứng).
  - Không có JS / không có IntersectionObserver (jsdom) → nội dung vẫn hiển thị đầy đủ.
  - Giữ AC của các task landing trước: landmark, một `h1`, text heading không đổi, sáng/tối, 360/768/1280 px
    không cuộn ngang, bàn phím dùng được, landing không tải module chat/admin.
  - Ctrl/⌘/Shift/chuột giữa trên link vẫn mở tab mới như thường (pixel transition không chặn).

## Tiêu chí nghiệm thu

- [x] AC-01: Có đủ 9 nhóm hiệu ứng ở mục "Kết quả cần có", quan sát được trên trình duyệt thật (ảnh chụp các
  khung hình giữa chuyển động ở 1280 px).
- [x] AC-02: `prefers-reduced-motion: reduce` → không có transform/animation chạy; nội dung hiển thị ngay; bấm
  CTA chuyển trang ngay (kiểm bằng Playwright emulate reduced motion + test).
- [x] AC-03: Không IntersectionObserver/JS motion → mọi phần tử `data-reveal` vẫn hiện (test jsdom); text của
  `h1`/`h2` không đổi so với trước (test sẵn có giữ nguyên kỳ vọng).
- [x] AC-04: Pixel transition chỉ chặn click chuột trái không phím bổ trợ trên link nội bộ; sau khi Back từ
  trang chat (bfcache) lớp phủ không còn che landing.
- [x] AC-05: 360/768/1280 px sáng/tối không cuộn ngang; nav dính không che tiêu đề section khi bấm link neo.
- [x] AC-06: `npm test`, `npm run build`, `npm run check:bundle` đạt; ghi kích thước gzip landing trước/sau.

## Tài liệu và phụ thuộc

- Task trước: `.agents/tasks/2026-10-28-landing-figma-redesign/` (`done`, đã merge `dev` qua PR #45).
- Tham khảo: <https://www.awwwards.com/eduardbodak/>, danh sách hiệu ứng trên Awwwards và bài Codrops
  "Built to Move: A Closer Look at the Animations Behind Eduard Bodak's Portfolio" (chỉ đọc được tóm tắt).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: `done` — S-01 … S-04 xong, V-01 … V-06 `passed`, review `self_review` `approved` (R-03, R-04 deferred).
- Blocker: không.
- Bước tiếp theo: người dùng xem landing; cho phép tên miền tham chiếu trong cài đặt mạng nếu muốn đối chiếu kỹ hơn.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-28T20:48:26+07:00` — `claude-agent`: tạo task từ yêu cầu người dùng, chuyển thẳng `in_progress` vì
  người dùng yêu cầu "lập kế hoạch và thực hiện".
- `2026-10-28T21:07:39+07:00` — `claude-agent`: hoàn tất, chuyển `done`. Thay chữ nền ở dải kêu gọi bằng vòng chủ đề
  3D (ghi ở S-02 trong `implementation.md`).
