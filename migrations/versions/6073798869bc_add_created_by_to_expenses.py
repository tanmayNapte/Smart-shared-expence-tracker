# revision identifiers, used by Alembic.
revision = '6073798869bc'
down_revision = '9e43dc25dc73'
branch_labels = None
depends_on = None

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column("expenses", sa.Column("created_by", sa.Integer(), nullable=True))

def downgrade():
    op.drop_column("expenses", "created_by")
