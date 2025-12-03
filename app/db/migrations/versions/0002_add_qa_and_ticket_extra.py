"""add QA tables + extra ticket fields + extend status enum (idempotent)"""

from alembic import op
import sqlalchemy as sa

# Ідентифікатор цієї ревізії має лишитися тим самим, що у тебе вже є
revision = "0002_add_qa_and_ticket_extra"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- 1) tickets: безпечні ADD COLUMN (IF NOT EXISTS) ----
    op.execute("""
    ALTER TABLE tickets ADD COLUMN IF NOT EXISTS dept         VARCHAR(32);
    ALTER TABLE tickets ADD COLUMN IF NOT EXISTS topic        VARCHAR(255);
    ALTER TABLE tickets ADD COLUMN IF NOT EXISTS position     VARCHAR(255);
    ALTER TABLE tickets ADD COLUMN IF NOT EXISTS phone        VARCHAR(32);
    ALTER TABLE tickets ADD COLUMN IF NOT EXISTS work_email   VARCHAR(255);
    ALTER TABLE tickets ADD COLUMN IF NOT EXISTS backup_email VARCHAR(255);
    """)

    # ---- 2) ticket_status_enum: додати відсутні значення (IF NOT EXISTS) ----
    # У Postgres нема "ADD VALUE IF NOT EXISTS" до старих версій, тому робимо через DO ... EXCEPTION WHEN
    op.execute("""
    DO $$
    BEGIN
        -- triage
        IF NOT EXISTS (SELECT 1 FROM pg_type t
                       JOIN pg_enum e ON t.oid = e.enumtypid
                       WHERE t.typname = 'ticket_status_enum' AND e.enumlabel = 'triage') THEN
            ALTER TYPE ticket_status_enum ADD VALUE 'triage';
        END IF;
    END$$;
    """)
    op.execute("""
    DO $$
    BEGIN
        -- pending_admin
        IF NOT EXISTS (SELECT 1 FROM pg_type t
                       JOIN pg_enum e ON t.oid = e.enumtypid
                       WHERE t.typname = 'ticket_status_enum' AND e.enumlabel = 'pending_admin') THEN
            ALTER TYPE ticket_status_enum ADD VALUE 'pending_admin';
        END IF;
    END$$;
    """)

    # ---- 3) question_status_enum (створити, якщо ще нема) ----
    op.execute("""
    DO $$
    BEGIN
        CREATE TYPE question_status_enum AS ENUM ('new','answered','closed');
    EXCEPTION WHEN duplicate_object THEN
        NULL;
    END$$;
    """)

    # ---- 4) questions (IF NOT EXISTS) ----
    op.execute("""
    CREATE TABLE IF NOT EXISTS questions (
        id          SERIAL PRIMARY KEY,
        author_id   INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        title       VARCHAR(255) NOT NULL,
        content     TEXT NOT NULL,
        status      question_status_enum NOT NULL DEFAULT 'new',
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_questions_author_id ON questions(author_id);")

    # ---- 5) answers (IF NOT EXISTS) ----
    op.execute("""
    CREATE TABLE IF NOT EXISTS answers (
        id           SERIAL PRIMARY KEY,
        question_id  INTEGER NOT NULL REFERENCES questions(id) ON DELETE CASCADE,
        operator_id  INTEGER NULL REFERENCES users(id) ON DELETE SET NULL,
        content      TEXT NOT NULL,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_answers_question_id ON answers(question_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_answers_operator_id ON answers(operator_id);")


def downgrade() -> None:
    # Downgrade можна залишити як був (або акуратно з IF EXISTS)
    op.execute("DROP TABLE IF EXISTS answers;")
    op.execute("DROP TABLE IF EXISTS questions;")
    # НЕ видаляємо enum-значення з ticket_status_enum (Postgres цього не любить)
    # question_status_enum видаляти теж необов'язково; але якщо дуже треба:
    op.execute("DROP TYPE IF EXISTS question_status_enum;")
