import pandas as pd
import plotly.express as px
import streamlit as st

from src.api import api_get
from src.ui import (
    configure_page,
    dataframe_config,
    format_number,
    format_percent,
    page_header,
    render_data_error,
    section_intro,
    style_figure,
)


configure_page("Decision Support", "🎯")
page_header(
    "Seller Decision Support",
    "Xếp hạng seller bằng scorecard có cấu hình, sau đó ánh xạ qua knowledge base để đề xuất hành động.",
    "DSS · Seller scorecard",
)

STATE_CODES = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
    "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR",
    "RS", "SC", "SE", "SP", "TO",
]
LABEL_COLORS = {
    "Retain": "#138a66",
    "Improve": "#f59e0b",
    "Watch": "#4c78a8",
    "Review": "#d1495b",
    "Insufficient data": "#94a3b8",
    "Insufficient data - high GMV": "#7c3aed",
}


try:
    config_payload = api_get("/api/v1/dss/config")
    config = config_payload.get("data", {})
    configured_weights = {
        item["criterion"]: float(item["weight"])
        for item in config.get("weights", [])
    }
    if not configured_weights:
        raise ValueError("DSS config không có scoring weights")

    st.sidebar.subheader("Phạm vi xếp hạng")
    selected_state = st.sidebar.selectbox("Seller state", ["Toàn quốc", *STATE_CODES])
    limit = st.sidebar.slider("Số seller hiển thị", 10, 100, 50, 10)
    st.sidebar.subheader("Trọng số mô phỏng")
    use_custom_weights = st.sidebar.toggle("Tùy chỉnh trọng số", value=False)

    weights = configured_weights.copy()
    if use_custom_weights:
        weights["gmv"] = st.sidebar.slider(
            "GMV", 0.0, 1.0, configured_weights.get("gmv", 0.3), 0.05
        )
        weights["late_rate"] = st.sidebar.slider(
            "Giao đúng hạn", 0.0, 1.0, configured_weights.get("late_rate", 0.35), 0.05
        )
        weights["low_review_rate"] = st.sidebar.slider(
            "Chất lượng review", 0.0, 1.0,
            configured_weights.get("low_review_rate", 0.35), 0.05,
        )
        if sum(weights.values()) == 0:
            st.sidebar.error("Cần ít nhất một trọng số lớn hơn 0.")
            st.stop()
        st.sidebar.caption(f"Tổng trước chuẩn hóa: {sum(weights.values()):.2f}")

    params = {
        "state": None if selected_state == "Toàn quốc" else selected_state,
        "limit": limit,
        "weights": (
            ",".join(f"{name}:{value:.2f}" for name, value in weights.items())
            if use_custom_weights else None
        ),
    }
    payload = api_get("/api/v1/dss/seller-scorecard", params)
    scorecard = pd.DataFrame(payload.get("data", []))
    total_sellers = int(payload.get("pagination", {}).get("total") or 0)
    if scorecard.empty:
        st.info("Không có seller phù hợp với phạm vi đang chọn.")
        st.stop()

    reliable = scorecard[scorecard["score"].notna()].copy()
    review_count = int(scorecard["label"].eq("Review").sum())
    improve_count = int(scorecard["label"].eq("Improve").sum())
    retain_count = int(scorecard["label"].eq("Retain").sum())
    metrics = st.columns(5)
    metrics[0].metric("Seller trong phạm vi", format_number(total_sellers))
    metrics[1].metric("Đủ dữ liệu chấm điểm", format_number(len(reliable)))
    metrics[2].metric("Cần review", format_number(review_count))
    metrics[3].metric("Cần cải thiện", format_number(improve_count))
    metrics[4].metric("Nên duy trì", format_number(retain_count))

    section_intro(
        "Bản đồ quyết định",
        "Kích thước bong bóng biểu diễn GMV; góc trên bên phải là vùng rủi ro vận hành và trải nghiệm cao.",
    )
    if not reliable.empty:
        reliable["late_rate_pct"] = reliable["late_rate"] * 100
        reliable["low_review_rate_pct"] = reliable["low_review_rate"] * 100
        risk_map = px.scatter(
            reliable,
            x="late_rate_pct",
            y="low_review_rate_pct",
            size="gmv",
            color="label",
            color_discrete_map=LABEL_COLORS,
            hover_name="seller_id",
            hover_data={
                "seller_state": True,
                "n_eligible": ":,.0f",
                "score": ":.3f",
                "gmv": ":,.2f",
                "late_rate_pct": ":.1f",
                "low_review_rate_pct": ":.1f",
            },
            labels={
                "late_rate_pct": "Tỷ lệ giao trễ (%)",
                "low_review_rate_pct": "Tỷ lệ review thấp (%)",
                "label": "Khuyến nghị",
            },
            title="Rủi ro seller theo giao hàng và review",
        )
        st.plotly_chart(style_figure(risk_map, height=470), width="stretch")
    else:
        st.info("Các seller đang hiển thị chưa đủ dữ liệu để vẽ bản đồ quyết định.")

    left, right = st.columns([1, 2])
    label_counts = (
        scorecard["label"].value_counts().rename_axis("label").reset_index(name="sellers")
    )
    label_chart = px.bar(
        label_counts,
        x="sellers",
        y="label",
        orientation="h",
        color="label",
        color_discrete_map=LABEL_COLORS,
        title="Phân bố khuyến nghị",
        labels={"sellers": "Số seller", "label": "Nhãn"},
    )
    left.plotly_chart(style_figure(label_chart), width="stretch")

    weight_rows = pd.DataFrame(payload.get("weights", []))
    if not weight_rows.empty:
        weight_rows["Trọng số chuẩn hóa"] = (
            weight_rows["weight"] / weight_rows["weight"].sum()
        )
        weight_rows["Tiêu chí"] = weight_rows["criterion"].map(
            {"gmv": "GMV", "late_rate": "Giao đúng hạn", "low_review_rate": "Review tốt"}
        )
        weight_chart = px.bar(
            weight_rows,
            x="Trọng số chuẩn hóa",
            y="Tiêu chí",
            orientation="h",
            color="Tiêu chí",
            title="Trọng số đang áp dụng",
            text_auto=".0%",
        )
        weight_chart.update_xaxes(tickformat=".0%", range=[0, 1])
        right.plotly_chart(style_figure(weight_chart), width="stretch")

    section_intro(
        "Danh sách hành động ưu tiên",
        "Ưu tiên xem các seller có nhãn Review/Improve và GMV lớn; bảng chỉ hiển thị tối đa theo thanh điều khiển.",
    )
    priority = {"Review": 0, "Improve": 1, "Watch": 2, "Retain": 3,
                "Insufficient data - high GMV": 4, "Insufficient data": 5}
    display = scorecard.copy()
    display["_priority"] = display["label"].map(priority).fillna(9)
    display["late_rate"] = display["late_rate"] * 100
    display["low_review_rate"] = display["low_review_rate"] * 100
    display = display.sort_values(["_priority", "gmv"], ascending=[True, False])
    columns = [
        "rank", "seller_id", "seller_state", "seller_city", "gmv", "n_orders",
        "n_eligible", "late_rate", "low_review_rate", "score", "label", "action",
    ]
    st.dataframe(
        display[[column for column in columns if column in display.columns]],
        width="stretch",
        hide_index=True,
        column_config={
            **dataframe_config(),
            "rank": st.column_config.NumberColumn("Hạng", format="%d"),
            "seller_id": "Seller",
            "seller_state": "State",
            "seller_city": "City",
            "n_orders": st.column_config.NumberColumn("Số đơn", format="%d"),
            "n_eligible": st.column_config.NumberColumn("Đơn hợp lệ", format="%d"),
            "label": "Quyết định",
            "action": st.column_config.TextColumn("Hành động", width="large"),
        },
    )
    st.download_button(
        "Tải scorecard CSV",
        scorecard.to_csv(index=False).encode("utf-8-sig"),
        file_name="olist_seller_scorecard.csv",
        mime="text/csv",
    )

    with st.expander("Phương pháp chấm điểm và giới hạn diễn giải"):
        settings = config.get("settings", {})
        st.markdown(
            f"""
            - Seller cần tối thiểu **{int(settings.get('min_eligible_orders', 30))}** đơn giao hàng đủ điều kiện để được chấm điểm.
            - GMV được biến đổi `log(1 + GMV)`; mỗi tiêu chí được min-max trong phạm vi đang phân tích.
            - Các tiêu chí được chuẩn hóa theo trọng số và ánh xạ qua rule theo thứ tự ưu tiên.
            - Tỷ lệ giao trễ và review thấp chỉ được dùng trên order một seller để tránh quy kết sai grain.
            - Scorecard hỗ trợ ưu tiên điều tra, không chứng minh quan hệ nhân quả.
            """
        )
except Exception as exc:
    render_data_error(exc)
