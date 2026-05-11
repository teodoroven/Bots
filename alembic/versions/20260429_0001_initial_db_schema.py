"""initial db schema

Revision ID: 20260429_0001
Revises:
Create Date: 2026-04-29
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260429_0001"
down_revision: str | None = None
branch_labels: str | None = None
depends_on: str | None = None


def json_type() -> sa.JSON:
    return sa.JSON().with_variant(postgresql.JSONB(astext_type = sa.Text()), "postgresql")


def upgrade():
    op.create_table(
        "app_state",
        sa.Column("id", sa.Integer(), nullable = False),
        sa.Column("message_id", sa.Integer(), nullable = False),
        sa.Column("session_id", sa.Integer(), nullable = False),
        sa.Column("event_id", sa.Integer(), nullable = False),
        sa.Column("user_id", sa.Integer(), nullable = False),
        sa.Column("conv_id", sa.Integer(), nullable = False),
        sa.Column("client_id", sa.Integer(), nullable = False),
        sa.Column("element_id", sa.Integer(), nullable = False),
        sa.Column("message_queue_id", sa.Integer(), nullable = False),
        sa.Column("bot_enabled", sa.Boolean(), nullable = False),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.Column("updated_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.PrimaryKeyConstraint("id", name = op.f("pk_app_state")),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable = False),
        sa.Column("access_level", sa.Integer(), nullable = False),
        sa.Column("payload", json_type(), nullable = False),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.Column("updated_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.PrimaryKeyConstraint("id", name = op.f("pk_users")),
    )
    op.create_table(
        "conversations",
        sa.Column("id", sa.Integer(), nullable = False),
        sa.Column("payload", json_type(), nullable = False),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.Column("updated_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.PrimaryKeyConstraint("id", name = op.f("pk_conversations")),
    )
    op.create_table(
        "bot_configs",
        sa.Column("id", sa.Integer(), autoincrement = True, nullable = False),
        sa.Column("position", sa.Integer(), nullable = False),
        sa.Column("bot_key", sa.String(length = 32), nullable = False),
        sa.Column("token", sa.String(length = 512), nullable = False),
        sa.Column("name", sa.String(length = 255), nullable = False),
        sa.Column("group_id", sa.BigInteger(), nullable = False),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.Column("updated_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.PrimaryKeyConstraint("id", name = op.f("pk_bot_configs")),
        sa.UniqueConstraint("bot_key", "group_id", name = "uq_bot_configs_bot_key_group_id"),
    )
    op.create_table(
        "storage_documents",
        sa.Column("key", sa.String(length = 128), nullable = False),
        sa.Column("payload", json_type(), nullable = False),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.Column("updated_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.PrimaryKeyConstraint("key", name = op.f("pk_storage_documents")),
    )
    op.create_table(
        "admins",
        sa.Column("user_id", sa.Integer(), nullable = False),
        sa.Column("access_level", sa.Integer(), nullable = False),
        sa.Column("permissions", json_type(), nullable = False),
        sa.Column("notifications", json_type(), nullable = False),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.Column("updated_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name = op.f("fk_admins_user_id_users"), ondelete = "CASCADE"),
        sa.PrimaryKeyConstraint("user_id", name = op.f("pk_admins")),
    )
    op.create_table(
        "user_chat_ids",
        sa.Column("id", sa.Integer(), autoincrement = True, nullable = False),
        sa.Column("user_id", sa.Integer(), nullable = False),
        sa.Column("bot_key", sa.String(length = 32), nullable = False),
        sa.Column("chat_id", sa.BigInteger(), nullable = False),
        sa.Column("created_at", sa.DateTime(timezone = True), server_default = sa.text("CURRENT_TIMESTAMP"), nullable = False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name = op.f("fk_user_chat_ids_user_id_users"), ondelete = "CASCADE"),
        sa.PrimaryKeyConstraint("id", name = op.f("pk_user_chat_ids")),
        sa.UniqueConstraint("bot_key", "chat_id", name = "uq_user_chat_ids_bot_key_chat_id"),
    )
    op.create_index(op.f("ix_user_chat_ids_user_id"), "user_chat_ids", ["user_id"], unique = False)


def downgrade():
    op.drop_index(op.f("ix_user_chat_ids_user_id"), table_name = "user_chat_ids")
    op.drop_table("user_chat_ids")
    op.drop_table("admins")
    op.drop_table("storage_documents")
    op.drop_table("bot_configs")
    op.drop_table("conversations")
    op.drop_table("users")
    op.drop_table("app_state")
