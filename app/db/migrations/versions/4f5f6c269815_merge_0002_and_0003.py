"""merge 0002 and 0003

Revision ID: 4f5f6c269815
Revises: 0002_add_qa_and_ticket_extra, 0003_tickets_contact_fields
Create Date: 2025-11-07 10:58:30.237958
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '4f5f6c269815'
down_revision = ('0002_add_qa_and_ticket_extra', '0003_tickets_contact_fields')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
