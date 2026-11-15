from __future__ import annotations

from typing import Any

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.api import api_get
from src.ui import section_intro, style_figure


def pivot_table_frame(payload: dict[str, Any], *, include_totals: bool = True) -> pd.DataFrame:
    """Convert a Pivot API response to a display/export table."""
    row_headers = payload.get("row_headers", [])
    col_headers = payload.get("col_headers", [])
    matrix = payload.get("matrix", [])
    if not _valid_shape(row_headers, col_headers, matrix):
        return pd.DataFrame()

    scale = _display_scale(payload)
    row_labels = [str(item.get("label", item.get("key", ""))) for item in row_headers]
    col_labels = [str(item.get("label", item.get("key", ""))) for item in col_headers]
    scaled_matrix = [[_scaled(value, scale) for value in row] for row in matrix]
    frame = pd.DataFrame(scaled_matrix, columns=col_labels)
    frame.insert(0, "Hàng", row_labels)

    if include_totals:
        row_totals = payload.get("row_totals", [])
        if isinstance(row_totals, list) and len(row_totals) == len(frame):
            frame["Tổng hàng"] = [_scaled(value, scale) for value in row_totals]

        col_totals = payload.get("col_totals", [])
        if isinstance(col_totals, list) and len(col_totals) == len(col_labels):
            total_row: dict[str, Any] = {
                "Hàng": "Tổng cột",
                **{
                    label: _scaled(value, scale)
                    for label, value in zip(col_labels, col_totals, strict=True)
                },
            }
            if "Tổng hàng" in frame.columns:
                total_row["Tổng hàng"] = _scaled(payload.get("grand_total"), scale)
            frame = pd.concat([frame, pd.DataFrame([total_row])], ignore_index=True)
    return frame


def pivot_heatmap_values(
    payload: dict[str, Any],
) -> tuple[list[str], list[str], list[list[float | None]]]:
    """Return labels and scaled values suitable for a heatmap."""
    row_headers = payload.get("row_headers", [])
    col_headers = payload.get("col_headers", [])
    matrix = payload.get("matrix", [])
    if not _valid_shape(row_headers, col_headers, matrix):
        return [], [], []
    scale = _display_scale(payload)
    return (
        [str(item.get("label", item.get("key", ""))) for item in row_headers],
        [str(item.get("label", item.get("key", ""))) for item in col_headers],
        [[_scaled(value, scale) for value in row] for row in matrix],
    )


