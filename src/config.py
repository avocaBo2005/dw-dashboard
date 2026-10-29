from __future__ import annotations

from dataclasses import dataclass
import os
from urllib.parse import quote_plus

from dotenv import load_dotenv


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    database: str
    user: str
    password: str
    schema: str = "analytics"

    @classmethod
    def from_env(cls) -> "DatabaseSettings":
        load_dotenv()
        required = {
            "POSTGRES_HOST": os.getenv("POSTGRES_HOST"),
            "POSTGRES_DB": os.getenv("POSTGRES_DB"),
            "POSTGRES_USER": os.getenv("POSTGRES_USER"),
            "POSTGRES_PASSWORD": os.getenv("POSTGRES_PASSWORD"),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError(
                "Missing database settings: " + ", ".join(sorted(missing))
            )
        try:
            port = int(os.getenv("POSTGRES_PORT", "5432"))
        except ValueError as exc:
            raise RuntimeError("POSTGRES_PORT must be an integer") from exc
        return cls(
            host=required["POSTGRES_HOST"] or "",
            port=port,
            database=required["POSTGRES_DB"] or "",
            user=required["POSTGRES_USER"] or "",
            password=required["POSTGRES_PASSWORD"] or "",
            schema=os.getenv("POSTGRES_SCHEMA", "analytics"),
        )

    @property
    def sqlalchemy_url(self) -> str:
        user = quote_plus(self.user)
        password = quote_plus(self.password)
        return (
            f"postgresql+psycopg://{user}:{password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

