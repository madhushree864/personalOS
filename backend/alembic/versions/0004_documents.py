from alembic import op
import sqlalchemy as sa

revision = "0004_documents"
down_revision = "0003_investment_approvals"
branch_labels = None
depends_on = None


def upgrade():
    inspector = sa.inspect(op.get_bind())
    if "documents" in inspector.get_table_names():
        return
    op.create_table(
        "documents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("owner_id", sa.String(64), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("document_type", sa.String(40), nullable=False),
        sa.Column("content_type", sa.String(120), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="ingested"),
        sa.Column("source", sa.String(120), nullable=False, server_default="upload"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("metadata", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_documents_owner_id", "documents", ["owner_id"])


def downgrade():
    op.drop_index("ix_documents_owner_id", table_name="documents")
    op.drop_table("documents")
