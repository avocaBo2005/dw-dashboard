# Kế hoạch đánh giá

Trang `Evaluation` tự động chạy các kiểm tra dưới đây và đo thời gian phản hồi
từng endpoint.

## Độ đúng

- API health và database health trả `ok`.
- Sales OLAP trả ít nhất một order.
- `delivery.grand_total.eligible_orders` bằng `distribution.meta.total`.
- Đối soát mốc ETL hiện tại:
  - eligible orders: `96,470`;
  - late orders: `6,534`;
  - late rate: `6.77%`.
- Review `group=flag` trả đủ `late` và `not_late`.
- DSS config có trọng số hợp lệ và seller scorecard trả dữ liệu.

Nếu dữ liệu hoặc ETL thay đổi, mốc tham chiếu phải được cập nhật thay vì sửa
dashboard để ép kết quả.

## Hiệu năng

- Ghi nhận thời gian phản hồi của health, sales, delivery, distribution, review và DSS.
- Phân loại: tốt `<= 500 ms`, chấp nhận `<= 1.5 s`, trên `1.5 s` cần tối ưu.
- Dùng `EXPLAIN (ANALYZE, BUFFERS)` tại backend cho endpoint chậm.
- Cache UI có TTL 5 phút; trang Evaluation cố ý gọi không cache để đo API thật.

## Tính hữu ích

- Demo roll-up/drill-down sales theo thời gian và seller geography.
- Xác định customer state có tỷ lệ giao trễ cao với volume đủ lớn.
- So sánh review của order trễ và không trễ.
- DSS đưa ra scorecard seller có giải thích trọng số, rule, danh sách hành động và
  file CSV tải xuống; kết quả không khẳng định nhân quả.

## Hạn chế

- Order status là snapshot và ETL đang full refresh.
- Chưa có payments, geolocation, SCD hoặc incremental load.
- Không thể quy trách nhiệm giao trễ về seller từ mô hình V1.
- Dữ liệu Olist là dữ liệu lịch sử, không phải dữ liệu vận hành hiện tại.
