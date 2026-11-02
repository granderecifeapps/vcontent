"""esquema inicial do VContent"""

import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(160), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("phone", sa.String(40)),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("role in ('admin', 'client')", name="ck_users_role"),
    )
    op.create_index("ix_users_role", "users", ["role"])

    op.create_table(
        "password_reset_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_password_reset_user", "password_reset_tokens", ["user_id"])

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("ip", sa.String(64)),
        sa.Column("user_agent", sa.String(300)),
    )
    op.create_index("ix_refresh_user", "refresh_tokens", ["user_id"])

    op.create_table(
        "clients",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("company_name", sa.String(160), nullable=False),
        sa.Column("contact_name", sa.String(160), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(40)),
        sa.Column("logo_key", sa.String(400)),
        sa.Column("description", sa.Text()),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status in ('active', 'inactive')", name="ck_clients_status"),
    )
    op.create_index("ix_clients_email", "clients", ["email"])

    op.create_table(
        "client_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("client_id", "user_id", name="uq_client_user"),
    )
    op.create_index("ix_client_users_client", "client_users", ["client_id"])

    op.create_table(
        "platforms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("slug", sa.String(40), nullable=False, unique=True),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )

    op.create_table(
        "content_formats",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("platform_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platforms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("slug", sa.String(40), nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("media_type", sa.String(30), nullable=False),
        sa.Column("allows_hashtags", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("min_files", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("max_files", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("platform_id", "slug", name="uq_format_platform_slug"),
        sa.CheckConstraint(
            "media_type in ('single_image', 'multi_image', 'video', 'image_or_video')",
            name="ck_format_media_type",
        ),
    )

    op.create_table(
        "content_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("client_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("clients.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("platform_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platforms.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("format_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_formats.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("internal_description", sa.Text()),
        sa.Column("scheduled_date", sa.Date()),
        sa.Column("scheduled_time", sa.Time()),
        sa.Column("caption", sa.Text()),
        sa.Column("copy_text", sa.Text()),
        sa.Column("hashtags", sa.Text()),
        sa.Column("status", sa.String(32), nullable=False, server_default="draft"),
        sa.Column("internal_notes", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint(
            "status in ('draft','pending_approval','approved','changes_requested','in_review','resubmitted','published','cancelled')",
            name="ck_content_status",
        ),
    )
    op.create_index("ix_content_client_status", "content_items", ["client_id", "status"])
    op.create_index("ix_content_scheduled", "content_items", ["scheduled_date"])
    op.create_index("ix_content_deleted", "content_items", ["deleted_at"])
    op.create_index("ix_content_platform", "content_items", ["platform_id"])
    op.create_index("ix_content_status", "content_items", ["status"])

    op.create_table(
        "content_media",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storage_key", sa.String(400), nullable=False),
        sa.Column("original_filename", sa.String(180), nullable=False),
        sa.Column("mime_type", sa.String(80), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_media_content_order", "content_media", ["content_id", "sort_order"])

    op.create_table(
        "approval_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("action", sa.String(40), nullable=False),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("reason", sa.Text()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_approval_content_created", "approval_history", ["content_id", "created_at"])

    op.create_table(
        "content_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("content_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_comments_content", "content_comments", ["content_id"])

    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", sa.String(60), nullable=False),
        sa.Column("title", sa.String(180), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("data", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("channels", postgresql.JSONB(), nullable=False, server_default=sa.text("'[\"in_app\"]'::jsonb")),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_notifications_user_read", "notifications", ["user_id", "read_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL")),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("entity_type", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.String(64)),
        sa.Column("details", postgresql.JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("ip", sa.String(64)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_created", "audit_logs", ["created_at"])
    op.create_index("ix_audit_entity", "audit_logs", ["entity_type", "entity_id"])

    platforms = sa.table(
        "platforms",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("sort_order", sa.Integer),
    )
    formats = sa.table(
        "content_formats",
        sa.column("id", postgresql.UUID(as_uuid=True)),
        sa.column("platform_id", postgresql.UUID(as_uuid=True)),
        sa.column("slug", sa.String),
        sa.column("name", sa.String),
        sa.column("media_type", sa.String),
        sa.column("allows_hashtags", sa.Boolean),
        sa.column("min_files", sa.Integer),
        sa.column("max_files", sa.Integer),
        sa.column("sort_order", sa.Integer),
    )
    tiktok = uuid.UUID("11111111-1111-1111-1111-111111111111")
    instagram = uuid.UUID("22222222-2222-2222-2222-222222222222")
    op.bulk_insert(
        platforms,
        [
            {"id": tiktok, "slug": "tiktok", "name": "TikTok", "is_active": True, "sort_order": 1},
            {"id": instagram, "slug": "instagram", "name": "Instagram", "is_active": True, "sort_order": 2},
        ],
    )
    op.bulk_insert(
        formats,
        [
            {"id": uuid.UUID("11111111-1111-1111-1111-111111111101"), "platform_id": tiktok, "slug": "static", "name": "Foto única", "media_type": "single_image", "allows_hashtags": True, "min_files": 1, "max_files": 1, "sort_order": 1},
            {"id": uuid.UUID("11111111-1111-1111-1111-111111111102"), "platform_id": tiktok, "slug": "carousel", "name": "Carrossel", "media_type": "multi_image", "allows_hashtags": True, "min_files": 2, "max_files": 10, "sort_order": 2},
            {"id": uuid.UUID("11111111-1111-1111-1111-111111111103"), "platform_id": tiktok, "slug": "video", "name": "Vídeo", "media_type": "video", "allows_hashtags": True, "min_files": 1, "max_files": 1, "sort_order": 3},
            {"id": uuid.UUID("22222222-2222-2222-2222-222222222201"), "platform_id": instagram, "slug": "post", "name": "Post estático", "media_type": "single_image", "allows_hashtags": False, "min_files": 1, "max_files": 1, "sort_order": 1},
            {"id": uuid.UUID("22222222-2222-2222-2222-222222222202"), "platform_id": instagram, "slug": "carousel", "name": "Carrossel", "media_type": "multi_image", "allows_hashtags": False, "min_files": 2, "max_files": 10, "sort_order": 2},
            {"id": uuid.UUID("22222222-2222-2222-2222-222222222203"), "platform_id": instagram, "slug": "reels", "name": "Reels", "media_type": "video", "allows_hashtags": False, "min_files": 1, "max_files": 1, "sort_order": 3},
            {"id": uuid.UUID("22222222-2222-2222-2222-222222222204"), "platform_id": instagram, "slug": "stories", "name": "Stories", "media_type": "image_or_video", "allows_hashtags": False, "min_files": 1, "max_files": 1, "sort_order": 4},
        ],
    )


def downgrade() -> None:
    for name in (
        "audit_logs",
        "notifications",
        "content_comments",
        "approval_history",
        "content_media",
        "content_items",
        "content_formats",
        "platforms",
        "client_users",
        "clients",
        "refresh_tokens",
        "password_reset_tokens",
        "users",
    ):
        op.drop_table(name)
