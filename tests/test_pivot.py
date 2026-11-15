import pytest

from src.pivot import pivot_heatmap_values, pivot_table_frame


def pivot_payload(unit="count"):
    return {
        "meta": {"unit": unit},
        "row_headers": [
            {"key": "2017", "label": "2017"},
            {"key": "2018", "label": "2018"},
        ],
        "col_headers": [
            {"key": "SP", "label": "SP"},
            {"key": "RJ", "label": "RJ"},
        ],
        "matrix": [[10, 5], [8, None]],
        "row_totals": [15, 8],
        "col_totals": [18, 5],
        "grand_total": 23,
    }


def test_pivot_table_adds_backend_totals():
    frame = pivot_table_frame(pivot_payload())

    assert frame.columns.tolist() == ["Hàng", "SP", "RJ", "Tổng hàng"]
    assert frame.iloc[-1].to_dict() == {
        "Hàng": "Tổng cột",
        "SP": 18.0,
        "RJ": 5.0,
        "Tổng hàng": 23.0,
    }


def test_ratio_pivot_is_scaled_for_display():
    payload = pivot_payload("ratio")
    payload["matrix"] = [[0.05, 0.075], [0.1, None]]
    payload["row_totals"] = [0.06, 0.1]
    payload["col_totals"] = [0.07, 0.075]
    payload["grand_total"] = 0.08

    frame = pivot_table_frame(payload)
    rows, cols, values = pivot_heatmap_values(payload)

    assert rows == ["2017", "2018"]
    assert cols == ["SP", "RJ"]
    assert values[0][0] == pytest.approx(5)
    assert frame.loc[0, "Tổng hàng"] == pytest.approx(6)
    assert frame.iloc[-1]["Tổng hàng"] == pytest.approx(8)


def test_invalid_pivot_shape_returns_empty_outputs():
    payload = pivot_payload()
    payload["matrix"] = [[1]]

    assert pivot_table_frame(payload).empty
    assert pivot_heatmap_values(payload) == ([], [], [])
