from __future__ import annotations

from datetime import date

import streamlit as st

from src.database import query_dataframe


def purchase_date_range() -> tuple[date, date]:
    bounds = query_dataframe(
        """
        SELECT MIN(purchase_date) AS min_date, MAX(purchase_date) AS max_date
        FROM analytics.v_delivery_detail
        """
    ).iloc[0]
    min_date = bounds["min_date"]
    max_date = bounds["max_date"]
    selected = st.sidebar.date_input(
        "Purchase date",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )
    if not isinstance(selected, (tuple, list)) or len(selected) != 2:
        st.warning("Select both a start date and an end date.")
        st.stop()
    return selected[0], selected[1]


def multiselect_from_query(
    label: str,
    sql: str,
    column: str,
) -> list[str]:
    values = query_dataframe(sql)[column].dropna().astype(str).tolist()
    return st.sidebar.multiselect(label, values)

