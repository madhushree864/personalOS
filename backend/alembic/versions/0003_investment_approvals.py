from alembic import op
import sqlalchemy as sa

revision = "0003_investment_approvals"
down_revision = "0002_security_hardening"
branch_labels = None
depends_on = None

def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "investment_approvals" not in inspector.get_table_names():
        op.create_table(
            "investment_approvals",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("proposal_id", sa.String(64), sa.ForeignKey("investment_proposals.id"), nullable=False),
            sa.Column("owner_id", sa.String(64), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="pending_user"),
            sa.Column("requested_by", sa.String(64), nullable=False),
            sa.Column("approved_by", sa.String(64), nullable=True),
            sa.Column("mfa_verified_at", sa.DateTime(), nullable=True),
            sa.Column("approved_at", sa.DateTime(), nullable=True),
            sa.Column("rejected_at", sa.DateTime(), nullable=True),
            sa.Column("executed_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("proposal_id"),
        )
        op.create_index("ix_investment_approvals_proposal_id", "investment_approvals", ["proposal_id"])
        op.create_index("ix_investment_approvals_owner_id", "investment_approvals", ["owner_id"])

def downgrade():
    op.drop_index("ix_investment_approvals_owner_id", table_name="investment_approvals")
    op.drop_index("ix_investment_approvals_proposal_id", table_name="investment_approvals")
    op.drop_table("investment_approvals")
