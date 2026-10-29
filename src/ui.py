from __future__ import annotations

from collections.abc import Iterable

import streamlit as st


def configure_page(title: str, icon: str = "📊") -> None:
    st.set_page_config(page_title=title, page_icon=icon, layout="wide")


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
        "Cannot load analytics data. Start the DW database, apply "
        "sql/001_create_analytics_views.sql, and verify .env."
    )
    st.exception(exc)
    st.stop()

