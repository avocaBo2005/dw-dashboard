import pandas as pd
import streamlit as st

from src.api import timed_api_get
from src.transform import grand_total
from src.ui import configure_page, format_number, render_data_error


configure_page("Đánh giá hệ thống", "✅")
st.title("Đánh giá và đối soát hệ thống")
st.caption("Kiểm tra API, database, tính nhất quán KPI và thời gian phản hồi")

EXPECTED_ELIGIBLE = 96_470
EXPECTED_LATE = 6_534
EXPECTED_LATE_RATE = 6.77


def status_text(passed: bool) -> str:
    return "PASS" if passed else "FAIL"


if st.button("Chạy bộ đánh giá", type="primary"):
    try:
        results = []
        payloads = {}
        endpoints = [
            ("API health", "/api/v1/health", None),
            ("Database health", "/api/v1/db-health", None),
            (
                "Sales OLAP",
                "/api/v1/sale/analysis",
                {"dim": "time", "depth": 1, "status": "delivered"},
            ),
            (
                "Delivery OLAP",
                "/api/v1/delivery/analysis",
                {"dim": "time", "depth": 1},
            ),
            (
                "Delivery distribution",
                "/api/v1/delivery/distribution",
                {"dim": "time", "depth": 1},
            ),
            ("Review by delay", "/api/v1/reviews/by-delay", {"group": "flag"}),
        ]
        progress = st.progress(0)
        for index, (name, path, params) in enumerate(endpoints, start=1):
            payload, elapsed = timed_api_get(path, params)
            payloads[name] = payload
            results.append(
                {
                    "Hạng mục": name,
                    "Trạng thái": "PASS",
                    "Thời gian (ms)": round(elapsed, 2),
                    "Tiêu chí": "HTTP thành công và JSON hợp lệ",
                }
            )
            progress.progress(index / len(endpoints))

        api_ok = payloads["API health"].get("data", {}).get("status") == "ok"
        db_ok = payloads["Database health"].get("status") == "ok"
        sales_total = grand_total(payloads["Sales OLAP"])
        delivery_total = grand_total(payloads["Delivery OLAP"])
        distribution = payloads["Delivery distribution"]
        eligible = int(delivery_total.get("eligible_orders") or 0)
        late = int(distribution.get("summary", {}).get("late_orders") or 0)
        late_rate = float(distribution.get("summary", {}).get("late_rate") or 0)

        checks = [
            ("API sẵn sàng", api_ok, "health.status = ok"),
            ("Database kết nối", db_ok, "db-health.status = ok"),
            (
                "Sales có dữ liệu",
                int(sales_total.get("n_orders") or 0) > 0,
                "n_orders > 0",
            ),
            (
                "Delivery totals nhất quán",
                eligible == int(distribution.get("meta", {}).get("total") or -1),
                "eligible_orders = distribution.meta.total",
            ),
            (
                "Eligible orders khớp mốc ETL",
                eligible == EXPECTED_ELIGIBLE,
                f"{eligible:,} / {EXPECTED_ELIGIBLE:,}",
            ),
            (
                "Late orders khớp mốc ETL",
                late == EXPECTED_LATE,
                f"{late:,} / {EXPECTED_LATE:,}",
            ),
            (
                "Late rate khớp mốc ETL",
                abs(late_rate - EXPECTED_LATE_RATE) <= 0.01,
                f"{late_rate:.2f}% / {EXPECTED_LATE_RATE:.2f}%",
            ),
            (
                "Review đủ hai nhóm",
                {row.get("group") for row in payloads["Review by delay"].get("data", [])}
                == {"late", "not_late"},
                "late và not_late",
            ),
        ]
        check_frame = pd.DataFrame(
            [
                {"Kiểm tra": name, "Kết quả": status_text(passed), "Chi tiết": detail}
                for name, passed, detail in checks
            ]
        )
        result_frame = pd.DataFrame(results)

        passed_count = sum(passed for _, passed, _ in checks)
        metrics = st.columns(4)
        metrics[0].metric("Kiểm tra đạt", f"{passed_count}/{len(checks)}")
        metrics[1].metric("Eligible orders", format_number(eligible))
        metrics[2].metric("Late orders", format_number(late))
        metrics[3].metric("Late rate", f"{late_rate:.2f}%")

        st.subheader("Đối soát KPI")
        st.dataframe(check_frame, width="stretch", hide_index=True)
        st.subheader("Hiệu năng API")
        st.dataframe(result_frame, width="stretch", hide_index=True)
        st.caption(
            "Mốc đối soát lấy từ lần ETL đã được ghi nhận trong DW_DESIGN_HANDOVER. "
            "Nếu dữ liệu nguồn hoặc quy tắc ETL thay đổi, hãy cập nhật mốc tham chiếu."
        )
    except Exception as exc:
        render_data_error(exc)
else:
    st.info("Nhấn “Chạy bộ đánh giá” để thực hiện kiểm tra trên dữ liệu hiện tại.")

st.subheader("Hạn chế cần trình bày trong báo cáo")
st.markdown(
    """
- Trạng thái đơn là snapshot tại lần ETL gần nhất; chưa có lịch sử trạng thái/SCD.
- `SUM(price)` là giá trị mặt hàng, không phải lợi nhuận hay doanh thu thuần.
- Giao hàng có grain order nên không dùng để xếp hạng giao trễ theo seller.
- Chưa tích hợp payments và geolocation vào mô hình V1.
- ETL đang full refresh, chưa hỗ trợ incremental load.
- Cảnh báo DSS là rule-based và không chứng minh quan hệ nhân quả.
"""
)
