import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()


def resolve_database_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url

    try:
        import streamlit as st

        secrets_url = st.secrets.get("DATABASE_URL")
        if secrets_url:
            return secrets_url
    except Exception:
        pass

    return "postgresql://postgres:189014800%40Postgres@localhost:5432/app_booking"


DATABASE_URL = resolve_database_url()

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine) 