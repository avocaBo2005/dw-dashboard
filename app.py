import plotly.express as px
import streamlit as st

from src.database import query_dataframe
from src.filters import purchase_date_range
from src.ui import configure_page, format_number, render_data_error


configure_page("Olist DW Dashboard", "📦")
st.title("Olist Data Warehouse Dashboard")
st.caption("Executive overview of sales value, delivery quality, and customer reviews")

try:
    date_from, date_to = purchase_date_range()
    params = {"date_from": date_from, "date_to": date_to}

    sales = query_dataframe(
        """
        SELECT
            COALESCE(SUM(item_value), 0) AS item_value,
            COALESCE(SUM(freight_value), 0) AS freight_value,
            COALESCE(SUM(item_count), 0) AS item_count,
            COUNT(DISTINCT order_id) AS order_count
        FROM analytics.v_sales_detail
        WHERE purchase_date BETWEEN :date_from AND :date_to
        """,
        params,
    ).iloc[0]
    delivery = query_dataframe(
        """
        SELECT
            COUNT(*) FILTER (WHERE is_delivery_eligible) AS eligible_orders,
            COUNT(*) FILTER (WHERE is_delivery_eligible AND is_delayed) AS delayed_orders,
            ROUND(100.0 * COUNT(*) FILTER (
                WHERE is_delivery_eligible AND is_delayed
            ) / NULLIF(COUNT(*) FILTER (
                WHERE is_delivery_eligible
            ), 0), 2) AS delayed_rate_pct,
            ROUND(AVG(delivery_days) FILTER (
                WHERE is_delivery_eligible
            )::numeric, 2) AS avg_delivery_days
        FROM analytics.v_delivery_detail
        WHERE purchase_date BETWEEN :date_from AND :date_to
        """,
        params,
    ).iloc[0]
    reviews = query_dataframe(
        """
        SELECT ROUND(AVG(review_score)::numeric, 2) AS avg_review_score
        FROM analytics.v_review_delivery_detail
        WHERE purchase_date BETWEEN :date_from AND :date_to
        """,
        params,
    ).iloc[0]

    first = st.columns(4)
    first[0].metric("Item value", format_number(sales["item_value"], 2))
    first[1].metric("Freight value", format_number(sales["freight_value"], 2))
    first[2].metric("Distinct orders", format_number(sales["order_count"]))
    first[3].metric("Items", format_number(sales["item_count"]))
    second = st.columns(4)
    second[0].metric("Eligible deliveries", format_number(delivery["eligible_orders"]))
    second[1].metric("Delayed orders", format_number(delivery["delayed_orders"]))
    second[2].metric(
        "Delayed rate",
        f"{format_number(delivery['delayed_rate_pct'], 2)}%",
    )
    second[3].metric(
        "Average review",
        format_number(reviews["avg_review_score"], 2),
    )

    monthly = query_dataframe(
        """
        SELECT
            DATE_TRUNC('month', purchase_date)::date AS month,
            SUM(item_value) AS item_value,
            COUNT(DISTINCT order_id) AS orders
        FROM analytics.v_sales_detail
        WHERE purchase_date BETWEEN :date_from AND :date_to
        GROUP BY DATE_TRUNC('month', purchase_date)::date
        ORDER BY month
        """,
        params,
    )
    categories = query_dataframe(
        """
        SELECT
            COALESCE(product_category, 'Unknown') AS product_category,
            SUM(item_value) AS item_value
        FROM analytics.v_sales_detail
        WHERE purchase_date BETWEEN :date_from AND :date_to
        GROUP BY COALESCE(product_category, 'Unknown')
        ORDER BY item_value DESC
        LIMIT 10
        """,
        params,
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.line(monthly, x="month", y="item_value", markers=True,
                title="Monthly item value"),
        use_container_width=True,
    )
    right.plotly_chart(
        px.bar(categories.sort_values("item_value"), x="item_value",
               y="product_category", orientation="h",
               title="Top product categories"),
        use_container_width=True,
    )

    st.info(
        "Use the pages in the sidebar for seller, delivery, review, and "
        "decision-support analysis. Item value is not profit or net revenue."
    )
except Exception as exc:
    render_data_error(exc)

