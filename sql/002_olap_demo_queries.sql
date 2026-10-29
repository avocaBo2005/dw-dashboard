SET search_path TO analytics, dw, public;

-- Roll-up: month -> quarter -> year.
SELECT
    year,
    quarter,
    month,
    SUM(item_value) AS item_value,
    COUNT(DISTINCT order_id) AS orders
FROM v_sales_detail
GROUP BY ROLLUP (year, quarter, month)
ORDER BY year NULLS LAST, quarter NULLS LAST, month NULLS LAST;

-- Cube: sales by time, product category, and seller state.
SELECT
    year,
    product_category,
    seller_state,
    SUM(item_value) AS item_value
FROM v_sales_detail
GROUP BY CUBE (year, product_category, seller_state);

-- Slice: delivered orders only.
SELECT purchase_date, customer_state, delivery_days, delay_days
FROM v_delivery_detail
WHERE order_status = 'delivered';

-- Dice: selected date, category, and seller-state ranges.
SELECT product_category, seller_state, SUM(item_value) AS item_value
FROM v_sales_detail
WHERE purchase_date BETWEEN DATE '2017-01-01' AND DATE '2017-12-31'
  AND seller_state IN ('SP', 'RJ', 'MG')
  AND product_category IN ('bed_bath_table', 'health_beauty')
GROUP BY product_category, seller_state;

-- Pivot-like review distribution.
SELECT
    COUNT(*) FILTER (WHERE review_score = 1) AS score_1,
    COUNT(*) FILTER (WHERE review_score = 2) AS score_2,
    COUNT(*) FILTER (WHERE review_score = 3) AS score_3,
    COUNT(*) FILTER (WHERE review_score = 4) AS score_4,
    COUNT(*) FILTER (WHERE review_score = 5) AS score_5
FROM v_review_delivery_detail;

