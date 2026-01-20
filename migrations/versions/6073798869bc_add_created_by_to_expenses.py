from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column("expenses", sa.Column("created_by", sa.Integer(), nullable=True))

def downgrade():
    op.drop_column("expenses", "created_by")
