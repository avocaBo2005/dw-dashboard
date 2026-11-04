from __future__ import annotations

from collections.abc import Iterable

import streamlit as st


_DASHBOARD_STYLES = """
<style>
/* KPI cards */
div[data-testid="stMetric"] {
    min-height: 132px;
    padding: 1.15rem 1.25rem;
    background: #ffffff;
    border: 1px solid #d7dee9;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

div[data-testid="stMetric"]:hover {
    border-color: #94a3b8;
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.08);
}

[data-testid="stMetricLabel"] {
    min-height: 2.5rem;
    color: #475569;
    font-weight: 600;
}

[data-testid="stMetricLabel"] [data-testid="stMarkdownContainer"],
[data-testid="stMetricLabel"] p {
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    line-height: 1.25;
}

/* Charts, tables and expandable content */
div[data-testid="stPlotlyChart"],
div[data-testid="stDataFrame"],
div[data-testid="stTable"],
details[data-testid="stExpander"] {
    background: #ffffff;
    border: 1px solid #d7dee9;
    border-radius: 12px;
    box-shadow: 0 2px 8px rgba(15, 23, 42, 0.04);
    overflow: hidden;
}

div[data-testid="stPlotlyChart"] {
    padding: 0.5rem;
}

/* Make interactive filters easier to distinguish. */
div[data-baseweb="select"] > div,
div[data-baseweb="input"] > div,
div[data-testid="stDateInput"] input,
div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input {
    border-color: #cbd5e1 !important;
    border-radius: 8px !important;
}

div[data-testid="stAlert"] {
    border: 1px solid rgba(100, 116, 139, 0.3);
    border-radius: 10px;
}

/* Preserve clear card boundaries in dark mode. */
@media (prefers-color-scheme: dark) {
    div[data-testid="stMetric"],
    div[data-testid="stPlotlyChart"],
    div[data-testid="stDataFrame"],
    div[data-testid="stTable"],
    details[data-testid="stExpander"] {
        background: rgba(30, 41, 59, 0.45);
        border-color: #475569;
    }
}
</style>
"""


def configure_page(title: str, icon: str = "📊") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(_DASHBOARD_STYLES, unsafe_allow_html=True)


def format_number(value: object, decimals: int = 0) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.{decimals}f}"


def render_metrics(metrics: Iterable[tuple[str, object, str | None]]) -> None:
    items = list(metrics)
    columns = st.columns(len(items))
    for column, (label, value, suffix) in zip(columns, items, strict=True):
        display = str(value) if suffix is None else f"{value}{suffix}"
        column.metric(label, display)


def render_data_error(exc: Exception) -> None:
    st.error(
        "Không thể tải dữ liệu. Hãy chạy PostgreSQL/ETL, áp dụng view của "
        "backend, khởi động API và kiểm tra API_BASE_URL trong .env."
    )
    st.exception(exc)
    st.stop()
