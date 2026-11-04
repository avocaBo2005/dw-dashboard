from __future__ import annotations

from typing import Any

import pandas as pd


def analysis_frame(payload: dict[str, Any]) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for item in payload.get("data", []):
        record = {
            "level": item.get("level"),
            "level_name": item.get("level_name"),
            **(item.get("keys") or {}),
        }
        measures = item.get("measures")
        if isinstance(measures, dict):
            record.update(measures)
        for name in ("total_price", "total_freight", "n_orders", "n_items"):
            if name in item:
                record[name] = item[name]
        records.append(record)
    frame = pd.DataFrame(records)
    numeric_columns = {
        "level",
        "year",
        "quarter",
        "month",
        "total_price",
        "total_freight",
        "n_orders",
        "n_items",
        "eligible_orders",
        "late_orders",
        "late_rate",
        "avg_delivery_days",
        "avg_delay_days",
    }
    for column in numeric_columns.intersection(frame.columns):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
    return frame


def grand_total(payload: dict[str, Any]) -> dict[str, Any]:
    for item in payload.get("data", []):
        if item.get("level") == 0:
            measures = item.get("measures")
            return {**item, **(measures if isinstance(measures, dict) else {})}
    return {}


def level_frame(payload: dict[str, Any], level: int) -> pd.DataFrame:
    frame = analysis_frame(payload)
    if frame.empty or "level" not in frame:
        return frame
    return frame[frame["level"] == level].copy()


def add_month_start(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or not {"year", "month"}.issubset(frame.columns):
        return frame
    result = frame.copy()
    result["month_start"] = pd.to_datetime(
        {"year": result["year"], "month": result["month"], "day": 1},
        errors="coerce",
    )
    return result.sort_values("month_start")
