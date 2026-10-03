from alembic import op
import sqlalchemy as sa
from passlib.context import CryptContext
import json

revision = "0002_security_hardening"
down_revision = "0001_auth_ownership"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    users = {c["name"] for c in inspector.get_columns("users")}
    if "password_hash" not in users:
        op.alter_column("users", "password", new_column_name="password_hash")
    if "is_active" not in users:
        op.add_column("users", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    if "created_at" not in users:
        op.add_column("users", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    if "updated_at" not in users:
        op.add_column("users", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    password_ctx = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")
    rows = bind.execute(sa.text("SELECT id, password_hash, permissions FROM users")).mappings()
    for row in rows:
        value = row["password_hash"] or ""
        if not value.startswith(("$argon2", "$2a$", "$2b$", "$2y$")):
            bind.execute(sa.text("UPDATE users SET password_hash=:value WHERE id=:id"),
                         {"value": password_ctx.hash(value), "id": row["id"]})
    if "revoked_tokens" not in inspector.get_table_names():
        op.create_table(
            "revoked_tokens",
            sa.Column("jti", sa.String(64), primary_key=True),
            sa.Column("user_id", sa.String(64), nullable=False),
            sa.Column("revoked_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
        )
        op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])
    rows = bind.execute(sa.text("SELECT id, permissions FROM users")).mappings()
    for row in rows:
        try:
            permissions = json.loads(row["permissions"] or "[]")
        except (TypeError, json.JSONDecodeError):
            permissions = []
        aliases = {"renewal:read": "renewal.read", "renewal:write": "renewal.create",
                   "health:read": "health.read", "stock:read": "stock.read",
                   "investment:review": "investment.propose"}
        permissions = [aliases.get(item, item) for item in permissions]
        bind.execute(sa.text("UPDATE users SET permissions=:permissions WHERE id=:id"),
                     {"permissions": json.dumps(permissions), "id": row["id"]})


def downgrade():
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")
    op.drop_column("users", "updated_at")
    op.drop_column("users", "created_at")
    op.drop_column("users", "is_active")
    op.alter_column("users", "password_hash", new_column_name="password")
