import plotly.express as px
import streamlit as st

from src.database import query_dataframe
from src.filters import multiselect_from_query, purchase_date_range
from src.query_utils import add_in_filter
from src.ui import configure_page, format_number, render_data_error


configure_page("Delivery & Reviews", "🚚")
st.title("Delivery & Customer Reviews")

try:
    date_from, date_to = purchase_date_range()
    states = multiselect_from_query(
        "Customer state",
        "SELECT DISTINCT customer_state FROM analytics.v_delivery_detail "
        "WHERE customer_state IS NOT NULL ORDER BY customer_state",
        "customer_state",
    )
    clauses = ["purchase_date BETWEEN :date_from AND :date_to"]
    params = {"date_from": date_from, "date_to": date_to}
    add_in_filter(clauses, params, "customer_state", states, "customer_state")
    where_sql = " AND ".join(clauses)

    summary = query_dataframe(
        f"""
        SELECT COUNT(*) FILTER (WHERE is_delivery_eligible) AS eligible,
               COUNT(*) FILTER (WHERE is_delivery_eligible AND is_delayed) AS delayed,
               ROUND(100.0 * COUNT(*) FILTER (
                   WHERE is_delivery_eligible AND is_delayed
               ) / NULLIF(COUNT(*) FILTER (
                   WHERE is_delivery_eligible
               ), 0), 2) AS delayed_rate,
               ROUND(AVG(delivery_days) FILTER (
                   WHERE is_delivery_eligible
               )::numeric, 2) AS avg_delivery_days
        FROM analytics.v_delivery_detail
        WHERE {where_sql}
        """,
        params,
    ).iloc[0]
    metrics = st.columns(4)
    metrics[0].metric("Eligible orders", format_number(summary["eligible"]))
    metrics[1].metric("Delayed orders", format_number(summary["delayed"]))
    metrics[2].metric("Delayed rate", f"{format_number(summary['delayed_rate'], 2)}%")
    metrics[3].metric("Average delivery days", format_number(summary["avg_delivery_days"], 2))

    monthly = query_dataframe(
        f"""
        SELECT DATE_TRUNC('month', purchase_date)::date AS month,
               COUNT(*) FILTER (WHERE is_delivery_eligible) AS eligible_orders,
               ROUND(100.0 * COUNT(*) FILTER (
                   WHERE is_delivery_eligible AND is_delayed
               ) / NULLIF(COUNT(*) FILTER (
                   WHERE is_delivery_eligible
               ), 0), 2) AS delayed_rate_pct
        FROM analytics.v_delivery_detail
        WHERE {where_sql}
        GROUP BY DATE_TRUNC('month', purchase_date)::date
        ORDER BY month
        """,
        params,
    )
    state_data = query_dataframe(
        f"""
        SELECT customer_state,
               COUNT(*) FILTER (WHERE is_delivery_eligible) AS eligible_orders,
               ROUND(100.0 * COUNT(*) FILTER (
                   WHERE is_delivery_eligible AND is_delayed
               ) / NULLIF(COUNT(*) FILTER (
                   WHERE is_delivery_eligible
               ), 0), 2) AS delayed_rate_pct
        FROM analytics.v_delivery_detail
        WHERE {where_sql}
        GROUP BY customer_state
        HAVING COUNT(*) FILTER (WHERE is_delivery_eligible) >= 30
        ORDER BY delayed_rate_pct DESC
        """,
        params,
    )
    review_distribution = query_dataframe(
        f"""
        SELECT review_score, COUNT(*) AS reviews
        FROM analytics.v_review_delivery_detail
        WHERE {where_sql}
        GROUP BY review_score
        ORDER BY review_score
        """,
        params,
    )
    review_delay = query_dataframe(
        f"""
        SELECT CASE WHEN is_delayed THEN 'Delayed' ELSE 'Not delayed' END AS delivery_group,
               ROUND(AVG(review_score)::numeric, 2) AS avg_review_score,
               COUNT(*) AS reviews
        FROM analytics.v_review_delivery_detail
        WHERE {where_sql} AND is_delivery_eligible
        GROUP BY CASE WHEN is_delayed THEN 'Delayed' ELSE 'Not delayed' END
        """,
        params,
    )

    st.plotly_chart(
        px.line(monthly, x="month", y="delayed_rate_pct", markers=True,
                title="Monthly delayed-delivery rate"),
        use_container_width=True,
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(state_data, x="customer_state", y="delayed_rate_pct",
               title="Delayed rate by customer state"),
        use_container_width=True,
    )
    right.plotly_chart(
        px.bar(review_distribution, x="review_score", y="reviews",
               title="Review score distribution"),
        use_container_width=True,
    )
    st.plotly_chart(
        px.bar(review_delay, x="delivery_group", y="avg_review_score",
               color="delivery_group", title="Review score by delivery outcome"),
        use_container_width=True,
    )
except Exception as exc:
    render_data_error(exc)

