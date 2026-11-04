from __future__ import annotations

from datetime import date
from typing import Any

import streamlit as st

from src.api import api_get


MIN_DATE = date(2016, 9, 1)
MAX_DATE = date(2018, 12, 31)


def purchase_date_range() -> tuple[date, date]:
    selected = st.sidebar.date_input(
        "Khoảng ngày mua",
        value=(MIN_DATE, MAX_DATE),
        min_value=MIN_DATE,
        max_value=MAX_DATE,
    )
    if not isinstance(selected, (tuple, list)) or len(selected) != 2:
        st.warning("Hãy chọn cả ngày bắt đầu và ngày kết thúc.")
        st.stop()
    return selected[0], selected[1]


def date_params(date_from: date, date_to: date) -> dict[str, str]:
    return {"from": date_from.isoformat(), "to": date_to.isoformat()}


def sales_status_filter() -> list[str]:
    statuses = [
        "delivered",
        "shipped",
        "invoiced",
        "processing",
        "approved",
        "created",
        "canceled",
        "unavailable",
    ]
    return st.sidebar.multiselect("Trạng thái đơn", statuses, default=["delivered"])


def analysis_options(
    endpoint: str,
    dimension: str,
    key: str,
    params: dict[str, Any] | None = None,
) -> list[str]:
    query = {"dim": dimension, "depth": 1, **(params or {})}
    payload = api_get(endpoint, query)
    values = {
        item.get("keys", {}).get(key)
        for item in payload.get("data", [])
        if item.get("level") == 1
    }
    return sorted(str(value) for value in values if value not in (None, ""))
