import pandas as pd
import plotly.express as px
import streamlit as st

from src.api import api_get
from src.filters import analysis_options, date_params, purchase_date_range
from src.transform import add_month_start, grand_total, has_columns, level_frame
from src.ui import (
    configure_page, dataframe_config, format_number, page_header,
    render_data_error, section_intro, style_figure,
)


configure_page("Delivery & Reviews", "🚚")
page_header(
    "Giao hàng và trải nghiệm",
    "Phân tích độ trễ và phản hồi khách hàng trên các đơn đủ điều kiện ở grain order.",
    "OLAP cube · Delivery order",
)

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

    section_intro("Xu hướng giao hàng", "Tỷ lệ trễ được tính trên các đơn đủ điều kiện giao hàng.")
    if has_columns(monthly, "month_start", "late_rate"):
        st.plotly_chart(style_figure(px.line(
            monthly,
            x="month_start",
            y="late_rate",
            markers=True,
            title="Tỷ lệ giao trễ theo tháng",
            labels={"month_start": "Tháng", "late_rate": "Tỷ lệ trễ (%)"},
        )), width="stretch")
    else:
        st.info("Không có dữ liệu delivery theo tháng cho bộ lọc hiện tại.")
    left, right = st.columns(2)
    if has_columns(state_data, "customer_state", "late_rate"):
        left.plotly_chart(style_figure(px.bar(
            state_data.nlargest(15, "late_rate"),
            x="customer_state",
            y="late_rate",
            hover_data=["eligible_orders", "late_orders"],
            title="Tỷ lệ giao trễ theo customer state",
        )), width="stretch")
    else:
        left.info("Không có dữ liệu theo customer state.")
    if not buckets.empty and {"label", "n_orders", "side"}.issubset(buckets.columns):
        right.plotly_chart(style_figure(px.bar(
            buckets,
            x="label",
            y="n_orders",
            color="side",
            title="Phân phối sớm / đúng hạn / trễ",
        )), width="stretch")
    else:
        right.info("Không có dữ liệu phân phối độ trễ.")
    left, right = st.columns(2)
    if not reviews.empty and {"label", "avg_score", "group"}.issubset(reviews.columns):
        left.plotly_chart(style_figure(px.bar(
            reviews,
            x="label",
            y="avg_score",
            color="group",
            title="Điểm review theo nhóm độ trễ",
        )), width="stretch")
        right.plotly_chart(style_figure(px.bar(
            reviews,
            x="label",
            y="low_review_pct",
            color="group",
            title="Tỷ lệ review thấp theo nhóm độ trễ",
        )), width="stretch")
    else:
        left.info("Không có dữ liệu review theo độ trễ.")
        right.info("Không có dữ liệu review theo độ trễ.")

    section_intro("Drill-down customer state → customer city", "100 thành phố có nhiều đơn đủ điều kiện nhất.")
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
    if has_columns(city_data, "eligible_orders") and city_columns:
        st.dataframe(
            city_data.nlargest(100, "eligible_orders")[city_columns],
            width="stretch", hide_index=True, column_config=dataframe_config(),
        )
    else:
        st.info("Không có dữ liệu drill-down theo customer city.")
except Exception as exc:
    render_data_error(exc)