def render_pivot_explorer(cube: str, filters: dict[str, Any]) -> None:
    """Render a metadata-driven Pivot explorer for the selected cube."""
    with st.expander("Pivot tùy biến", expanded=False):
        st.caption(
            "Chọn chiều hàng, chiều cột và độ đo. Kết quả được giới hạn để dashboard "
            "vẫn dễ đọc; tổng được backend tính trực tiếp trên toàn bộ phạm vi lọc."
        )
        enabled = st.toggle("Bật Pivot tùy biến", key=f"{cube}_pivot_enabled")
        if not enabled:
            return

        metadata_payload = api_get("/api/v1/meta/pivot")
        cube_metadata = metadata_payload.get("data", {}).get(cube, {})
        axes = cube_metadata.get("axes", [])
        measures = cube_metadata.get("measures", [])
        if not axes or not measures:
            st.warning("Pivot metadata không đầy đủ cho cube này.")
            return

        axis_by_key = {item["key"]: item for item in axes}
        axis_keys = list(axis_by_key)
        default_rows = "year_month" if "year_month" in axis_by_key else axis_keys[0]
        preferred_col = "category" if cube == "sales" else "customer_state"
        default_cols = preferred_col if preferred_col in axis_by_key else axis_keys[1]

        first, second = st.columns(2)
        row_key = first.selectbox(
            "Chiều hàng",
            axis_keys,
            index=axis_keys.index(default_rows),
            format_func=lambda key: axis_by_key[key]["label"],
            key=f"{cube}_pivot_rows",
        )
        available_cols = [key for key in axis_keys if key != row_key]
        col_default = default_cols if default_cols in available_cols else available_cols[0]
        col_key = second.selectbox(
            "Chiều cột",
            available_cols,
            index=available_cols.index(col_default),
            format_func=lambda key: axis_by_key[key]["label"],
            key=f"{cube}_pivot_cols",
        )

        if cube == "delivery" and "delay_bucket" in {row_key, col_key}:
            allowed = {"eligible_orders", "avg_delivery_days"}
            measures = [item for item in measures if item.get("key") in allowed]
            st.info(
                "Khi dùng nhóm độ trễ, backend chỉ cho phép Số đơn đủ điều kiện "
                "hoặc Số ngày giao trung bình."
            )

        measure_by_key = {item["key"]: item for item in measures}
        measure_keys = list(measure_by_key)
        preferred_measure = "total_price" if cube == "sales" else "late_rate"
        if "delay_bucket" in {row_key, col_key}:
            preferred_measure = "eligible_orders"
        measure_default = (
            measure_keys.index(preferred_measure) if preferred_measure in measure_keys else 0
        )
        controls = st.columns(3)
        measure_key = controls[0].selectbox(
            "Độ đo",
            measure_keys,
            index=measure_default,
            format_func=lambda key: measure_by_key[key]["label"],
            key=f"{cube}_pivot_measure_{'bucket' if 'delay_bucket' in {row_key, col_key} else 'normal'}",
        )
        max_rows = controls[1].slider(
            "Số hàng tối đa", 5, 50, 20, 5, key=f"{cube}_pivot_max_rows"
        )
        max_cols = controls[2].slider(
            "Số cột tối đa", 5, 50, 10, 5, key=f"{cube}_pivot_max_cols"
        )

        params = {
            **filters,
            "rows": row_key,
            "cols": col_key,
            "measure": measure_key,
            "max_rows": max_rows,
            "max_cols": max_cols,
        }
        payload = api_get(f"/api/v1/{'sale' if cube == 'sales' else 'delivery'}/pivot", params)
        table = pivot_table_frame(payload)
        row_labels, col_labels, heatmap_values = pivot_heatmap_values(payload)
        if table.empty or not heatmap_values:
            st.info("Không có dữ liệu Pivot cho bộ lọc hiện tại.")
            return

        meta = payload.get("meta", {})
        unit = meta.get("unit", "")
        unit_label = {
            "currency": "Giá trị",
            "count": "Số lượng",
            "ratio": "Tỷ lệ (%)",
            "days": "Ngày",
        }.get(unit, "Giá trị")
        section_intro(
            "Ma trận Pivot",
            f"{axis_by_key[row_key]['label']} × {axis_by_key[col_key]['label']} · "
            f"{measure_by_key[measure_key]['label']}",
        )
        heatmap = go.Figure(
            data=go.Heatmap(
                z=heatmap_values,
                x=col_labels,
                y=row_labels,
                colorscale="Blues",
                colorbar={"title": unit_label},
                hovertemplate=(
                    f"{axis_by_key[row_key]['label']}: %{{y}}<br>"
                    f"{axis_by_key[col_key]['label']}: %{{x}}<br>"
                    f"{measure_by_key[measure_key]['label']}: %{{z:,.2f}}<extra></extra>"
                ),
            )
        )
        heatmap.update_layout(title="Heatmap Pivot")
        heatmap.update_yaxes(autorange="reversed")
        st.plotly_chart(
            style_figure(heatmap, height=max(390, min(780, 32 * len(row_labels) + 170))),
            width="stretch",
        )

        numeric_columns = [column for column in table.columns if column != "Hàng"]
        number_format = {
            "ratio": "%.2f%%",
            "count": "%d",
            "currency": "%.2f",
            "days": "%.2f",
        }.get(unit, "%.2f")
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={
                column: st.column_config.NumberColumn(column, format=number_format)
                for column in numeric_columns
            },
        )
        truncated = meta.get("truncated", {})
        if truncated.get("rows") or truncated.get("cols"):
            st.warning(
                f"Đang hiển thị {meta.get('n_rows', len(row_labels))}/"
                f"{meta.get('total_rows', len(row_labels))} hàng và "
                f"{meta.get('n_cols', len(col_labels))}/"
                f"{meta.get('total_cols', len(col_labels))} cột. "
                "Các ô bị cắt không được cộng thủ công; hãy dùng tổng do backend trả về."
            )
        st.download_button(
            "Tải ma trận Pivot CSV",
            table.to_csv(index=False).encode("utf-8-sig"),
            f"olist_{cube}_pivot.csv",
            "text/csv",
            key=f"{cube}_pivot_download",
        )


def _valid_shape(row_headers: object, col_headers: object, matrix: object) -> bool:
    return (
        isinstance(row_headers, list)
        and isinstance(col_headers, list)
        and isinstance(matrix, list)
        and len(matrix) == len(row_headers)
        and all(isinstance(row, list) and len(row) == len(col_headers) for row in matrix)
    )


def _display_scale(payload: dict[str, Any]) -> float:
    return 100.0 if payload.get("meta", {}).get("unit") == "ratio" else 1.0


def _scaled(value: object, scale: float) -> float | None:
    if value is None:
        return None
    try:
        return float(value) * scale
    except (TypeError, ValueError):
        return None
