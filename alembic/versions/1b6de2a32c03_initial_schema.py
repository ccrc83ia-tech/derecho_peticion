"""initial_schema

Revision ID: 1b6de2a32c03
Revises:
Create Date: 2026-04-08
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "1b6de2a32c03"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("tenant_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("legal_rules", JSONB(), nullable=False, server_default="[]"),
        sa.Column("branding", JSONB(), nullable=False, server_default="{}"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("tenant_id"),
    )

    op.create_table(
        "templates",
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("fields", JSONB(), nullable=False, server_default="[]"),
        sa.Column("system_prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("legal_rules", JSONB(), nullable=False, server_default="[]"),
        sa.PrimaryKeyConstraint("template_id"),
    )

    op.create_table(
        "template_documents",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.String(), nullable=False),
        sa.Column("doc_name", sa.String(), nullable=False),
        sa.Column("file_type", sa.String(), nullable=False, server_default=""),
        sa.Column("chunks_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "uploaded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["template_id"], ["templates.template_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("template_id", "doc_name"),
    )
    op.create_index("ix_template_documents_template_id", "template_documents", ["template_id"])

    op.create_table(
        "entities",
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("nit", sa.String(), nullable=False, server_default=""),
        sa.Column("address", sa.String(), nullable=False, server_default=""),
        sa.Column("city", sa.String(), nullable=False, server_default=""),
        sa.Column("phone", sa.String(), nullable=False, server_default=""),
        sa.Column("email", sa.String(), nullable=False, server_default=""),
        sa.Column("legal_rep", sa.String(), nullable=False, server_default=""),
        sa.Column("entity_type", sa.String(), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("entity_id"),
    )
    op.create_index("ix_entities_name", "entities", ["name"])

    op.create_table(
        "users",
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, server_default=""),
        sa.Column("role", sa.String(), nullable=False, server_default="pasante"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("password_hash", sa.String(), nullable=False, server_default=""),
        sa.PrimaryKeyConstraint("user_id"),
        sa.UniqueConstraint("username"),
    )
    op.create_index("ix_users_username", "users", ["username"])


def downgrade() -> None:
    op.drop_table("template_documents")
    op.drop_table("templates")
    op.drop_table("tenants")
    op.drop_table("entities")
    op.drop_table("users")
