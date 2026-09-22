"""Recreate a throwaway test database: empty schema, latest migrations, seeded bosses.

    DATABASE_URL=postgresql+psycopg://.../sekiro_test python -m scripts.reset_test_database

Refuses to run unless the database name ends in '_test'.
"""

import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from app.db.session import get_database_url
from app.seed import load_boss_data, sync_reference_data

BACKEND_DIR = Path(__file__).resolve().parent.parent


def alembic_config(url: str) -> Config:
    config = Config(str(BACKEND_DIR / "alembic.ini"))
    config.set_main_option("script_location", str(BACKEND_DIR / "alembic"))
    config.set_main_option("sqlalchemy.url", url)
    return config


def ensure_test_database(url: str) -> None:
    parsed = make_url(url)
    if not (parsed.database or "").endswith("_test"):
        raise ValueError(f"refusing to touch '{parsed.database}': test database names must end in '_test'")
    admin = create_engine(parsed.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": parsed.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{parsed.database}"'))
    admin.dispose()


def reset_schema(url: str) -> None:
    ensure_test_database(url)
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    engine.dispose()
    command.upgrade(alembic_config(url), "head")


def main() -> int:
    url = get_database_url()
    reset_schema(url)
    engine = create_engine(url)
    with Session(engine) as session:
        sync_reference_data(session, load_boss_data())
        session.commit()
    engine.dispose()
    print(f"Reset and seeded {make_url(url).database}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
