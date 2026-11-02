import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text

os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = "postgresql+psycopg://vcontent:vcontent@localhost:5433/vcontent_test"
os.environ["SECRET_KEY"] = "test-secret-key-vcontent-please-change"
os.environ["RATE_LIMIT_ENABLED"] = "false"
os.environ["ADMIN_EMAIL"] = "admin@vcontent.local"
os.environ["ADMIN_PASSWORD"] = "Admin!2026"
os.environ["ADMIN_NAME"] = "Administradora"
os.environ["COOKIE_SECURE"] = "false"
os.environ["FRONTEND_URL"] = "http://localhost:3010"

ROOT = Path(__file__).resolve().parents[1]


def _ensure_database() -> None:
    with psycopg.connect("postgresql://vcontent:vcontent@localhost:5433/vcontent", autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'vcontent_test'").fetchone()
        if not exists:
            conn.execute("CREATE DATABASE vcontent_test")


@pytest.fixture(scope="session", autouse=True)
def migrated():
    _ensure_database()
    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL"])
    command.upgrade(cfg, "head")


@pytest.fixture
def client(migrated):
    from app.database import engine
    from app.main import app
    from app.storage import MemoryStorage, set_storage

    set_storage(MemoryStorage())
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                TRUNCATE TABLE
                  audit_logs,
                  notifications,
                  content_comments,
                  approval_history,
                  content_media,
                  content_items,
                  client_users,
                  clients,
                  refresh_tokens,
                  password_reset_tokens,
                  users
                RESTART IDENTITY CASCADE
                """
            )
        )
    with TestClient(app) as test_client:
        yield test_client


HEADERS = {"X-Requested-With": "vcontent"}


def login(client: TestClient, email: str, password: str):
    response = client.post("/api/auth/login", json={"email": email, "password": password}, headers=HEADERS)
    assert response.status_code == 200, response.text
    return response.json()["user"]


def auth(client: TestClient):
    return login(client, "admin@vcontent.local", "Admin!2026")
