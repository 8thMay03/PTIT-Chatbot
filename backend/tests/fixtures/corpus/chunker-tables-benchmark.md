# Báo cáo vận hành thử nghiệm chunker

Tài liệu tổng hợp dùng làm chuẩn so sánh (benchmark) cho việc chia khối (chunking)
các tài liệu nhiều bảng. Dữ liệu bên dưới là dữ liệu giả lập, không phải dữ liệu thật.

## Sổ giao dịch mô phỏng

Bảng giao dịch dài dưới đây dùng để kiểm tra việc lặp lại dòng tiêu đề khi bảng
bị chia thành nhiều khối.

| Mã Giao Dịch | Ngày | Loại giao dịch | Số tiền |
| --- | --- | --- | --- |
| TX-2026-001 | 02/01/2026 | Nạp tiền ban đầu | 5.000.000 |
| TX-2026-002 | 05/01/2026 | Thanh toán học phí | 12.500.000 |
| TX-2026-003 | 09/01/2026 | Hoàn trả chi phí | 750.000 |
| TX-2026-004 | 12/01/2026 | Nạp tiền bổ sung | 3.000.000 |
| TX-2026-005 | 16/01/2026 | Thanh toán dịch vụ | 1.250.000 |
| TX-2026-006 | 20/01/2026 | Nạp tiền bổ sung | 2.500.000 |
| TX-2026-007 | 23/01/2026 | Trả lại nhầm lẫn | 900.000 |
| TX-2026-008 | 27/01/2026 | Thanh toán ký túc xá | 4.800.000 |
| TX-2026-009 | 02/02/2026 | Nạp tiền bổ sung | 6.000.000 |
| TX-2026-010 | 06/02/2026 | Mua tài liệu học tập | 320.000 |
| TX-2026-011 | 10/02/2026 | Thanh toán phòng máy | 1.100.000 |
| TX-2026-012 | 14/02/2026 | Hoàn tiền hủy lịch | 450.000 |
| TX-2026-013 | 18/02/2026 | Nạp tiền bổ sung | 7.250.000 |
| TX-2026-014 | 22/02/2026 | Thanh toán chuyển phát | 180.000 |
| TX-2026-015 | 26/02/2026 | Đóng bảo hiểm y tế | 890.000 |
| TX-2026-016 | 02/03/2026 | Nạp tiền bổ sung | 4.400.000 |
| TX-2026-017 | 06/03/2026 | Thanh toán thi lại | 220.000 |
| TX-2026-018 | 10/03/2026 | Trợ cấp nghiên cứu | 9.000.000 |
| TX-2026-019 | 14/03/2026 | Nạp tiền bổ sung | 1.750.000 |
| TX-2026-020 | 18/03/2026 | Đối soát cuối kỳ | 0 |

## Danh mục tài khoản mô phỏng

Bảng tài khoản dùng để kiểm tra việc giữ tiêu đề bảng markdown trong các khối con.

| Mã Tài Khoản | Vai trò | Khu vực | Trạng thái |
| --- | --- | --- | --- |
| USR-QT-001 | Quản trị | Trung tâm dữ liệu | Kích hoạt |
| USR-QT-002 | Quản trị | Trung tâm dữ liệu | Kích hoạt |
| USR-KS-003 | Kiểm soát | Phòng vận hành | Kích hoạt |
| USR-KS-004 | Kiểm soát | Phòng vận hành | Tạm dừng |
| USR-KT-005 | Kỹ thuật | Phòng kỹ thuật | Kích hoạt |
| USR-KT-006 | Kỹ thuật | Phòng kỹ thuật | Kích hoạt |
| USR-TS-007 | Thực tập sinh | Phòng kỹ thuật | Kích hoạt |
| USR-TS-008 | Thực tập sinh | Phòng vận hành | Tạm dừng |

## Nhật ký chuyển tiếp mô phỏng

Bảng nhật ký dùng để kiểm tra thêm một biến thể bảng markdown khác.

| Mã Bản Ghi | Thời điểm | Kênh | Kết quả |
| --- | --- | --- | --- |
| FTR-LOG-0001 | 08:00:01 | Cổng API | Thành công |
| FTR-LOG-0002 | 08:05:14 | Cổng API | Thành công |
| FTR-LOG-0003 | 08:11:37 | Hàng đợi | Thử lại |
| FTR-LOG-0004 | 08:17:52 | Hàng đợi | Thành công |
| FTR-LOG-0005 | 08:23:09 | Đồng bộ | Thành công |
| FTR-LOG-0006 | 08:29:41 | Đồng bộ | Lỗi tạm thời |
| FTR-LOG-0007 | 08:35:20 | Cổng API | Thành công |
| FTR-LOG-0008 | 08:41:58 | Hàng đợi | Thành công |

## Bảng HTML tổng hợp

Bảng HTML dưới đây dùng để kiểm tra việc giữ nguyên cấu trúc thẻ khi bảng bị chia.

<table>
  <thead>
    <tr>
      <th>Mã Báo Cáo</th>
      <th>Kỳ</th>
      <th>Chỉ Tiêu</th>
      <th>Giá Trị</th>
    </tr>
  </thead>
  <tbody>
    <tr><td>RPT-2026-001</td><td>Tháng 01</td><td>Số giao dịch</td><td>20</td></tr>
    <tr><td>RPT-2026-002</td><td>Tháng 01</td><td>Tỷ lệ thành công</td><td>98,5%</td></tr>
    <tr><td>RPT-2026-003</td><td>Tháng 01</td><td>Thời gian phản hồi trung bình</td><td>210 ms</td></tr>
    <tr><td>RPT-2026-004</td><td>Tháng 02</td><td>Số giao dịch</td><td>18</td></tr>
    <tr><td>RPT-2026-005</td><td>Tháng 02</td><td>Tỷ lệ thành công</td><td>99,1%</td></tr>
    <tr><td>RPT-2026-006</td><td>Tháng 02</td><td>Thời gian phản hồi trung bình</td><td>195 ms</td></tr>
    <tr><td>RPT-2026-007</td><td>Tháng 03</td><td>Số giao dịch</td><td>22</td></tr>
    <tr><td>RPT-2026-008</td><td>Tháng 03</td><td>Tỷ lệ thành công</td><td>97,8%</td></tr>
    <tr><td>RPT-2026-009</td><td>Tháng 03</td><td>Thời gian phản hồi trung bình</td><td>240 ms</td></tr>
    <tr><td>RPT-2026-010</td><td>Quý 1</td><td>Tổng giao dịch</td><td>60</td></tr>
  </tbody>
</table>

## Kết luận

Các bảng trên đủ dài để cơ chế chia khối phải tách thành nhiều mảnh và lặp lại
dòng tiêu đề, đồng thời giữ nguyên cấu trúc cây tiêu đề cho khối cha – khối con.
