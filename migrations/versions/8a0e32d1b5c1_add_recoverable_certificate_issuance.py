"""Add recoverable Fabric issuance state.

Revision ID: 8a0e32d1b5c1
Revises: 4fe49e0e15d7
"""
from alembic import op
import sqlalchemy as sa

revision = "8a0e32d1b5c1"
down_revision = "4fe49e0e15d7"
branch_labels = None
depends_on = None

def upgrade():
    with op.batch_alter_table("certificates") as batch_op:
        batch_op.add_column(sa.Column("issuance_state", sa.String(length=40), nullable=False, server_default="Blockchain Registration Pending"))
        batch_op.add_column(sa.Column("blockchain_registered_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("blockchain_error", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("issuance_attempts", sa.Integer(), nullable=False, server_default="0"))
        batch_op.create_index(batch_op.f("ix_certificates_issuance_state"), ["issuance_state"], unique=False)

def downgrade():
    with op.batch_alter_table("certificates") as batch_op:
        batch_op.drop_index(batch_op.f("ix_certificates_issuance_state"))
        batch_op.drop_column("issuance_attempts")
        batch_op.drop_column("blockchain_error")
        batch_op.drop_column("blockchain_registered_at")
        batch_op.drop_column("issuance_state")
