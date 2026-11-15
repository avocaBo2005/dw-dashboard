import plotly.express as px
import streamlit as st

from src.api import ApiError, api_get
from src.delivery_buffer import (
    POLICY_LABELS,
    curve_frame,
    segments_frame,
    summary_frame,
    tradeoff_frame,
)
from src.ui import (
    configure_page,
    format_number,
    format_percent,
    page_header,
    section_intro,
    status_badge,
    style_figure,
)


configure_page("Delivery Buffer", "🚚")
page_header(
    "Delivery Buffer Decision Support",
    "So sánh hiện trạng với buffer giao hàng chung và buffer theo bang để kiểm soát tỷ lệ giao trễ.",
    "DSS · Delivery policy",
)

STATE_CODES = [
    "AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG",
    "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR",
    "RS", "SC", "SE", "SP", "TO",
]
STATUS_LABELS = {"met": "Đạt", "missed": "Chưa đạt", "low_power": "Mẫu nhỏ"}


def show_policy_error(exc: Exception) -> None:
    detail = str(exc)
    if isinstance(exc, ApiError) and "404" in detail:
        st.error("Chưa có policy run phù hợp trong database.")
        st.info(
            "Hãy áp dụng migration Delivery Buffer và chạy pipeline profile/build ở backend. "
            "Dashboard chỉ đọc kết quả qua API, không tự tạo dữ liệu mô hình."
        )
    else:
        st.error("Không thể tải kết quả Delivery Buffer từ backend.")
    with st.expander("Chi tiết kỹ thuật"):
        st.code(detail)
    st.stop()


st.sidebar.subheader("Mục tiêu chính sách")
selected_state = st.sidebar.selectbox("Customer state", ["Tổng quan", *STATE_CODES])
target_percent = st.sidebar.number_input(
    "Tỷ lệ trễ mục tiêu (%)", min_value=0.1, max_value=99.9, value=5.0, step=0.1
)
k_min, k_max = st.sidebar.slider(
    "Khoảng buffer k (ngày)",
    min_value=-30,
    max_value=30,
    value=(-30, 30),
)
run_id_value = st.sidebar.number_input(
    "Run ID (0 = active run)", min_value=0, value=0, step=1
)

params = {
    "state": None if selected_state == "Tổng quan" else selected_state,
    "target_late_rate": target_percent / 100,
    "k_min": k_min,
    "k_max": k_max,
    "run_id": int(run_id_value) or None,
}

try:
    payload = api_get("/api/v1/dss/delivery-buffer", params)
except Exception as exc:
    show_policy_error(exc)

meta = payload.get("meta", {})
status_badge(f"RUN {meta.get('run_id', '—')}", "info")
st.caption(
    f"Train: {' → '.join(meta.get('learn_period', [])) or '—'} · "
    f"Test: {' → '.join(meta.get('test_period', [])) or '—'} · "
    f"Mục tiêu: {format_percent(meta.get('target_late_rate'), 1, fraction=True)}"
)

