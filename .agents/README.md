# Phối hợp công việc giữa các AI agents

Mỗi task là một mục tiêu chung; các agent nhận những nhiệm vụ riêng trong cùng task. Năm file Markdown lưu trạng thái để agent khác hoặc phiên làm việc sau có thể tiếp tục mà không cần toàn bộ lịch sử chat.

## Cấu trúc

```text
.agents/
  README.md
  tasks/
    _template/
      task.md
      plan.md
      implementation.md
      verification.md
      review.md
    <yyyy-mm-dd-ten-task>/
      task.md
      plan.md
      implementation.md
      verification.md
      review.md
```

- `task.md`: yêu cầu, phạm vi, coordinator, trạng thái chung và tiêu chí nghiệm thu có ID `AC-*`.
- `plan.md`: nhiệm vụ có ID `S-*`, người nhận, phạm vi file, phụ thuộc, hợp đồng dùng chung và thứ tự tích hợp.
- `implementation.md`: thay đổi thực tế, quyết định, trao đổi, blocker và thông tin bàn giao.
- `verification.md`: kiểm tra gắn với `AC-*`, lệnh/thao tác, kết quả thực tế, bằng chứng và kết luận.
- `review.md`: đánh giá thay đổi, nhận xét có ID `R-*`, mức độ ảnh hưởng, người xử lý, phản hồi và kết luận review trên bản cụ thể. Verification ghi kết quả kiểm tra; review đánh giá tính đúng đắn, phạm vi, khả năng bảo trì và rủi ro còn lại.

## Tạo task

Từ thư mục gốc repo, chọn ID duy nhất rồi sao chép mẫu bằng PowerShell:

```powershell
$taskId = '2026-10-11-ten-task'
$taskPath = Join-Path '.agents/tasks' $taskId
if (Test-Path -LiteralPath $taskPath) { throw "Task đã tồn tại: $taskPath" }
New-Item -ItemType Directory -Path $taskPath | Out-Null
Copy-Item -Path '.agents/tasks/_template/*.md' -Destination $taskPath
```

Điền các chỗ `<...>` trước khi triển khai. Chọn một coordinator chịu trách nhiệm trạng thái chung, phân công và tích hợp. Một agent có thể kiêm nhiều vai trò khi làm việc một mình.

## Nhận việc và triển khai

1. Đọc cả năm file, xác định đúng task và các thay đổi đã có trong working tree.
2. Coordinator ghi ID agent ổn định, nhiệm vụ, phạm vi file và phụ thuộc trong `plan.md` trước khi giao việc. Agent chỉ bắt đầu khi phụ thuộc đã sẵn sàng.
3. Ghi rõ hợp đồng API/schema hoặc file dùng chung trước khi các phần việc liên quan chạy song song. Mỗi file mã nguồn chỉ có một người sửa tại một thời điểm; chia theo thư mục chưa đủ nếu cùng chạm file chung.
4. Agent cập nhật sau mỗi mốc có ý nghĩa, khi phát hiện blocker, thay đổi quyết định hoặc trước khi kết thúc phiên. Thông báo cần ghi người gửi, người nhận, ID nhiệm vụ và hành động mong muốn.
5. Người nhận ghi phản hồi, tham chiếu ID thông báo, rồi cập nhật nhiệm vụ tương ứng. Đọc lại thông báo dành cho mình khi bắt đầu/tiếp tục công việc và trước khi bàn giao.
6. Coordinator tích hợp các phần theo thứ tự đã ghi. Verifier kiểm tra trạng thái sau tích hợp, liên kết bằng chứng với từng `AC-*`.
7. Reviewer đọc yêu cầu, diff và bằng chứng kiểm chứng, ghi nhận xét trong `review.md`. Agent phụ trách sửa các nhận xét bắt buộc; verifier chạy lại kiểm tra bị ảnh hưởng và reviewer xác nhận trên bản mới trước khi coordinator kết luận task.

## Quyền ghi và tránh xung đột

