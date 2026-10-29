from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.config import DatabaseSettings


@st.cache_resource
def get_engine() -> Engine:
    settings = DatabaseSettings.from_env()
    return create_engine(
        settings.sqlalchemy_url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={settings.schema},dw,public"},
    )


@st.cache_data(ttl=300, show_spinner=False)
def _query_dataframe(
    sql: str, params_items: tuple[tuple[str, Any], ...]
) -> pd.DataFrame:
    params = dict(params_items)
    with get_engine().connect() as connection:
        return pd.read_sql_query(text(sql), connection, params=params)


def query_dataframe(
    sql: str, params: dict[str, Any] | None = None
) -> pd.DataFrame:
    params_items = tuple(sorted((params or {}).items()))
    return _query_dataframe(sql, params_items)


def check_connection() -> None:
    with get_engine().connect() as connection:
        connection.execute(text("SELECT 1"))

