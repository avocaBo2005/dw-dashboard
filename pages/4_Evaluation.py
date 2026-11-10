from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import streamlit as st

from src.api import timed_api_get
from src.evaluation import evaluate_payloads, response_rating
from src.ui import (
    configure_page,
    format_number,
    format_percent,
    page_header,
    section_intro,
    status_badge,
    style_figure,
)


configure_page("Đánh giá hệ thống", "✅")
page_header(
    "Đánh giá và đối soát",
    "Kiểm tra end-to-end từ API, kho dữ liệu và OLAP đến DSS; đồng thời ghi nhận độ trễ phản hồi thực tế.",
    "Quality gate · Reconciliation",
)

ENDPOINTS = [
    ("API health", "/api/v1/health", None),
    ("Database health", "/api/v1/db-health", None),
    ("Sales OLAP", "/api/v1/sale/analysis", {"dim": "time", "depth": 1, "status": "delivered"}),
    ("Delivery OLAP", "/api/v1/delivery/analysis", {"dim": "time", "depth": 1}),
    ("Delivery distribution", "/api/v1/delivery/distribution", {"dim": "time", "depth": 1}),
    ("Review by delay", "/api/v1/reviews/by-delay", {"group": "flag"}),
    ("DSS config", "/api/v1/dss/config", None),
    ("DSS scorecard", "/api/v1/dss/seller-scorecard", {"limit": 10}),
]


def run_evaluation() -> dict:
    payloads = {}
    endpoint_rows = []
    progress = st.progress(0, text="Đang khởi tạo bộ đánh giá...")
    for index, (name, path, params) in enumerate(ENDPOINTS, start=1):
        try:
            payload, elapsed = timed_api_get(path, params)
            payloads[name] = payload
            endpoint_rows.append(
                {
                    "Endpoint": name,
                    "Trạng thái": "PASS",
                    "Thời gian (ms)": round(elapsed, 2),
                    "Mức đáp ứng": response_rating(elapsed),
                    "Chi tiết": "HTTP thành công, JSON object hợp lệ",
                }
            )
        except Exception as exc:
            payloads[name] = {}
            endpoint_rows.append(
                {
                    "Endpoint": name,
                    "Trạng thái": "FAIL",
                    "Thời gian (ms)": None,
                    "Mức đáp ứng": "Không đo được",
                    "Chi tiết": str(exc)[:240],
                }
            )
        progress.progress(index / len(ENDPOINTS), text=f"Đã kiểm tra {name}")
    progress.empty()
    checks, metrics = evaluate_payloads(payloads)
    return {
        "run_at": datetime.now(ZoneInfo("Asia/Ho_Chi_Minh")).isoformat(timespec="seconds"),
        "checks": [check.as_row() for check in checks],
        "metrics": metrics,
        "endpoints": endpoint_rows,
    }


action_col, note_col = st.columns([1, 3])
with action_col:
    run_clicked = st.button("Chạy bộ đánh giá", type="primary", width="stretch")
with note_col:
    st.caption(
        "Bài đo bỏ qua cache UI và dùng toàn bộ dữ liệu làm mốc đối soát. "
        "Kết quả được giữ trong phiên để có thể tải CSV."
    )

if run_clicked:
    st.session_state["evaluation_result"] = run_evaluation()

