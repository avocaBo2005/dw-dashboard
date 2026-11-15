# Olist Data Warehouse Dashboard

Streamlit dashboard cho bài tập lớn CO4031. Repo UI gọi OLAP API trong repo
backend; UI không đọc CSV và không kết nối PostgreSQL trực tiếp.

## Chức năng

- Tổng quan KPI sales, delivery và review.
- OLAP sales theo hierarchy thời gian, seller geography và product.
- Delivery OLAP theo thời gian và customer geography.
- Pivot tùy biến cho Sales và Delivery với heatmap, ma trận tổng hợp và xuất CSV.
- Phân phối giao sớm/đúng hạn/trễ và review theo độ trễ.
- DSS scorecard xếp hạng seller bằng trọng số/rule cấu hình ở backend, hỗ trợ mô phỏng
  trọng số và xuất danh sách hành động CSV.
- Delivery Buffer so sánh hiện trạng, buffer chung và buffer theo bang, hiển thị
  khoảng tin cậy, đường cong chính sách và trade-off safety margin.
- Trang đánh giá end-to-end API, database, OLAP và DSS; đối soát KPI, phân loại thời
  gian phản hồi và xuất kết quả CSV.

## Kiến trúc

```text
DW_ETL/PostgreSQL -> Express TypeScript API :3000 -> Streamlit UI :8501
```

Contract API được mô tả tại [`docs/data_contract.md`](docs/data_contract.md).

## 1. Chạy Data Warehouse

Từ repo `Dataware-House-Assignment/DW_ETL`:

```bash
docker compose up -d
python -m etl.profile_sources
python -m etl.load_dw
```

## 2. Tạo view review cho backend

Từ repo `Dataware-House-Assignment`:

```bash
docker exec -i olist-dw-postgres psql -U dw_user -d olist_dw \
  -v ON_ERROR_STOP=1 < be/src/sql/003__views.sql
```

## 3. Chạy backend API

```bash
cd be
cp .env.example .env
npm install
npm run dev
```

Kiểm tra:

```bash
curl http://localhost:3000/api/v1/health
curl http://localhost:3000/api/v1/db-health
```

## 4. Chạy dashboard

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
streamlit run app.py
```

Mở <http://localhost:8501>.

Windows PowerShell dùng:

```powershell
.\.venv\Scripts\Activate.ps1
```

## Chạy UI bằng Docker

Backend API vẫn phải chạy ở cổng `3000`:

```bash
cp .env.example .env
docker compose up --build
```

Compose tự đổi API URL thành `http://host.docker.internal:3000`.

## Tests

```bash
pytest
python -m compileall -q app.py pages src tests
```

## Quy tắc KPI

- `total_price` là tổng giá trị mặt hàng, không phải lợi nhuận/doanh thu thuần.
- Sales mặc định lọc trạng thái `delivered`.
- Số order sales là `COUNT(DISTINCT order_id)`.
- Delivery chỉ tính các order có `is_delivery_eligible = true`.
- `late_rate` từ delivery API là phần trăm.
- `low_review_rate` từ review API là tỷ lệ 0–1; UI nhân 100 để hiển thị.
- `late_rate` từ Pivot và Delivery Buffer là tỷ lệ 0–1; UI nhân 100 để hiển thị.
- Không quy KPI giao trễ cho seller vì delivery fact có grain order.
- DSS seller chỉ dùng order một seller và yêu cầu đủ số mẫu trước khi chấm điểm.

## Cấu trúc

```text
app.py                         # Executive overview
pages/1_Sales_OLAP.py         # Sales roll-up/drill-down
pages/2_Delivery_and_Reviews.py
pages/3_Decision_Support.py
pages/4_Delivery_Buffer.py
pages/5_Evaluation.py
src/api.py                     # HTTP client và cache
src/delivery_buffer.py         # Chuẩn hóa response Delivery Buffer
src/pivot.py                   # Pivot explorer dùng metadata từ backend
src/filters.py                 # Bộ lọc dùng chung
src/transform.py               # Chuẩn hóa payload OLAP thành DataFrame
docs/data_contract.md
docs/evaluation.md
```

