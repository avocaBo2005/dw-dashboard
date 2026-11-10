import pandas as pd
import plotly.express as px
import streamlit as st

from src.api import api_get
from src.filters import date_params, purchase_date_range, sales_status_filter
from src.transform import add_month_start, grand_total, has_columns, level_frame
from src.ui import (
    configure_page,
    format_number,
    page_header,
    render_data_error,
    section_intro,
    status_badge,
    style_figure,
)


configure_page("Olist DW Dashboard", "📦")
page_header(
    "Olist Performance Hub",
    "Tổng quan điều hành về bán hàng, giao hàng và trải nghiệm khách hàng từ kho dữ liệu đa chiều.",
    "Executive overview · Olist",
)

try:
    health = api_get("/api/v1/health")
    health_status = health.get("data", {}).get("status", "unknown")
    with st.sidebar:
        status_badge(
            f"API · {str(health_status).upper()}",
            "ok" if health_status == "ok" else "warn",
        )

    date_from, date_to = purchase_date_range()
    statuses = sales_status_filter()
    if not statuses:
        st.sidebar.warning("Chọn ít nhất một trạng thái đơn hàng.")
        st.stop()

    base_params = date_params(date_from, date_to)
    sales_params = {
        **base_params,
        "dim": "time",
        "depth": 3,
        "status": ",".join(statuses),
    }
    delivery_params = {**base_params, "dim": "time", "depth": 3}

    sales_payload = api_get("/api/v1/sale/analysis", sales_params)
    delivery_payload = api_get("/api/v1/delivery/analysis", delivery_params)
    distribution = api_get("/api/v1/delivery/distribution", delivery_params)
    reviews = api_get(
        "/api/v1/reviews/by-delay", {**base_params, "group": "flag"}
    )

    sales_total = grand_total(sales_payload)
    delivery_total = grand_total(delivery_payload)
    review_rows = {row["group"]: row for row in reviews.get("data", [])}

    first = st.columns(4)
    first[0].metric("Giá trị mặt hàng", format_number(sales_total.get("total_price"), 2))
    first[1].metric("Phí vận chuyển", format_number(sales_total.get("total_freight"), 2))
    first[2].metric("Số đơn phân biệt", format_number(sales_total.get("n_orders")))
    first[3].metric("Số mặt hàng", format_number(sales_total.get("n_items")))

    second = st.columns(4)
    second[0].metric(
        "Đơn đủ điều kiện", format_number(delivery_total.get("eligible_orders"))
    )
    second[1].metric(
        "Tỷ lệ giao trễ",
        f"{format_number(distribution.get('summary', {}).get('late_rate'), 2)}%",
    )
    second[2].metric(
        "Điểm review khi trễ",
        format_number(review_rows.get("late", {}).get("avg_score"), 2),
    )
    second[3].metric(
        "Điểm review khi không trễ",
        format_number(review_rows.get("not_late", {}).get("avg_score"), 2),
    )

    sales_monthly = add_month_start(level_frame(sales_payload, 3))
    delivery_monthly = add_month_start(level_frame(delivery_payload, 3))
    category_payload = api_get(
        "/api/v1/sale/analysis",
        {
            **base_params,
            "dim": "product",
            "depth": 1,
            "status": ",".join(statuses),
        },
    )
    categories = level_frame(category_payload, 1).nlargest(10, "total_price")
    buckets = pd.DataFrame(distribution.get("data", []))

    section_intro("Xu hướng chính", "So sánh diễn biến giá trị mặt hàng và tỷ lệ giao trễ theo tháng.")
    left, right = st.columns(2)
    if has_columns(sales_monthly, "month_start", "total_price"):
        left.plotly_chart(style_figure(px.line(
            sales_monthly,
            x="month_start",
            y="total_price",
            markers=True,
            title="Giá trị mặt hàng theo tháng",
            labels={"month_start": "Tháng", "total_price": "Giá trị mặt hàng"},
        )), width="stretch")
    else:
        left.info("Không có dữ liệu sales theo tháng cho bộ lọc hiện tại.")
    if has_columns(delivery_monthly, "month_start", "late_rate"):
        right.plotly_chart(style_figure(px.line(
            delivery_monthly,
            x="month_start",
            y="late_rate",
            markers=True,
            title="Tỷ lệ giao trễ theo tháng",
            labels={"month_start": "Tháng", "late_rate": "Tỷ lệ trễ (%)"},
        )), width="stretch")
    else:
        right.info("Không có dữ liệu delivery theo tháng cho bộ lọc hiện tại.")

    section_intro("Cơ cấu và phân phối", "Top danh mục theo giá trị mặt hàng và phân bố chênh lệch ngày giao.")
    left, right = st.columns(2)
    if has_columns(categories, "total_price", "category"):
        left.plotly_chart(style_figure(px.bar(
            categories.sort_values("total_price"),
            x="total_price",
            y="category",
            orientation="h",
            title="10 danh mục có giá trị mặt hàng cao nhất",
            labels={"total_price": "Giá trị mặt hàng", "category": "Danh mục"},
        )), width="stretch")
    else:
        left.info("Không có dữ liệu danh mục cho bộ lọc hiện tại.")
    if not buckets.empty and {"label", "n_orders", "side"}.issubset(buckets.columns):
        right.plotly_chart(style_figure(px.bar(
            buckets,
            x="label",
            y="n_orders",
            color="side",
            title="Phân phối độ trễ giao hàng",
            labels={"label": "Nhóm giao hàng", "n_orders": "Số đơn"},
        )), width="stretch")
    else:
        right.info("Không có dữ liệu phân phối giao hàng.")

    st.info(
        "Giá trị mặt hàng là SUM(price), không phải lợi nhuận hoặc doanh thu thuần. "
        "KPI giao hàng chỉ tính các đơn đủ điều kiện."
    )
except Exception as exc:
    render_data_error(exc)

