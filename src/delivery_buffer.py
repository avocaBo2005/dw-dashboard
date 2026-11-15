from __future__ import annotations

from typing import Any

import pandas as pd


POLICY_LABELS = {
    "current_k0": "Hiện trạng (k=0)",
    "global_k": "Buffer chung",
    "state_k": "Buffer theo bang",
}


def summary_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Normalize the policy summary returned by the Delivery Buffer API."""
    summary = payload.get("data", {}).get("summary", {})
    rows: list[dict[str, Any]] = []
    if not isinstance(summary, dict):
        return pd.DataFrame()

    for policy, values in summary.items():
        if not isinstance(values, dict):
            continue
        rows.append(
            {
                "policy": policy,
                "Chính sách": POLICY_LABELS.get(policy, policy),
                "Tỷ lệ trễ (%)": _percent(values.get("late_rate")),
                "Ngày cam kết TB": values.get("promised_days_avg"),
                "Số bang đánh giá": values.get("n_segments_scored"),
                "Số bang đạt mục tiêu": values.get("n_segments_met"),
                "Tỷ lệ đơn thuộc bang đạt (%)": _percent(values.get("pct_orders_in_met")),
                "Bang rủi ro nhất": values.get("worst_segment"),
                "Tỷ lệ trễ cao nhất (%)": _percent(values.get("worst_late_rate")),
            }
        )
    return pd.DataFrame(rows)


def segments_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Flatten per-state policy evaluations for display and CSV export."""
    raw_segments = payload.get("data", {}).get("segments", [])
    rows: list[dict[str, Any]] = []
    if not isinstance(raw_segments, list):
        return pd.DataFrame()

    for segment in raw_segments:
        if not isinstance(segment, dict):
            continue
        row: dict[str, Any] = {
            "Bang": segment.get("segment"),
            "Số đơn test": segment.get("n_test"),
            "Dùng fallback": segment.get("fallback"),
        }
        for policy in ("current_k0", "global_k", "state_k"):
            values = segment.get(policy) or {}
            prefix = POLICY_LABELS[policy]
            row[f"{prefix} · k"] = values.get("k")
            row[f"{prefix} · tỷ lệ trễ (%)"] = _percent(values.get("late_rate_test"))
            row[f"{prefix} · trạng thái"] = values.get("status")
            row[f"{prefix} · CI thấp (%)"] = _percent(values.get("ci_low"))
            row[f"{prefix} · CI cao (%)"] = _percent(values.get("ci_high"))
        rows.append(row)
    return pd.DataFrame(rows)


def tradeoff_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Normalize trade-off rows and convert ratio fields to percentages."""
    data = payload.get("data", [])
    if not isinstance(data, list):
        return pd.DataFrame()
    frame = pd.DataFrame(data)
    if frame.empty:
        return frame
    for column in ("safety_margin", "late_rate", "pct_orders_in_met", "worst_late_rate"):
        if column in frame.columns:
            frame[f"{column}_pct"] = pd.to_numeric(frame[column], errors="coerce") * 100
    return frame


def curve_frame(payload: dict[str, Any]) -> pd.DataFrame:
    """Normalize one state's policy curve for charting."""
    data = payload.get("data", {}).get("curve", [])
    if not isinstance(data, list):
        return pd.DataFrame()
    frame = pd.DataFrame(data)
    if frame.empty:
        return frame
    for column in ("late_rate_train", "late_rate_test"):
        if column in frame.columns:
            frame[f"{column}_pct"] = pd.to_numeric(frame[column], errors="coerce") * 100
    return frame


def _percent(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * 100
    except (TypeError, ValueError):
        return None
