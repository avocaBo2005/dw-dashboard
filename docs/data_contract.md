# Backend API contract

UI sử dụng base URL trong `API_BASE_URL`, mặc định `http://localhost:3000`.

| Endpoint | Mục đích |
| --- | --- |
| `GET /api/v1/health` | Trạng thái API |
| `GET /api/v1/db-health` | Trạng thái PostgreSQL |
| `GET /api/v1/sale/analysis` | Sales OLAP |
| `GET /api/v1/delivery/analysis` | Delivery OLAP |
| `GET /api/v1/delivery/distribution` | Phân phối `delay_days` |
| `GET /api/v1/reviews/by-delay` | Review theo bucket/flag độ trễ |
| `GET /api/v1/dss/config` | Trọng số, rule và setting của knowledge base |
| `GET /api/v1/dss/seller-scorecard` | Xếp hạng và khuyến nghị seller |

## Sales

Hierarchy:

- `time`: `year -> quarter -> month`
- `seller_geo`: `seller_state -> seller_city`
- `product`: `category -> product`

Measures: `total_price`, `total_freight`, `n_orders`, `n_items`.

## Delivery

Hierarchy:

- `time`: `year -> quarter -> month`
- `customer_geo`: `customer_state -> customer_city`

Measures: `eligible_orders`, `late_orders`, `late_rate`,
`avg_delivery_days`, `avg_delay_days`.

Delivery API luôn giới hạn trên các order đủ điều kiện. `late_rate` là phần trăm.

## Review

`group=bucket` trả sáu nhóm từ `early_8plus` đến `late_8plus`.
`group=flag` trả `not_late` và `late`. `low_review_rate` và `p0` nằm trong
khoảng 0–1.

## Grain và diễn giải

- Sales: một order item; `n_orders` phải distinct.
- Delivery: một order.
- Review API tổng hợp review về order trước khi nối delivery.
- Không cộng các subtotal trả về bởi `ROLLUP`; record `level=0` là grand total.
- Không dùng delivery measures để xếp hạng seller.

## DSS seller scorecard

- Tiêu chí: `gmv` (higher), `late_rate` (lower), `low_review_rate` (lower).
- Seller chỉ được chấm điểm khi đạt `min_eligible_orders`; seller còn lại được gắn
  nhãn thiếu dữ liệu thay vì suy diễn từ mẫu nhỏ.
- `late_rate` và `low_review_rate` của scorecard là tỷ lệ 0–1; UI nhân 100 để hiển thị.
- Backend chuẩn hóa tổng trọng số trước khi tính điểm. UI có thể truyền override theo
  dạng `weights=gmv:0.3,late_rate:0.35,low_review_rate:0.35`.
- Scorecard chỉ dùng order có đúng một seller để bảo toàn grain khi nối sales,
  delivery và review.