if selected_state == "Tổng quan":
    summary = summary_frame(payload)
    segments = segments_frame(payload)
    if summary.empty:
        st.warning("API không trả về bảng tổng hợp chính sách.")
        st.stop()

    indexed = summary.set_index("policy")
    cards = st.columns(4)
    cards[0].metric("Mục tiêu tỷ lệ trễ", f"{target_percent:.1f}%")
    for column, policy in zip(cards[1:], ("current_k0", "global_k", "state_k"), strict=True):
        value = indexed.loc[policy, "Tỷ lệ trễ (%)"] if policy in indexed.index else None
        column.metric(POLICY_LABELS[policy], format_percent(value, 2))

    section_intro(
        "So sánh chính sách",
        "Chính sách tốt cần giảm tỷ lệ trễ nhưng không kéo dài ngày cam kết quá mức cần thiết.",
    )
    comparison = px.scatter(
        summary,
        x="Ngày cam kết TB",
        y="Tỷ lệ trễ (%)",
        color="Chính sách",
        size="Số bang đánh giá",
        text="Chính sách",
        hover_data=["Số bang đạt mục tiêu", "Tỷ lệ đơn thuộc bang đạt (%)"],
        title="Tỷ lệ giao trễ và thời gian cam kết",
    )
    comparison.add_hline(
        y=target_percent,
        line_dash="dot",
        line_color="#d1495b",
        annotation_text=f"Mục tiêu {target_percent:.1f}%",
    )
    comparison.update_traces(textposition="top center")
    st.plotly_chart(style_figure(comparison, height=470), width="stretch")
    st.dataframe(
        summary.drop(columns=["policy"]),
        width="stretch",
        hide_index=True,
        column_config={
            "Tỷ lệ trễ (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "Ngày cam kết TB": st.column_config.NumberColumn(format="%.2f"),
            "Tỷ lệ đơn thuộc bang đạt (%)": st.column_config.NumberColumn(format="%.2f%%"),
            "Tỷ lệ trễ cao nhất (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

    section_intro(
        "Đánh giá theo bang",
        "Low power nghĩa là số đơn test chưa đủ để kết luận chắc chắn; fallback dùng mô hình chung.",
    )
    if segments.empty:
        st.info("Không có kết quả đánh giá theo bang.")
    else:
        status_columns = [column for column in segments.columns if column.endswith("trạng thái")]
        display_segments = segments.copy()
        for column in status_columns:
            display_segments[column] = display_segments[column].map(STATUS_LABELS).fillna(
                display_segments[column]
            )
        st.dataframe(display_segments, width="stretch", hide_index=True)
        st.download_button(
            "Tải kết quả theo bang CSV",
            segments.to_csv(index=False).encode("utf-8-sig"),
            "olist_delivery_buffer_segments.csv",
            "text/csv",
        )

    section_intro(
        "Đánh đổi safety margin",
        "Mỗi điểm là kết quả của một lần build với safety margin khác nhau trên cùng giai đoạn test.",
    )
    try:
        tradeoff_payload = api_get("/api/v1/dss/delivery-buffer/tradeoff")
        tradeoff = tradeoff_frame(tradeoff_payload)
        if len(tradeoff) >= 2:
            tradeoff_chart = px.line(
                tradeoff.sort_values("promised_days_avg"),
                x="promised_days_avg",
                y="late_rate_pct",
                markers=True,
                title="Trade-off tỷ lệ trễ và ngày cam kết",
                hover_data=["safety_margin_pct", "n_segments_met", "pct_orders_in_met_pct"],
                labels={
                    "promised_days_avg": "Ngày cam kết TB",
                    "late_rate_pct": "Tỷ lệ trễ (%)",
                    "safety_margin_pct": "Safety margin (%)",
                },
            )
            tradeoff_chart.add_hline(y=target_percent, line_dash="dot", line_color="#d1495b")
            st.plotly_chart(style_figure(tradeoff_chart), width="stretch")
        elif len(tradeoff) == 1:
            st.info(
                "Hiện chỉ có một safety margin nên chưa đủ điểm để vẽ đường trade-off. "
                "Cần chạy margin sweep ở pipeline backend."
            )
        else:
            st.info("Chưa có dữ liệu trade-off.")
        if not tradeoff.empty:
            columns = [
                "run_id", "safety_margin_pct", "late_rate_pct", "promised_days_avg",
                "n_segments_scored", "n_segments_met", "pct_orders_in_met_pct",
                "worst_segment", "worst_late_rate_pct",
            ]
            st.dataframe(
                tradeoff[[column for column in columns if column in tradeoff.columns]],
                width="stretch",
                hide_index=True,
            )
            st.download_button(
                "Tải trade-off CSV",
                tradeoff.to_csv(index=False).encode("utf-8-sig"),
                "olist_delivery_buffer_tradeoff.csv",
                "text/csv",
            )
    except Exception as exc:
        st.warning(f"Không tải được dữ liệu trade-off: {exc}")
else:
    data = payload.get("data", {})
    segment = data.get("segment", {})
    current = data.get("current") or {}
    recommended = data.get("recommended") or {}
    global_policy = data.get("global_comparison") or {}

    section_intro(
        f"Chính sách cho bang {selected_state}",
        "Recommended dùng mô hình theo bang; global comparison áp dụng cùng một k cho mọi bang.",
    )
    status_badge(
        "CÓ THỂ ĐẠT MỤC TIÊU" if segment.get("attainable") else "CHƯA ĐẠT TRONG KHOẢNG K",
        "ok" if segment.get("attainable") else "warn",
    )
    if segment.get("fallback"):
        st.info("Bang này chưa đủ dữ liệu học riêng nên recommendation đang dùng mô hình chung.")

    cards = st.columns(4)
    cards[0].metric("Hiện trạng", format_percent(current.get("late_rate_test"), 2, fraction=True))
    cards[1].metric("k đề xuất", format_number(recommended.get("k")))
    cards[2].metric(
        "Tỷ lệ trễ đề xuất",
        format_percent(recommended.get("late_rate_test"), 2, fraction=True),
    )
    cards[3].metric("Ngày cam kết", format_number(recommended.get("promised_days"), 2))

    curve = curve_frame(payload)
    if curve.empty:
        st.info("Không có đường cong chính sách cho bang này.")
    else:
        chart_data = curve.melt(
            id_vars=["k"],
            value_vars=["late_rate_train_pct", "late_rate_test_pct"],
            var_name="Tập dữ liệu",
            value_name="Tỷ lệ trễ (%)",
        )
        chart_data["Tập dữ liệu"] = chart_data["Tập dữ liệu"].map(
            {"late_rate_train_pct": "Train", "late_rate_test_pct": "Test"}
        )
        curve_chart = px.line(
            chart_data,
            x="k",
            y="Tỷ lệ trễ (%)",
            color="Tập dữ liệu",
            markers=True,
            title=f"Đường cong buffer của {selected_state}",
            labels={"k": "Buffer k (ngày)"},
        )
        curve_chart.add_hline(y=target_percent, line_dash="dot", line_color="#d1495b")
        for name, values, color in (
            ("Hiện trạng", current, "#607086"),
            ("Đề xuất", recommended, "#138a66"),
            ("Buffer chung", global_policy, "#4c78a8"),
        ):
            if values.get("k") is not None:
                curve_chart.add_vline(
                    x=values["k"], line_dash="dash", line_color=color,
                    annotation_text=f"{name}: k={values['k']}",
                )
        st.plotly_chart(style_figure(curve_chart, height=480), width="stretch")
        st.dataframe(
            curve,
            width="stretch",
            hide_index=True,
            column_config={
                "late_rate_train_pct": st.column_config.NumberColumn("Train (%)", format="%.2f%%"),
                "late_rate_test_pct": st.column_config.NumberColumn("Test (%)", format="%.2f%%"),
                "promised_days": st.column_config.NumberColumn("Ngày cam kết", format="%.2f"),
                "expected_review": st.column_config.NumberColumn("Review kỳ vọng", format="%.3f"),
            },
        )

with st.expander("Giả định và giới hạn diễn giải"):
    assumptions = meta.get("assumptions", [])
    if assumptions:
        st.markdown("\n".join(f"- {item}" for item in assumptions))
    else:
        st.write("API không cung cấp danh sách giả định.")
    st.caption(
        f"Số đơn train: {format_number(meta.get('n_train'))} · "
        f"Số đơn test: {format_number(meta.get('n_test'))} · "
        f"Safety margin: {format_percent(meta.get('safety_margin'), 2, fraction=True)}"
    )