- Coordinator duy trì `task.md` và `plan.md`; agent khác gửi đề xuất cập nhật qua công cụ liên lạc đang có hoặc mục trao đổi trong `implementation.md`.
- Agent triển khai ghi các mục mang ID của mình trong `implementation.md`; verifier duy trì `verification.md`; reviewer duy trì `review.md` và xác nhận kết quả xử lý nhận xét. Phản hồi của người triển khai được reviewer tổng hợp theo lượt ghi tuần tự. Nếu nhiều verifier hoặc reviewer, chỉ định người tổng hợp cho từng file.
- Các phần trong cùng một file vẫn có thể xung đột. Coordinator phải bố trí lượt ghi tuần tự hoặc tổng hợp nội dung do agent gửi. Trước khi ghi, đọc lại bản mới nhất và sửa đúng mục; không thay toàn bộ file từ bản cũ. Không xem quy ước này là khóa file tự động.
- Nếu dùng các worktree/clone riêng, file không tự đồng bộ. Bàn giao kèm branch/commit/patch và nội dung nhật ký; coordinator tích hợp rồi thông báo bản mới cho các agent.
- Mỗi thông báo dùng ID duy nhất, ví dụ `MSG-agent-backend-001`. Giữ nội dung lịch sử, thêm phản hồi/thông báo mới; không xóa trao đổi để làm sạch nhật ký.
- Dùng thời gian ISO 8601 có múi giờ, ví dụ `2026-10-11T14:30:00+07:00`. Không bịa timestamp, commit, kết quả chạy hoặc số lượng test.

## Trạng thái và bàn giao

Task dùng `draft`, `ready`, `in_progress`, `blocked`, `in_review`, `done`, `cancelled`. Coordinator cập nhật trong `task.md`: `ready` khi đủ yêu cầu và phân công; `in_review` khi đã tích hợp và chờ kết luận kiểm chứng/review; `done` khi mọi tiêu chí bắt buộc đạt và review được chấp thuận. Khi kiểm chứng thất bại hoặc review yêu cầu sửa, quay lại `in_progress` để xử lý rồi kiểm tra/review lại.

Nhiệm vụ dùng `todo`, `in_progress`, `blocked`, `in_review`, `done`, `cancelled`. Chỉ người được giao hoặc coordinator cập nhật trạng thái nhiệm vụ đó. Nhiệm vụ bị chặn phải ghi nguyên nhân, người cần phản hồi và điều kiện tiếp tục. Một nhiệm vụ bị chặn không có nghĩa toàn bộ task bị chặn nếu phần khác vẫn làm được.

Mỗi lần bàn giao cần có: nhiệm vụ đã làm, file/commit/patch liên quan, giao diện hoặc quyết định ảnh hưởng agent khác, kiểm tra đã chạy và kết quả, phần chưa xong, người nhận và bước tiếp theo. Agent nhận việc chưa rõ phải ghi câu hỏi, không tự suy diễn hợp đồng còn thiếu.

`verification.md` dùng `not_run`, `passed`, `failed`, `blocked` cho từng phép kiểm tra. `not_run` không phải `passed`. Chỉ ghi `done` khi mọi `AC-*` bắt buộc có bằng chứng đạt, không còn blocker, không còn nhiệm vụ bắt buộc chưa hoàn tất và `review.md` có kết luận `approved` trên bản mới nhất. Nếu phạm vi thay đổi, coordinator cập nhật tiêu chí cùng lý do trước khi kết luận.

## Review và vòng sửa lỗi

- Coordinator chỉ định reviewer và phạm vi review trong `plan.md`. Khi chỉ có một agent, có thể tự review nhưng phải ghi rõ `self_review`; không mô tả là review độc lập.
- Trạng thái review dùng `pending`, `in_progress`, `changes_requested`, `blocked`, `approved`. Mặc định là `pending`; không có nhận xét chưa đồng nghĩa với đã được chấp thuận.
- Mỗi nhận xét `R-*` ghi vị trí, vấn đề, tác động, mức độ `critical`, `high`, `medium` hoặc `low`, có bắt buộc sửa hay không, người xử lý và cách xác nhận. `critical`/`high` luôn bắt buộc sửa trước khi hoàn tất.
- Nhận xét dùng `open`, `resolved`, `deferred`. Agent triển khai ghi cách sửa và bằng chứng; reviewer xác nhận rồi chuyển sang `resolved`. Chỉ dùng `deferred` cho nhận xét không bắt buộc, có lý do và hướng theo dõi tiếp; coordinator ghi nhận quyết định.
- `approved` yêu cầu đã đọc bản được bàn giao, đối chiếu bằng chứng kiểm chứng và không còn nhận xét bắt buộc chưa xử lý. Nếu thay đổi nội dung cần đánh giá sau review, cập nhật bản tham chiếu, đưa review về `pending` và review lại phần bị ảnh hưởng; giữ lịch sử vòng trước. Việc ghi kết luận và đóng trạng thái task không tự làm mất hiệu lực review.

Các file là kênh trao đổi bất đồng bộ; agent phải chủ động đọc hoặc được công cụ điều phối thông báo. Có thể lưu `.agents` cùng mã nguồn trong Git để giữ lịch sử và chia sẻ giữa các phiên.
