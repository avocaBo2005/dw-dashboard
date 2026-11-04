from src.config import DashboardSettings


def test_api_base_url_has_no_trailing_slash(monkeypatch) -> None:
    monkeypatch.setenv("API_BASE_URL", "http://localhost:3000/")
    monkeypatch.setenv("API_TIMEOUT_SECONDS", "10")
    settings = DashboardSettings.from_env()
    assert settings.api_base_url == "http://localhost:3000"
    assert settings.timeout_seconds == 10
