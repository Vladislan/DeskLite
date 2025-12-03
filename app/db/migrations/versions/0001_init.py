"""init schema

Revision ID: 0001_init
Revises:
Create Date: 2025-10-10 12:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---------- 1) Створюємо ENUM типи (ідемпотентно) ----------
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE role_enum AS ENUM ('user','operator','admin');
    EXCEPTION WHEN duplicate_object THEN NULL;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE priority_enum AS ENUM ('low','normal','high');
    EXCEPTION WHEN duplicate_object THEN NULL;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE ticket_status_enum AS ENUM ('new','triage','in_progress','blocked','done','canceled','archived');
    EXCEPTION WHEN duplicate_object THEN NULL;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE comment_visibility_enum AS ENUM ('public','internal');
    EXCEPTION WHEN duplicate_object THEN NULL;
    END$$;
    """)

    # ---------- 2) Таблиці (спершу VARCHAR, щоб уникнути CREATE TYPE з боку SA) ----------
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), nullable=False, server_default="user"),     # тимчасово VARCHAR
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "tickets",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("assignee_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("priority", sa.String(16), nullable=False, server_default="normal"),  # тимчасово VARCHAR
        sa.Column("status", sa.String(32), nullable=False, server_default="new"),       # тимчасово VARCHAR
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_tickets_status_priority", "tickets", ["status", "priority"], unique=False)
    op.create_index("ix_tickets_author_id", "tickets", ["author_id"], unique=False)
    op.create_index("ix_tickets_assignee_id", "tickets", ["assignee_id"], unique=False)
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"], unique=False)

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(16), nullable=False, server_default="public"),  # тимчасово VARCHAR
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_comments_ticket_id", "comments", ["ticket_id"], unique=False)
    op.create_index("ix_comments_author_id", "comments", ["author_id"], unique=False)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("ticket_id", sa.Integer(), sa.ForeignKey("tickets.id", ondelete="SET NULL"), nullable=True),
        sa.Column("payload", sa.dialects.postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_audit_log_actor_id", "audit_log", ["actor_id"], unique=False)
    op.create_index("ix_audit_log_ticket_id", "audit_log", ["ticket_id"], unique=False)

    # ---------- 3) Зміна типів VARCHAR → ENUM з безпечним handling default ----------
    # users.role
    op.execute("ALTER TABLE users ALTER COLUMN role DROP DEFAULT;")
    # (на випадок кастомних значень — нормалізуємо в lower)
    op.execute("UPDATE users SET role = LOWER(role);")
    op.execute("ALTER TABLE users ALTER COLUMN role TYPE role_enum USING role::role_enum;")
    op.execute("ALTER TABLE users ALTER COLUMN role SET DEFAULT 'user';")

    # tickets.priority / tickets.status
    op.execute("ALTER TABLE tickets ALTER COLUMN priority DROP DEFAULT;")
    op.execute("ALTER TABLE tickets ALTER COLUMN status DROP DEFAULT;")
    op.execute("UPDATE tickets SET priority = LOWER(priority), status = LOWER(status);")
    op.execute("ALTER TABLE tickets ALTER COLUMN priority TYPE priority_enum USING priority::priority_enum;")
    op.execute("ALTER TABLE tickets ALTER COLUMN status   TYPE ticket_status_enum USING status::ticket_status_enum;")
    op.execute("ALTER TABLE tickets ALTER COLUMN priority SET DEFAULT 'normal';")
    op.execute("ALTER TABLE tickets ALTER COLUMN status   SET DEFAULT 'new';")

    # comments.visibility
    op.execute("ALTER TABLE comments ALTER COLUMN visibility DROP DEFAULT;")
    op.execute("UPDATE comments SET visibility = LOWER(visibility);")
    op.execute("ALTER TABLE comments ALTER COLUMN visibility TYPE comment_visibility_enum USING visibility::comment_visibility_enum;")
    op.execute("ALTER TABLE comments ALTER COLUMN visibility SET DEFAULT 'public';")


def downgrade() -> None:
    # Відкотимо ENUM-и назад у текст
    op.execute("ALTER TABLE comments ALTER COLUMN visibility TYPE varchar(16);")
    op.execute("ALTER TABLE tickets  ALTER COLUMN status    TYPE varchar(32);")
    op.execute("ALTER TABLE tickets  ALTER COLUMN priority  TYPE varchar(16);")
    op.execute("ALTER TABLE users    ALTER COLUMN role      TYPE varchar(32);")

    op.drop_index("ix_audit_log_ticket_id", table_name="audit_log")
    op.drop_index("ix_audit_log_actor_id", table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index("ix_comments_author_id", table_name="comments")
    op.drop_index("ix_comments_ticket_id", table_name="comments")
    op.drop_table("comments")

    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_assignee_id", table_name="tickets")
    op.drop_index("ix_tickets_author_id", table_name="tickets")
    op.drop_index("ix_tickets_status_priority", table_name="tickets")
    op.drop_table("tickets")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    op.execute("DROP TYPE IF EXISTS role_enum")
    op.execute("DROP TYPE IF EXISTS priority_enum")
    op.execute("DROP TYPE IF EXISTS ticket_status_enum")
    op.execute("DROP TYPE IF EXISTS comment_visibility_enum")
