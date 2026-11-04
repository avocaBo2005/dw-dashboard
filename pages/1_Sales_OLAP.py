import plotly.express as px
import streamlit as st

from src.api import api_get
from src.filters import (
    analysis_options,
    date_params,
    purchase_date_range,
    sales_status_filter,
)
from src.transform import add_month_start, grand_total, level_frame
from src.ui import configure_page, format_number, render_data_error


configure_page("Sales OLAP", "💰")
st.title("Phân tích OLAP bán hàng")
st.caption("Roll-up và drill-down theo thời gian, địa lý seller và sản phẩm")

try:
    date_from, date_to = purchase_date_range()
    statuses = sales_status_filter()
    if not statuses:
        st.warning("Chọn ít nhất một trạng thái đơn hàng.")
        st.stop()
    common = {**date_params(date_from, date_to), "status": ",".join(statuses)}

    state_options = analysis_options(
        "/api/v1/sale/analysis", "seller_geo", "seller_state", common
    )
    category_options = analysis_options(
        "/api/v1/sale/analysis", "product", "category", common
    )
    selected_state = st.sidebar.selectbox("Seller state", ["Tất cả", *state_options])
    selected_category = st.sidebar.selectbox("Danh mục", ["Tất cả", *category_options])
    filters = {
        **common,
        "state": None if selected_state == "Tất cả" else selected_state,
        "category": None if selected_category == "Tất cả" else selected_category,
    }

    time_payload = api_get(
        "/api/v1/sale/analysis", {**filters, "dim": "time", "depth": 3}
    )
    geo_payload = api_get(
        "/api/v1/sale/analysis", {**filters, "dim": "seller_geo", "depth": 2}
    )
    product_payload = api_get(
        "/api/v1/sale/analysis", {**filters, "dim": "product", "depth": 1}
    )

    total = grand_total(time_payload)
    metrics = st.columns(4)
    metrics[0].metric("Giá trị mặt hàng", format_number(total.get("total_price"), 2))
    metrics[1].metric("Phí vận chuyển", format_number(total.get("total_freight"), 2))
    metrics[2].metric("Đơn phân biệt", format_number(total.get("n_orders")))
    metrics[3].metric("Số item", format_number(total.get("n_items")))

    monthly = add_month_start(level_frame(time_payload, 3))
    states = level_frame(geo_payload, 1)
    cities = level_frame(geo_payload, 2)
    categories = level_frame(product_payload, 1)

    st.plotly_chart(
        px.line(
            monthly,
            x="month_start",
            y=["total_price", "total_freight"],
            markers=True,
            title="Roll-up thời gian: giá trị mặt hàng và phí vận chuyển",
            labels={"month_start": "Tháng", "value": "Giá trị", "variable": "Measure"},
        ),
        width="stretch",
    )
    left, right = st.columns(2)
    left.plotly_chart(
        px.bar(
            states.nlargest(15, "total_price").sort_values("total_price"),
            x="total_price",
            y="seller_state",
            orientation="h",
            title="Giá trị mặt hàng theo seller state",
        ),
        width="stretch",
    )
    right.plotly_chart(
        px.bar(
            categories.nlargest(15, "total_price").sort_values("total_price"),
            x="total_price",
            y="category",
            orientation="h",
            title="Top danh mục sản phẩm",
        ),
        width="stretch",
    )

    st.subheader("Drill-down seller state → seller city")
    city_columns = [
        column
        for column in [
            "seller_state",
            "seller_city",
            "total_price",
            "total_freight",
            "n_orders",
            "n_items",
        ]
        if column in cities.columns
    ]
    st.dataframe(
        cities.nlargest(100, "total_price")[city_columns],
        width="stretch",
        hide_index=True,
    )
    st.warning(
        "Số đơn theo seller dùng COUNT(DISTINCT order_id). Không gán KPI giao trễ "
        "cho seller vì delivery fact có grain order."
    )
except Exception as exc:
    render_data_error(exc)

