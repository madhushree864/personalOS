from alembic import op
import sqlalchemy as sa
from app.db import Base
from app import models  # noqa: F401 - register all model tables
revision="0001_auth_ownership"; down_revision=None; branch_labels=None; depends_on=None
def upgrade():
    bind = op.get_bind()
    # Make this first revision usable for both new deployments and databases
    # created by the pre-Alembic application.
    Base.metadata.create_all(bind=bind)
    inspector = sa.inspect(bind)
    for table in ("renewals","health_records","holdings","investment_proposals"):
        if "owner_id" not in {c["name"] for c in inspector.get_columns(table)}:
            op.add_column(table,sa.Column("owner_id",sa.String(64),nullable=True))
        if "ix_%s_owner_id"%table not in {i["name"] for i in inspector.get_indexes(table)}:
            op.create_index("ix_%s_owner_id"%table,table,["owner_id"])
    if "user_id" not in {c["name"] for c in inspector.get_columns("audit_entries")}:
        op.add_column("audit_entries",sa.Column("user_id",sa.String(64),nullable=True))
    if "ix_audit_entries_user_id" not in {i["name"] for i in inspector.get_indexes("audit_entries")}:
        op.create_index("ix_audit_entries_user_id","audit_entries",["user_id"])
    # Existing single-user installations are assigned to the first user rather
    # than left globally visible to every subsequently created account.
    for table in ("renewals", "health_records", "holdings", "investment_proposals"):
        bind.execute(sa.text(
            f"UPDATE {table} SET owner_id = (SELECT id FROM users ORDER BY id LIMIT 1) "
            "WHERE owner_id IS NULL"
        ))
def downgrade():
    op.drop_index("ix_audit_entries_user_id",table_name="audit_entries"); op.drop_column("audit_entries","user_id")
    for table in ("investment_proposals","holdings","health_records","renewals"):
        op.drop_index("ix_%s_owner_id"%table,table_name=table); op.drop_column(table,"owner_id")
