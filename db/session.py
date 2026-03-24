import os
from pathlib import Path
import tomllib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def resolve_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

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
            secrets_url = data.get("DATABASE_URL")
            if secrets_url:
                return secrets_url
        except Exception:
            continue

    return "postgresql://postgres:189014800%40Postgres@localhost:5432/app_booking"


DATABASE_URL = resolve_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 