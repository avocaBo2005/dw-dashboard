import plotly.express as px
import streamlit as st

from src.database import query_dataframe
from src.filters import multiselect_from_query, purchase_date_range
from src.query_utils import add_in_filter
from src.ui import configure_page, render_data_error


configure_page("Sales & Sellers", "💰")
st.title("Sales & Seller Analysis")
st.caption("Item-level measures with distinct order counting per seller")

try:
    date_from, date_to = purchase_date_range()
    states = multiselect_from_query(
        "Seller state",
        "SELECT DISTINCT seller_state FROM analytics.v_sales_detail "
        "WHERE seller_state IS NOT NULL ORDER BY seller_state",
        "seller_state",
    )
    categories = multiselect_from_query(
        "Product category",
        "SELECT DISTINCT product_category FROM analytics.v_sales_detail "
        "WHERE product_category IS NOT NULL ORDER BY product_category",
        "product_category",
    )
    clauses = ["purchase_date BETWEEN :date_from AND :date_to"]
    params = {"date_from": date_from, "date_to": date_to}
    add_in_filter(clauses, params, "seller_state", states, "state")
    add_in_filter(clauses, params, "product_category", categories, "category")
    where_sql = " AND ".join(clauses)

    monthly = query_dataframe(
        f"""
        SELECT DATE_TRUNC('month', purchase_date)::date AS month,
               SUM(item_value) AS item_value,
               COUNT(DISTINCT order_id) AS orders
        FROM analytics.v_sales_detail
        WHERE {where_sql}
        GROUP BY DATE_TRUNC('month', purchase_date)::date
        ORDER BY month
        """,
        params,
    )
    seller = query_dataframe(
        f"""
        SELECT seller_id, seller_city, seller_state,
               SUM(item_count) AS items,
               COUNT(DISTINCT order_id) AS orders,
               SUM(item_value) AS item_value,
               SUM(freight_value) AS freight_value
        FROM analytics.v_sales_detail
        WHERE {where_sql}
        GROUP BY seller_id, seller_city, seller_state
        ORDER BY item_value DESC
        LIMIT 100
        """,
        params,
    )
    category = query_dataframe(
        f"""
        SELECT COALESCE(product_category, 'Unknown') AS product_category,
               SUM(item_value) AS item_value,
               SUM(item_count) AS items
        FROM analytics.v_sales_detail
        WHERE {where_sql}
        GROUP BY COALESCE(product_category, 'Unknown')
        ORDER BY item_value DESC
        LIMIT 15
        """,
        params,
    )

    st.plotly_chart(
        px.line(monthly, x="month", y="item_value", markers=True,
                title="Monthly item value"),
        use_container_width=True,
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(seller.head(15).sort_values("item_value"), x="item_value",
               y="seller_id", orientation="h", title="Top sellers"),
        use_container_width=True,
    )
    right.plotly_chart(
        px.bar(category.sort_values("item_value"), x="item_value",
               y="product_category", orientation="h", title="Top categories"),
        use_container_width=True,
    )
    st.subheader("Seller details")
    st.dataframe(seller, use_container_width=True, hide_index=True)
    st.warning(
        "Seller orders use COUNT(DISTINCT order_id). Delivery delays are not "
        "attributed to sellers because the delivery fact is at order grain."
    )
except Exception as exc:
    render_data_error(exc)

