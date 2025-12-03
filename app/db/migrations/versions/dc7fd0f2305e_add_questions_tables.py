"""add questions tables

Revision ID: dc7fd0f2305e
Revises: 0001_init
Create Date: 2025-10-27
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

# revision identifiers, used by Alembic.
revision = "dc7fd0f2305e"
down_revision = "0001_init"
branch_labels = None
depends_on = None


def upgrade():
    # 1) Створюємо ENUM, тільки якщо його ще нема
    op.execute("""
    DO $$
    BEGIN
        IF NOT EXISTS (
            SELECT 1 FROM pg_type WHERE typname = 'question_status_enum'
        ) THEN
            CREATE TYPE question_status_enum AS ENUM ('new','answered','closed');
        END IF;
    END
    $$;
    """)

    # Підготовлений тип (не створюємо ще раз)
    qstatus = pg.ENUM('new', 'answered', 'closed',
                      name='question_status_enum',
                      create_type=False)

    # 2) Таблиця questions
    op.create_table(
        'questions',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('author_id', sa.Integer, sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('status', qstatus, nullable=False, server_default='new'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_questions_status', 'questions', ['status'])
    op.create_index('ix_questions_author_id', 'questions', ['author_id'])
    op.create_index('ix_questions_created_at', 'questions', ['created_at'])

    # 3) Таблиця answers
    op.create_table(
        'answers',
        sa.Column('id', sa.Integer, primary_key=True),
        sa.Column('question_id', sa.Integer, sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('operator_id', sa.Integer, sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('now()')),
    )
    op.create_index('ix_answers_question_id', 'answers', ['question_id'])
    op.create_index('ix_answers_operator_id', 'answers', ['operator_id'])
    op.create_index('ix_answers_created_at', 'answers', ['created_at'])


def downgrade():
    # Видаляємо залежні об'єкти в правильному порядку
    op.drop_index('ix_answers_created_at', table_name='answers')
    op.drop_index('ix_answers_operator_id', table_name='answers')
    op.drop_index('ix_answers_question_id', table_name='answers')
    op.drop_table('answers')

    op.drop_index('ix_questions_created_at', table_name='questions')
    op.drop_index('ix_questions_author_id', table_name='questions')
    op.drop_index('ix_questions_status', table_name='questions')
    op.drop_table('questions')

    # Спробуємо видалити тип (безпечно, якщо десь ще використовується — БД не дасть)
    op.execute("DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'question_status_enum') THEN DROP TYPE question_status_enum; END IF; END $$;")
