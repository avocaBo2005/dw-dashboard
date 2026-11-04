import pandas as pd
import plotly.express as px
import streamlit as st

from src.api import api_get
from src.filters import analysis_options, date_params, purchase_date_range
from src.transform import add_month_start, grand_total, level_frame
from src.ui import configure_page, format_number, render_data_error


configure_page("Delivery & Reviews", "🚚")
st.title("Giao hàng và đánh giá khách hàng")
st.caption("Phân tích trên các đơn đủ điều kiện giao hàng ở grain order")

try:
    date_from, date_to = purchase_date_range()
    common = date_params(date_from, date_to)
    states = analysis_options(
        "/api/v1/delivery/analysis", "customer_geo", "customer_state", common
    )
    selected_state = st.sidebar.selectbox("Customer state", ["Tất cả", *states])
    filters = {
        **common,
        "state": None if selected_state == "Tất cả" else selected_state,
    }

    time_payload = api_get(
        "/api/v1/delivery/analysis", {**filters, "dim": "time", "depth": 3}
    )
    geo_payload = api_get(
        "/api/v1/delivery/analysis",
        {**filters, "dim": "customer_geo", "depth": 2},
    )
    distribution = api_get(
        "/api/v1/delivery/distribution",
        {**filters, "dim": "time", "depth": 3},
    )
    review_bucket = api_get(
        "/api/v1/reviews/by-delay", {**filters, "group": "bucket"}
    )
    review_flag = api_get(
        "/api/v1/reviews/by-delay", {**filters, "group": "flag"}
    )

    total = grand_total(time_payload)
    summary = distribution.get("summary", {})
    review_meta = review_flag.get("meta", {})
    metrics = st.columns(5)
    metrics[0].metric("Đơn đủ điều kiện", format_number(total.get("eligible_orders")))
    metrics[1].metric("Đơn giao trễ", format_number(summary.get("late_orders")))
    metrics[2].metric("Tỷ lệ giao trễ", f"{format_number(summary.get('late_rate'), 2)}%")
    metrics[3].metric("Ngày giao TB", format_number(total.get("avg_delivery_days"), 2))
    metrics[4].metric("Điểm review khi trễ", format_number(review_meta.get("avg_late"), 2))

    monthly = add_month_start(level_frame(time_payload, 3))
    state_data = level_frame(geo_payload, 1)
    city_data = level_frame(geo_payload, 2)
    buckets = pd.DataFrame(distribution.get("data", []))
    reviews = pd.DataFrame(review_bucket.get("data", []))
    if not reviews.empty:
        reviews["low_review_pct"] = reviews["low_review_rate"] * 100

    st.plotly_chart(
        px.line(
            monthly,
            x="month_start",
            y="late_rate",
            markers=True,
            title="Tỷ lệ giao trễ theo tháng",
            labels={"month_start": "Tháng", "late_rate": "Tỷ lệ trễ (%)"},
        ),
        width="stretch",
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            state_data.nlargest(15, "late_rate"),
            x="customer_state",
            y="late_rate",
            hover_data=["eligible_orders", "late_orders"],
            title="Tỷ lệ giao trễ theo customer state",
        ),
        width="stretch",
    )
    right.plotly_chart(
        px.bar(
            buckets,
            x="label",
            y="n_orders",
            color="side",
            title="Phân phối sớm / đúng hạn / trễ",
        ),
        width="stretch",
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            reviews,
            x="label",
            y="avg_score",
            color="group",
            title="Điểm review theo nhóm độ trễ",
        ),
        width="stretch",
    )
    right.plotly_chart(
        px.bar(
            reviews,
            x="label",
            y="low_review_pct",
            color="group",
            title="Tỷ lệ review thấp theo nhóm độ trễ",
        ),
        width="stretch",
    )

    st.subheader("Drill-down customer state → customer city")
    city_columns = [
        column
        for column in [
            "customer_state",
            "customer_city",
            "eligible_orders",
            "late_orders",
            "late_rate",
            "avg_delivery_days",
            "avg_delay_days",
        ]
        if column in city_data.columns
    ]
    st.dataframe(
        city_data.nlargest(100, "eligible_orders")[city_columns],
        width="stretch",
        hide_index=True,
    )
except Exception as exc:
    render_data_error(exc)

