"""${message}
"""
revision = '${up_revision}'
down_revision = ${down_revision if down_revision else None}
branch_labels = ${branch_labels if branch_labels else None}
depends_on = ${depends_on if depends_on else None}

from alembic import op
import sqlalchemy as sa


def upgrade():
    pass


def downgrade():
    pass
