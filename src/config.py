from __future__ import annotations

import os
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv


@dataclass(frozen=True)
class DashboardSettings:
    api_base_url: str
    timeout_seconds: float = 15.0

    @classmethod
    def from_env(cls) -> "DashboardSettings":
        load_dotenv()
        api_base_url = os.getenv("API_BASE_URL", "http://localhost:3000").rstrip("/")
        parsed_url = urlparse(api_base_url)
        if parsed_url.scheme not in {"http", "https"} or not parsed_url.netloc:
            raise RuntimeError("API_BASE_URL must be a valid HTTP(S) URL")
        try:
            timeout_seconds = float(os.getenv("API_TIMEOUT_SECONDS", "15"))
        except ValueError as exc:
            raise RuntimeError("API_TIMEOUT_SECONDS must be a number") from exc
        if timeout_seconds <= 0:
            raise RuntimeError("API_TIMEOUT_SECONDS must be positive")
        return cls(api_base_url=api_base_url, timeout_seconds=timeout_seconds)
