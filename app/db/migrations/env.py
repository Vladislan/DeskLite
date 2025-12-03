# app/db/migrations/env.py
from __future__ import annotations

from logging.config import fileConfig
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection
from alembic import context

# Alembic Config object
config = context.config

# Логування alembic.ini (якщо є)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Метадані моделей
from app.db.models import Base  # noqa: E402
target_metadata = Base.metadata

# URL беремо із твоїх settings
from app.core.config import settings  # noqa: E402
ASYNC_URL = settings.database_url

def to_sync_url(async_url: str) -> str:
    # найпростіше: замінити драйвер на sync
    # приклад: postgresql+asyncpg:// -> postgresql+psycopg2://
    if async_url.startswith("postgresql+asyncpg://"):
        return "postgresql+psycopg2://" + async_url[len("postgresql+asyncpg://") :]
    # якщо вже sync — залишаємо як є
    return async_url

SYNC_URL = to_sync_url(ASYNC_URL)

def run_migrations_offline() -> None:
    """Offline режим: генеруємо SQL без реального конекту."""
    context.configure(
        url=SYNC_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    """Основний запуск у контексті відкритого підключення."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_as_batch=False,
        version_table="alembic_version",
        include_schemas=False,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Online режим: реальний конект синхронним рушієм."""
    connectable = create_engine(
        SYNC_URL,
        poolclass=pool.NullPool,
        future=True,
    )
    with connectable.connect() as connection:
        do_run_migrations(connection)

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
