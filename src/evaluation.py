from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.transform import grand_total


EXPECTED_ELIGIBLE = 96_470
EXPECTED_LATE = 6_534
EXPECTED_LATE_RATE = 6.77


@dataclass(frozen=True)
class CheckResult:
    category: str
    name: str
    passed: bool
    actual: str
    expected: str

    def as_row(self) -> dict[str, Any]:
        row = asdict(self)
        return {
            "Nhóm": row["category"],
            "Kiểm tra": row["name"],
            "Kết quả": "PASS" if row["passed"] else "FAIL",
            "Thực tế": row["actual"],
            "Kỳ vọng": row["expected"],
        }


def response_rating(elapsed_ms: float) -> str:
    if elapsed_ms <= 500:
        return "Tốt"
    if elapsed_ms <= 1_500:
        return "Chấp nhận"
    return "Cần tối ưu"


def evaluate_payloads(payloads: dict[str, dict[str, Any]]) -> tuple[list[CheckResult], dict[str, Any]]:
    api_ok = payloads.get("API health", {}).get("data", {}).get("status") == "ok"
    db_ok = payloads.get("Database health", {}).get("status") == "ok"
    sales_total = grand_total(payloads.get("Sales OLAP", {}))
    delivery_total = grand_total(payloads.get("Delivery OLAP", {}))
    distribution = payloads.get("Delivery distribution", {})
    summary = distribution.get("summary", {})
    eligible = int(delivery_total.get("eligible_orders") or 0)
    distributed_total = int(distribution.get("meta", {}).get("total") or -1)
    late = int(summary.get("late_orders") or 0)
    late_rate = float(summary.get("late_rate") or 0)
    review_groups = {
        row.get("group")
        for row in payloads.get("Review by delay", {}).get("data", [])
    }
    dss_rows = payloads.get("DSS scorecard", {}).get("data", [])
    dss_weights = payloads.get("DSS config", {}).get("data", {}).get("weights", [])
    weight_sum = sum(float(item.get("weight") or 0) for item in dss_weights)

    checks = [
        CheckResult("Sẵn sàng", "API hoạt động", api_ok, str(api_ok), "True"),
        CheckResult("Sẵn sàng", "Database kết nối", db_ok, str(db_ok), "True"),
        CheckResult(
            "Dữ liệu", "Sales có dữ liệu", int(sales_total.get("n_orders") or 0) > 0,
            f"{int(sales_total.get('n_orders') or 0):,} đơn", "> 0 đơn",
        ),
        CheckResult(
            "Nhất quán", "Delivery khớp distribution", eligible == distributed_total,
            f"{eligible:,} / {distributed_total:,}", "Hai tổng bằng nhau",
        ),
        CheckResult(
            "Đối soát ETL", "Eligible orders", eligible == EXPECTED_ELIGIBLE,
            f"{eligible:,}", f"{EXPECTED_ELIGIBLE:,}",
        ),
        CheckResult(
            "Đối soát ETL", "Late orders", late == EXPECTED_LATE,
            f"{late:,}", f"{EXPECTED_LATE:,}",
        ),
        CheckResult(
            "Đối soát ETL", "Late rate", abs(late_rate - EXPECTED_LATE_RATE) <= 0.01,
            f"{late_rate:.2f}%", f"{EXPECTED_LATE_RATE:.2f}% ± 0.01",
        ),
        CheckResult(
            "Nhất quán", "Review đủ hai nhóm",
            review_groups == {"late", "not_late"},
            ", ".join(sorted(str(item) for item in review_groups)), "late, not_late",
        ),
        CheckResult(
            "DSS", "Scorecard trả kết quả", len(dss_rows) > 0,
            f"{len(dss_rows):,} dòng", "> 0 dòng",
        ),
        CheckResult(
            "DSS", "Tổng trọng số hợp lệ", bool(dss_weights) and weight_sum > 0,
            f"{weight_sum:.2f}", "> 0",
        ),
    ]
    metrics = {
        "eligible": eligible,
        "late": late,
        "late_rate": late_rate,
        "passed": sum(check.passed for check in checks),
        "total": len(checks),
    }
    return checks, metrics
