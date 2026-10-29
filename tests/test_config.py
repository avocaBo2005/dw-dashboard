from src.config import DatabaseSettings


def test_sqlalchemy_url_escapes_credentials() -> None:
    settings = DatabaseSettings(
        host="localhost",
        port=5432,
        database="olist_dw",
        user="dashboard user",
        password="p@ss/word",
    )
    assert settings.sqlalchemy_url == (
        "postgresql+psycopg://dashboard+user:p%40ss%2Fword@"
        "localhost:5432/olist_dw"
    )

