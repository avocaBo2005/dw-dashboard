import plotly.express as px
import streamlit as st

from src.database import query_dataframe
from src.filters import purchase_date_range
from src.ui import configure_page, render_data_error


configure_page("Decision Support", "🎯")
st.title("Decision Support")
st.caption("Rule-based prioritization of month and customer-state segments")

min_orders = st.sidebar.number_input("Minimum eligible orders", 10, 10000, 100, 10)
delay_threshold = st.sidebar.slider("Delayed-rate warning (%)", 0.0, 50.0, 10.0, 0.5)
review_threshold = st.sidebar.slider("Low average-review threshold", 1.0, 5.0, 3.5, 0.1)

try:
    date_from, date_to = purchase_date_range()
    segments = query_dataframe(
        """
        SELECT purchase_month, customer_state, eligible_orders, delayed_orders,
               delayed_rate_pct, avg_review_score, reviewed_orders
        FROM analytics.v_decision_segments
        WHERE purchase_month BETWEEN
                  DATE_TRUNC('month', CAST(:date_from AS date))::date
              AND DATE_TRUNC('month', CAST(:date_to AS date))::date
          AND eligible_orders >= :min_orders
        ORDER BY delayed_rate_pct DESC, eligible_orders DESC
        """,
        {
            "date_from": date_from,
            "date_to": date_to,
            "min_orders": min_orders,
        },
    )
    if segments.empty:
        st.info("No segment meets the selected minimum volume.")
        st.stop()

    segments["delivery_alert"] = segments["delayed_rate_pct"] >= delay_threshold
    segments["review_alert"] = segments["avg_review_score"] < review_threshold
    segments["priority"] = (
        segments["delivery_alert"].astype(int) * 2
        + segments["review_alert"].astype(int)
    )
    segments["recommendation"] = "Monitor"
    segments.loc[segments["delivery_alert"], "recommendation"] = (
        "Investigate delivery capacity and route performance"
    )
    segments.loc[segments["review_alert"], "recommendation"] = (
        "Review customer feedback and service quality"
    )
    segments.loc[
        segments["delivery_alert"] & segments["review_alert"],
        "recommendation",
    ] = "High priority: investigate delivery and customer experience"

    alerts = segments[segments["priority"] > 0].sort_values(
        ["priority", "eligible_orders"], ascending=[False, False]
    )
    metric_columns = st.columns(3)
    metric_columns[0].metric("Segments analyzed", f"{len(segments):,}")
    metric_columns[1].metric("Segments flagged", f"{len(alerts):,}")
    metric_columns[2].metric(
        "High-priority segments", f"{(segments['priority'] == 3).sum():,}"
    )

    st.plotly_chart(
        px.scatter(
            segments,
            x="delayed_rate_pct",
            y="avg_review_score",
            size="eligible_orders",
            color="priority",
            hover_data=["purchase_month", "customer_state", "eligible_orders"],
            title="Segment risk matrix",
        ),
        use_container_width=True,
    )
    st.subheader("Prioritized actions")
    st.dataframe(
        alerts[
            [
                "purchase_month",
                "customer_state",
                "eligible_orders",
                "delayed_rate_pct",
                "avg_review_score",
                "recommendation",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )
    st.caption(
        "These rules prioritize investigation; they do not establish causality. "
        "Validate flagged segments with operational context before acting."
    )
except Exception as exc:
    render_data_error(exc)
