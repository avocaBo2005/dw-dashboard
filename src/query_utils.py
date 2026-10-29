from __future__ import annotations

from typing import Any, Iterable


def add_in_filter(
    clauses: list[str],
    params: dict[str, Any],
    column_sql: str,
    values: Iterable[str],
    prefix: str,
) -> None:
    selected = list(values)
    if not selected:
        return
    placeholders = []
    for index, value in enumerate(selected):
        key = f"{prefix}_{index}"
        placeholders.append(f":{key}")
        params[key] = value
    clauses.append(f"{column_sql} IN ({', '.join(placeholders)})")