result = st.session_state.get("evaluation_result")
if result:
    metrics = result["metrics"]
    checks = pd.DataFrame(result["checks"])
    endpoints = pd.DataFrame(result["endpoints"])
    endpoint_passed = int(endpoints["Trạng thái"].eq("PASS").sum())
    passed_all = metrics["passed"] == metrics["total"] and endpoint_passed == len(endpoints)

    status_badge(
        "SẴN SÀNG DEMO" if passed_all else "CẦN KIỂM TRA",
        "ok" if passed_all else "warn",
    )
    st.caption(f"Lần chạy gần nhất: {result['run_at']}")

    cards = st.columns(5)
    cards[0].metric("Quality checks", f"{metrics['passed']}/{metrics['total']}")
    cards[1].metric("API endpoints", f"{endpoint_passed}/{len(endpoints)}")
    cards[2].metric("Eligible orders", format_number(metrics["eligible"]))
    cards[3].metric("Late orders", format_number(metrics["late"]))
    cards[4].metric("Late rate", format_percent(metrics["late_rate"], 2))

    section_intro(
        "Kết quả kiểm tra",
        "FAIL ở mốc ETL có thể do dữ liệu hoặc quy tắc ETL đã thay đổi; không nên sửa UI để ép kết quả.",
    )
    st.dataframe(
        checks,
        width="stretch",
        hide_index=True,
        column_config={
            "Kết quả": st.column_config.TextColumn("Kết quả", width="small"),
            "Kiểm tra": st.column_config.TextColumn("Kiểm tra", width="medium"),
            "Kỳ vọng": st.column_config.TextColumn("Kỳ vọng", width="medium"),
        },
    )

    section_intro(
        "Hiệu năng API",
        "Ngưỡng trình bày: tốt ≤ 500 ms, chấp nhận ≤ 1.5 s, trên 1.5 s cần xem EXPLAIN ANALYZE và index.",
    )
    measured = endpoints.dropna(subset=["Thời gian (ms)"])
    if not measured.empty:
        latency_chart = px.bar(
            measured.sort_values("Thời gian (ms)"),
            x="Thời gian (ms)",
            y="Endpoint",
            orientation="h",
            color="Mức đáp ứng",
            color_discrete_map={"Tốt": "#138a66", "Chấp nhận": "#f59e0b", "Cần tối ưu": "#d1495b"},
            text_auto=".0f",
            title="Độ trễ phản hồi không qua cache",
        )
        latency_chart.add_vline(x=500, line_dash="dot", line_color="#138a66")
        latency_chart.add_vline(x=1_500, line_dash="dot", line_color="#d1495b")
        st.plotly_chart(style_figure(latency_chart, height=430), width="stretch")
    st.dataframe(
        endpoints,
        width="stretch",
        hide_index=True,
        column_config={
            "Thời gian (ms)": st.column_config.NumberColumn("Thời gian (ms)", format="%.2f"),
            "Chi tiết": st.column_config.TextColumn("Chi tiết", width="large"),
        },
    )

    left, right = st.columns(2)
    left.download_button(
        "Tải kết quả đối soát CSV",
        checks.to_csv(index=False).encode("utf-8-sig"),
        "olist_evaluation_checks.csv",
        "text/csv",
        width="stretch",
    )
    right.download_button(
        "Tải kết quả hiệu năng CSV",
        endpoints.to_csv(index=False).encode("utf-8-sig"),
        "olist_api_performance.csv",
        "text/csv",
        width="stretch",
    )
else:
    st.info("Nhấn “Chạy bộ đánh giá” để kiểm tra hệ thống trên dữ liệu hiện tại.")

section_intro("Khung đánh giá dùng trong báo cáo")
tab_correctness, tab_performance, tab_usefulness, tab_limits = st.tabs(
    ["Độ đúng", "Hiệu năng", "Tính hữu ích", "Hạn chế"]
)
with tab_correctness:
    st.markdown(
        """
        - Kiểm tra sức khỏe API và kết nối PostgreSQL.
        - Đối soát tổng delivery giữa OLAP và distribution, tránh cộng nhầm subtotal từ `ROLLUP`.
        - So sánh eligible orders, late orders và late rate với mốc ETL đã xác nhận.
        - Xác nhận review có đủ hai nhóm và DSS trả scorecard cùng cấu hình trọng số.
        """
    )
with tab_performance:
    st.markdown(
        """
        - Đo trực tiếp 8 endpoint, không dùng cache 5 phút của dashboard.
        - Endpoint trên 1.5 giây cần được kiểm tra bằng `EXPLAIN (ANALYZE, BUFFERS)`.
        - Kết quả phụ thuộc máy chạy, kết nối và trạng thái cache của PostgreSQL nên cần ghi môi trường đo.
        """
    )
with tab_usefulness:
    st.markdown(
        """
        - Dashboard hỗ trợ roll-up/drill-down theo thời gian, địa lý và sản phẩm.
        - Delivery và review giúp xác định vùng có trải nghiệm kém với quy mô đủ lớn.
        - DSS xếp hạng seller, giải thích trọng số/rule và cung cấp hành động ưu tiên có thể tải xuống.
        """
    )
with tab_limits:
    st.markdown(
        """
        - Order status là snapshot; ETL hiện full refresh, chưa có SCD và incremental load.
        - `SUM(price)` là giá trị mặt hàng, không phải lợi nhuận hoặc doanh thu thuần.
        - Seller score chỉ dùng order một seller để bảo toàn grain, vì vậy không bao phủ toàn bộ order.
        - Chưa tích hợp payments/geolocation; dữ liệu Olist là dữ liệu lịch sử.
        - DSS rule-based giúp ưu tiên điều tra, không chứng minh quan hệ nhân quả.
        """
    )
