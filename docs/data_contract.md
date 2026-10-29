# Analytics data contract

The UI reads only from the `analytics` schema. The SQL in
`sql/001_create_analytics_views.sql` creates the contract after the DW ETL has
loaded the `dw` schema.

| View | Grain | Purpose |
| --- | --- | --- |
| `v_sales_detail` | One order item | Sales value, freight, seller, product, status, and purchase time |
| `v_delivery_detail` | One order | Delivery eligibility, duration, delay, customer geography, and status |
| `v_review_order` | One order with reviews | Safe order-level review aggregation |
| `v_review_delivery_detail` | One accepted review linked to an order | Review distribution and delivery comparison |
| `v_decision_segments` | Purchase month and customer state | Rule-based decision-support prioritization |

## Metric rules

- Item value is `SUM(price)` and is not profit or net revenue.
- Seller order count is `COUNT(DISTINCT order_id)`.
- Delivery denominators include only rows where `is_delivery_eligible = true`.
- Delivery performance is not attributed to sellers because delivery is stored
  at order grain and an order can contain items from multiple sellers.
- Reviews are aggregated to order grain before joining to an order-level segment.

