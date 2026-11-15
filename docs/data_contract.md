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
| `GET /api/v1/meta/pivot` | Danh sách chiều và độ đo được phép dùng cho Pivot |
| `GET /api/v1/sale/pivot` | Ma trận Pivot bán hàng |
| `GET /api/v1/delivery/pivot` | Ma trận Pivot giao hàng |
| `GET /api/v1/dss/delivery-buffer` | Chính sách buffer giao hàng tổng quan hoặc theo bang |
| `GET /api/v1/dss/delivery-buffer/tradeoff` | Đánh đổi giữa tỷ lệ trễ và ngày cam kết |

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

## Pivot

- `rows` và `cols` là bắt buộc, phải khác nhau và thuộc whitelist của cube.
- `measure` mặc định là `total_price` cho Sales và `late_rate` cho Delivery.
- Response gồm `row_headers`, `col_headers`, `matrix`, tổng hàng/cột và `grand_total`.
- `meta.truncated` cho biết kết quả có bị giới hạn bởi `max_rows` hoặc `max_cols`.
- Dashboard dùng metadata để tạo bộ chọn chiều/độ đo, hiển thị heatmap, ma trận và
  cho tải CSV. Tổng hàng/cột lấy trực tiếp từ response, không cộng lại các ô bị cắt.
- Riêng `late_rate` của Pivot có unit `ratio` và nằm trong khoảng 0–1; UI nhân 100
  để hiển thị. `late_rate` của Delivery Analysis cũ là phần trăm.

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

## DSS Delivery Buffer

- Query tổng quan hỗ trợ `target_late_rate`, `k_min`, `k_max` và `run_id`.
- Thêm `state=SP` (hoặc mã bang khác) để lấy đường cong và recommendation của
  một bang.
- Tổng quan trả ba chính sách: `current_k0`, `global_k`, `state_k` cùng bảng đánh
  giá theo bang.
- Các trường `late_rate`, `pct_orders_in_met`, `ci_low`, `ci_high` là tỷ lệ 0–1;
  UI nhân 100 để hiển thị.
- `fallback=true` nghĩa là bang chưa đủ điều kiện học riêng và dùng mô hình chung.
- `status` có thể là `met`, `missed` hoặc `low_power`; `low_power` không nên được
  diễn giải như đã đạt mục tiêu.
- API trả `404` nếu chưa có active policy run hoặc không tìm thấy bang/run yêu cầu.
- Trade-off chỉ có ý nghĩa biểu đồ khi pipeline đã build ít nhất hai safety margin.

