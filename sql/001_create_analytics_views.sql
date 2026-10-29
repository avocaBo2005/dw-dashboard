-- Analytics contract consumed by the separate Streamlit UI repository.
-- Run after the DW schema and ETL have been created successfully.
BEGIN;

CREATE SCHEMA IF NOT EXISTS analytics;

CREATE OR REPLACE VIEW analytics.v_sales_detail AS
SELECT
    f.order_id,
    f.order_item_id,
    f.purchase_date_key AS purchase_date,
    d.year,
    d.quarter,
    d.month,
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COALESCE(p.product_category_name_english, p.product_category_name) AS product_category,
    os.order_status,
    f.price AS item_value,
    f.freight_value,
    f.item_count
FROM dw.fact_sales_item f
JOIN dw.dim_date d ON d.date_key = f.purchase_date_key
JOIN dw.dim_seller s ON s.seller_key = f.seller_key
JOIN dw.dim_product p ON p.product_key = f.product_key
JOIN dw.dim_order_status os ON os.order_status_key = f.order_status_key;

CREATE OR REPLACE VIEW analytics.v_delivery_detail AS
SELECT
    f.order_id,
    f.purchase_date_key AS purchase_date,
    d.year,
    d.quarter,
    d.month,
    c.customer_unique_id,
    c.customer_city,
    c.customer_state,
    os.order_status,
    f.delivery_days,
    f.delay_days,
    f.is_delayed,
    f.is_delivery_eligible
FROM dw.fact_delivery_order f
LEFT JOIN dw.dim_date d ON d.date_key = f.purchase_date_key
JOIN dw.dim_customer c ON c.customer_key = f.customer_key
JOIN dw.dim_order_status os ON os.order_status_key = f.order_status_key;

CREATE OR REPLACE VIEW analytics.v_review_order AS
SELECT
    order_id,
    COUNT(*) AS review_count,
    AVG(review_score)::numeric AS avg_review_score,
    COUNT(*) FILTER (WHERE review_score <= 2) AS low_score_reviews
FROM dw.fact_review
GROUP BY order_id;

CREATE OR REPLACE VIEW analytics.v_review_delivery_detail AS
SELECT
    r.review_key,
    r.review_id,
    r.order_id,
    r.review_creation_date_key AS review_date,
    r.review_score,
    d.purchase_date,
    d.customer_city,
    d.customer_state,
    d.order_status,
    d.delivery_days,
    d.delay_days,
    d.is_delayed,
    d.is_delivery_eligible
FROM dw.fact_review r
JOIN analytics.v_delivery_detail d ON d.order_id = r.order_id;

CREATE OR REPLACE VIEW analytics.v_decision_segments AS
SELECT
    DATE_TRUNC('month', d.purchase_date)::date AS purchase_month,
    d.customer_state,
    COUNT(*) FILTER (WHERE d.is_delivery_eligible) AS eligible_orders,
    COUNT(*) FILTER (
        WHERE d.is_delivery_eligible AND d.is_delayed
    ) AS delayed_orders,
    ROUND(
        100.0 * COUNT(*) FILTER (
            WHERE d.is_delivery_eligible AND d.is_delayed
        ) / NULLIF(COUNT(*) FILTER (
            WHERE d.is_delivery_eligible
        ), 0),
        2
    ) AS delayed_rate_pct,
    ROUND(AVG(r.avg_review_score), 2) AS avg_review_score,
    COUNT(r.order_id) AS reviewed_orders
FROM analytics.v_delivery_detail d
LEFT JOIN analytics.v_review_order r ON r.order_id = d.order_id
WHERE d.purchase_date IS NOT NULL
GROUP BY DATE_TRUNC('month', d.purchase_date)::date, d.customer_state;

COMMIT;

