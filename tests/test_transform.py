from src.transform import analysis_frame, grand_total, level_frame


def test_flattens_sales_analysis_payload() -> None:
    payload = {
        "data": [
            {
                "level": 1,
                "level_name": "year",
                "keys": {"year": 2018},
                "total_price": 10.5,
                "total_freight": 2.0,
                "n_orders": 1,
                "n_items": 1,
            },
            {
                "level": 0,
                "level_name": "grand_total",
                "keys": {},
                "total_price": 10.5,
                "total_freight": 2.0,
                "n_orders": 1,
                "n_items": 1,
            },
        ]
    }
    assert grand_total(payload)["total_price"] == 10.5
    assert level_frame(payload, 1).iloc[0]["year"] == 2018
    assert analysis_frame(payload).shape[0] == 2


def test_flattens_delivery_measures() -> None:
    payload = {
        "data": [
            {
                "level": 0,
                "level_name": "grand_total",
                "keys": {},
                "measures": {"eligible_orders": 5, "late_orders": 1},
            }
        ]
    }
    assert grand_total(payload)["eligible_orders"] == 5
