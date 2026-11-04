import pandas as pd
import plotly.express as px
import streamlit as st

from src.api import api_get
from src.filters import date_params, purchase_date_range
from src.transform import level_frame
from src.ui import configure_page, render_data_error


configure_page("Decision Support", "🎯")
st.title("Hỗ trợ ra quyết định")
st.caption("Ưu tiên customer state cần điều tra dựa trên volume, giao trễ và review")

min_orders = st.sidebar.number_input("Số đơn tối thiểu", 10, 100000, 500, 50)
delay_threshold = st.sidebar.slider("Ngưỡng cảnh báo giao trễ (%)", 0.0, 30.0, 8.0, 0.5)
review_threshold = st.sidebar.slider("Ngưỡng điểm review khi trễ", 1.0, 5.0, 3.0, 0.1)
low_review_threshold = st.sidebar.slider("Ngưỡng review thấp (%)", 0.0, 100.0, 40.0, 1.0)

try:
    date_from, date_to = purchase_date_range()
    common = date_params(date_from, date_to)
    delivery_payload = api_get(
        "/api/v1/delivery/analysis",
        {**common, "dim": "customer_geo", "depth": 1},
    )
    states = level_frame(delivery_payload, 1)
    states = states[states["eligible_orders"] >= min_orders].copy()
    if states.empty:
        st.info("Không có customer state đạt ngưỡng volume đã chọn.")
        st.stop()

    review_metrics = []
    with st.spinner("Đang tổng hợp review theo customer state..."):
        for state in states["customer_state"].dropna().astype(str):
            review_payload = api_get(
                "/api/v1/reviews/by-delay",
                {**common, "group": "flag", "state": state},
            )
            late_row = next(
                (row for row in review_payload.get("data", []) if row.get("group") == "late"),
                {},
            )
            review_metrics.append(
                {
                    "customer_state": state,
                    "late_avg_review": late_row.get("avg_score"),
                    "late_low_review_pct": (
                        late_row.get("low_review_rate") * 100
                        if late_row.get("low_review_rate") is not None
                        else None
                    ),
                }
            )

    decision = states.merge(pd.DataFrame(review_metrics), on="customer_state", how="left")
    decision["delivery_alert"] = decision["late_rate"] >= delay_threshold
    decision["review_alert"] = decision["late_avg_review"].lt(review_threshold).fillna(False)
    decision["low_review_alert"] = (
        decision["late_low_review_pct"].ge(low_review_threshold).fillna(False)
    )
    decision["priority_score"] = (
        decision["delivery_alert"].astype(int) * 2
        + decision["review_alert"].astype(int)
        + decision["low_review_alert"].astype(int)
    )
    decision["khuyến nghị"] = "Theo dõi"
    decision.loc[decision["delivery_alert"], "khuyến nghị"] = (
        "Kiểm tra năng lực giao hàng và vùng phục vụ"
    )
    decision.loc[
        decision["review_alert"] | decision["low_review_alert"], "khuyến nghị"
    ] = "Phân tích phản hồi và chất lượng trải nghiệm"
    decision.loc[
        decision["delivery_alert"]
        & (decision["review_alert"] | decision["low_review_alert"]),
        "khuyến nghị",
    ] = "Ưu tiên cao: điều tra đồng thời giao hàng và trải nghiệm"

    flagged = decision[decision["priority_score"] > 0].sort_values(
        ["priority_score", "eligible_orders"], ascending=[False, False]
    )
    metrics = st.columns(3)
    metrics[0].metric("State được phân tích", f"{len(decision):,}")
    metrics[1].metric("State bị cảnh báo", f"{len(flagged):,}")
    metrics[2].metric("Ưu tiên cao", f"{(decision['priority_score'] >= 3).sum():,}")

    st.plotly_chart(
        px.scatter(
            decision,
            x="late_rate",
            y="late_avg_review",
            size="eligible_orders",
            color="priority_score",
            hover_name="customer_state",
            hover_data=["late_orders", "late_low_review_pct"],
            title="Ma trận rủi ro theo customer state",
            labels={
                "late_rate": "Tỷ lệ giao trễ (%)",
                "late_avg_review": "Điểm review TB khi giao trễ",
                "priority_score": "Điểm ưu tiên",
            },
        ),
        width="stretch",
    )
    st.subheader("Danh sách hành động ưu tiên")
    columns = [
        "customer_state",
        "eligible_orders",
        "late_orders",
        "late_rate",
        "late_avg_review",
        "late_low_review_pct",
        "priority_score",
        "khuyến nghị",
    ]
    st.dataframe(flagged[columns], width="stretch", hide_index=True)
    st.caption(
        "Các rule dùng để ưu tiên điều tra, không chứng minh quan hệ nhân quả. "
        "Không quy trách nhiệm giao trễ cho seller."
    )
except Exception as exc:
    render_data_error(exc)
