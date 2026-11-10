from __future__ import annotations

from collections.abc import Iterable
from html import escape
from typing import Any

import plotly.graph_objects as go
import streamlit as st


_DASHBOARD_STYLES = """
<style>
:root {
    --ink: #10233f;
    --muted: #607086;
    --brand: #176b87;
    --line: #dce5ec;
    --surface: #ffffff;
}
.block-container { max-width: 1440px; padding-top: 3.75rem; padding-bottom: 3rem; }
[data-testid="stSidebar"] { border-right: 1px solid var(--line); }
[data-testid="stSidebar"] .block-container { padding-top: 1.5rem; }
.dw-brand {
    padding: .85rem 1rem; margin-bottom: 1.2rem; color: white;
    background: linear-gradient(135deg, #103b5c 0%, #176b87 62%, #1d8aa2 100%);
    border-radius: 14px; box-shadow: 0 10px 24px rgba(16, 59, 92, .18);
}
.dw-brand small { display: block; opacity: .78; margin-top: .2rem; }
.dw-eyebrow {
    color: var(--brand); font-size: .77rem; font-weight: 750;
    letter-spacing: .11em; text-transform: uppercase; margin-bottom: .35rem;
    padding-top: 1.15rem;
}
.dw-page-title { color: var(--ink); font-size: 2.15rem; font-weight: 760; line-height: 1.12; margin: 0; }
.dw-page-subtitle { color: var(--muted); font-size: 1rem; margin: .55rem 0 1.45rem; max-width: 860px; }
.dw-section-note { color: var(--muted); margin-top: -.55rem; margin-bottom: 1rem; }
.dw-badge {
    display: inline-flex; padding: .3rem .6rem; border-radius: 999px;
    font-size: .77rem; font-weight: 700; line-height: 1;
}
.dw-badge--ok { color: #0f6b45; background: #dcfce7; }
.dw-badge--warn { color: #9a5700; background: #fff4d6; }
.dw-badge--bad { color: #a12828; background: #fee2e2; }
.dw-badge--info { color: #155e75; background: #cffafe; }
div[data-testid="stMetric"] {
    min-height: 128px; padding: 1.05rem 1.15rem; background: var(--surface);
    border: 1px solid var(--line); border-top: 3px solid #47a6b7;
    border-radius: 12px; box-shadow: 0 4px 14px rgba(15, 35, 63, .045);
}
div[data-testid="stMetric"]:hover { box-shadow: 0 8px 22px rgba(15, 35, 63, .09); }
[data-testid="stMetricLabel"] { min-height: 2.35rem; color: var(--muted); font-weight: 650; }
[data-testid="stMetricValue"] { color: var(--ink); font-weight: 730; }
[data-testid="stMetricLabel"] [data-testid="stMarkdownContainer"],
[data-testid="stMetricLabel"] p { white-space: normal !important; line-height: 1.2; }
div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"],
div[data-testid="stTable"], details[data-testid="stExpander"] {
    background: var(--surface); border: 1px solid var(--line); border-radius: 12px;
    box-shadow: 0 4px 14px rgba(15, 35, 63, .035); overflow: hidden;
}
div[data-testid="stPlotlyChart"] { padding: .35rem; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div,
div[data-testid="stDateInput"] input, div[data-testid="stNumberInput"] input,
div[data-testid="stTextInput"] input { border-color: #c7d5df !important; border-radius: 8px !important; }
div[data-testid="stAlert"] { border-radius: 10px; }
.stButton > button[kind="primary"] { box-shadow: 0 5px 14px rgba(23, 107, 135, .2); }
</style>
"""


def configure_page(title: str, icon: str = "📊") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")
    st.markdown(_DASHBOARD_STYLES, unsafe_allow_html=True)
    st.sidebar.markdown(
        """
        <div class="dw-brand">
          <strong>OLIST · DW/DSS</strong>
          <small>CO4031 · Học kỳ 261</small>
        </div>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, subtitle: str, eyebrow: str) -> None:
    st.markdown(
        f"""
        <div class="dw-eyebrow">{escape(eyebrow)}</div>
        <h1 class="dw-page-title">{escape(title)}</h1>
        <p class="dw-page-subtitle">{escape(subtitle)}</p>
        """,
        unsafe_allow_html=True,
    )


def section_intro(title: str, note: str | None = None) -> None:
    st.subheader(title)
    if note:
        st.markdown(f'<p class="dw-section-note">{escape(note)}</p>', unsafe_allow_html=True)


def status_badge(label: str, tone: str = "info") -> None:
    safe_tone = tone if tone in {"ok", "warn", "bad", "info"} else "info"
    st.markdown(
        f'<span class="dw-badge dw-badge--{safe_tone}">{escape(label)}</span>',
        unsafe_allow_html=True,
    )


def format_number(value: object, decimals: int = 0) -> str:
    if value is None:
        return "—"
    try:
        number = float(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{number:,.{decimals}f}"


def format_percent(value: object, decimals: int = 1, fraction: bool = False) -> str:
    if value is None:
        return "—"
    try:
        number = float(value) * (100 if fraction else 1)
    except (TypeError, ValueError):
        return "—"
    return f"{number:,.{decimals}f}%"


def render_metrics(metrics: Iterable[tuple[str, object, str | None]]) -> None:
    items = list(metrics)
    if not items:
        return
    columns = st.columns(len(items))
    for column, (label, value, suffix) in zip(columns, items, strict=True):
        display = str(value) if suffix is None else f"{value}{suffix}"
        column.metric(label, display)


def style_figure(figure: go.Figure, *, height: int = 390) -> go.Figure:
    figure.update_layout(
        height=height,
        margin=dict(l=22, r=22, t=65, b=24),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter, system-ui, sans-serif", color="#40536a"),
        title_font=dict(size=17, color="#10233f"),
        legend_title_text="",
        hoverlabel=dict(bgcolor="#10233f", font_color="white"),
    )
    figure.update_xaxes(showgrid=False, linecolor="#dce5ec")
    figure.update_yaxes(gridcolor="#e8eef3", zeroline=False)
    return figure


def dataframe_config() -> dict[str, Any]:
    return {
        "late_rate": st.column_config.NumberColumn("Tỷ lệ trễ", format="%.2f%%"),
        "low_review_rate": st.column_config.NumberColumn("Review thấp", format="%.1f%%"),
        "late_low_review_pct": st.column_config.NumberColumn("Review thấp", format="%.1f%%"),
        "score": st.column_config.ProgressColumn(
            "Điểm DSS", min_value=0.0, max_value=1.0, format="%.3f"
        ),
        "gmv": st.column_config.NumberColumn("GMV", format="%.2f"),
        "total_price": st.column_config.NumberColumn("Giá trị mặt hàng", format="%.2f"),
        "eligible_orders": st.column_config.NumberColumn("Đơn hợp lệ", format="%d"),
    }


def render_data_error(exc: Exception) -> None:
    st.error(
        "Không thể tải dữ liệu. Hãy chạy PostgreSQL/ETL, áp dụng view của "
        "backend, khởi động API và kiểm tra API_BASE_URL trong .env."
    )
    with st.expander("Chi tiết kỹ thuật"):
        st.exception(exc)
    st.stop()
