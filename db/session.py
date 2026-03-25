import os
from pathlib import Path
import tomllib
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def _build_postgres_url_from_parts() -> str | None:
    """
    Build a PostgreSQL DSN from common env vars.
    Supports either `DB_*` or `POSTGRES_*` naming.
    """
    host = os.getenv("DB_HOST") or os.getenv("POSTGRES_HOST")
    port = os.getenv("DB_PORT") or os.getenv("POSTGRES_PORT") or "5432"
    dbname = os.getenv("DB_NAME") or os.getenv("POSTGRES_DB")
    user = os.getenv("DB_USER") or os.getenv("POSTGRES_USER")
    password = os.getenv("DB_PASSWORD") or os.getenv("POSTGRES_PASSWORD")
    if not all([host, dbname, user, password]):
        return None
    return f"postgresql://{user}:{password}@{host}:{port}/{dbname}"


def _find_database_url_in_toml(data: object) -> str | None:
    """
    Recursively find a postgres URL inside Streamlit `secrets.toml`.
    """
    if isinstance(data, dict):
        # Common top-level keys
        for key in ("DATABASE_URL", "database_url", "url", "URL"):
            value = data.get(key)
            if isinstance(value, str) and "postgres" in value and "://" in value:
                return value
        # Recurse into nested sections
        for value in data.values():
            found = _find_database_url_in_toml(value)
            if found:
                return found
    elif isinstance(data, list):
        for item in data:
            found = _find_database_url_in_toml(item)
            if found:
                return found
    return None


def resolve_database_url() -> tuple[str, str]:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url, "env"

    built = _build_postgres_url_from_parts()
    if built:
        return built, "env_parts"

    # Read Streamlit secrets files directly to avoid calling Streamlit APIs
    # before st.set_page_config() in the app script.
    candidate_paths = [
        Path.home() / ".streamlit" / "secrets.toml",
        Path.cwd() / ".streamlit" / "secrets.toml",
    ]
    for secrets_path in candidate_paths:
        if not secrets_path.exists():
            continue
        try:
            with secrets_path.open("rb") as file:
                data = tomllib.load(file)
            secrets_url = _find_database_url_in_toml(data)
            if secrets_url:
                return secrets_url, "secrets"
        except Exception:
            continue

    # Local dev fallback (Streamlit Cloud will not have your local Postgres).
    return "postgresql://postgres:189014800%40Postgres@localhost:5432/app_booking", "fallback"


DATABASE_URL, DATABASE_URL_SOURCE = resolve_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 


def summarize_database_url(url: str) -> dict[str, str | int | None]:
    """
    Extract host/port/db/user from a postgres DSN without exposing the password.
    """
    try:
        parsed = urlparse(url)
        database = (parsed.path or "").lstrip("/") or None
        return {
            "scheme": parsed.scheme or None,
            "user": parsed.username or None,
            "host": parsed.hostname or None,
            "port": parsed.port,
            "database": database,
        }
    except Exception:
        return {"scheme": None, "user": None, "host": None, "port": None, "database": None}


DATABASE_URL_SUMMARY = summarize_database_url(DATABASE_URL)