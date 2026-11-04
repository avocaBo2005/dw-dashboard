from __future__ import annotations

from time import perf_counter
from typing import Any

import requests
import streamlit as st

from src.config import DashboardSettings


class ApiError(RuntimeError):
    """Raised when the dashboard API cannot provide a valid response."""


def _request(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    settings = DashboardSettings.from_env()
    url = f"{settings.api_base_url}/{path.lstrip('/')}"
    try:
        response = requests.get(url, params=params, timeout=settings.timeout_seconds)
        response.raise_for_status()
    except requests.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            detail = f" Response: {exc.response.text[:300]}"
        raise ApiError(f"GET {url} failed.{detail}") from exc
    try:
        payload = response.json()
    except ValueError as exc:
        raise ApiError(f"GET {url} did not return JSON") from exc
    if not isinstance(payload, dict):
        raise ApiError(f"GET {url} returned an unexpected payload")
    return payload


@st.cache_data(ttl=300, show_spinner=False)
def _cached_get(path: str, params_items: tuple[tuple[str, Any], ...]) -> dict[str, Any]:
    return _request(path, dict(params_items))


def api_get(path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = {
        key: value
        for key, value in (params or {}).items()
        if value is not None and value != ""
    }
    return _cached_get(path, tuple(sorted(normalized.items())))


def timed_api_get(
    path: str, params: dict[str, Any] | None = None
) -> tuple[dict[str, Any], float]:
    started = perf_counter()
    payload = _request(path, params)
    elapsed_ms = (perf_counter() - started) * 1000
    return payload, elapsed_ms

