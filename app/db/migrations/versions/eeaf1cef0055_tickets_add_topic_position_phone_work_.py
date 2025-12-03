from alembic import op
import sqlalchemy as sa

# підстав свій попередній head, напр.:
revision = "0003_tickets_contact_fields"
down_revision = "61c022d68763"   # або той, що в тебе зараз HEAD після виправлення ланцюжка
branch_labels = None
depends_on = None

def upgrade():
    # 1) Нові колонки (усі nullable, щоб узгодити з Pydantic Optional)
    op.add_column("tickets", sa.Column("topic", sa.String(255), nullable=True))
    op.add_column("tickets", sa.Column("position", sa.String(255), nullable=True))
    op.add_column("tickets", sa.Column("phone", sa.String(32), nullable=True))
    op.add_column("tickets", sa.Column("work_email", sa.String(255), nullable=True))
    op.add_column("tickets", sa.Column("backup_email", sa.String(255), nullable=True))

    # 2) Зробити dept nullable (у тебе в схемі Optional)
    op.alter_column("tickets", "dept", existing_type=sa.String(length=64), nullable=True)

    # 3) Індекси для зручних фільтрів
    op.create_index("ix_tickets_topic", "tickets", ["topic"], unique=False)
    op.create_index("ix_tickets_phone", "tickets", ["phone"], unique=False)
    # (dept уже можна було індексувати в іншій ревізії; якщо нема — додай)
    op.create_index("ix_tickets_dept", "tickets", ["dept"], unique=False)

    # 4) CHECK для резервного e-mail (дозволяє звичайні та внутрішні домени)
    op.execute("""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_tickets_backup_email') THEN
                ALTER TABLE tickets DROP CONSTRAINT chk_tickets_backup_email;
            END IF;
        END$$;
    """)
    op.execute(r"""
        ALTER TABLE tickets
        ADD CONSTRAINT chk_tickets_backup_email
        CHECK (
            backup_email IS NULL OR
            backup_email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+(\.[A-Za-z]{2,})?$'
        );
    """)

def downgrade():
    op.execute("ALTER TABLE tickets DROP CONSTRAINT IF EXISTS chk_tickets_backup_email;")
    op.drop_index("ix_tickets_dept", table_name="tickets")
    op.drop_index("ix_tickets_phone", table_name="tickets")
    op.drop_index("ix_tickets_topic", table_name="tickets")
    op.drop_column("tickets", "backup_email")
    op.drop_column("tickets", "work_email")
    op.drop_column("tickets", "phone")
    op.drop_column("tickets", "position")
    op.drop_column("tickets", "topic")
    # повернути dept NOT NULL (якщо потрібно)
    op.alter_column("tickets", "dept", existing_type=sa.String(length=64), nullable=False)
