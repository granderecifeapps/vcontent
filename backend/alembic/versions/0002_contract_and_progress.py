"""contrato do cliente e conteúdo em andamento"""

import sqlalchemy as sa
from alembic import op

revision = "0002_contract_progress"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

STATUS = (
    "status in ('draft','in_progress','pending_approval','approved',"
    "'changes_requested','in_review','resubmitted','published','cancelled')"
)


def upgrade() -> None:
    op.add_column("clients", sa.Column("contract_key", sa.String(400)))
    op.add_column("clients", sa.Column("contract_filename", sa.String(180)))
    op.add_column("clients", sa.Column("contract_uploaded_at", sa.DateTime(timezone=True)))
    op.add_column("content_items", sa.Column("waiting_note", sa.Text()))
    op.drop_constraint("ck_content_status", "content_items", type_="check")
    op.create_check_constraint("ck_content_status", "content_items", STATUS)


def downgrade() -> None:
    op.drop_constraint("ck_content_status", "content_items", type_="check")
    op.create_check_constraint(
        "ck_content_status",
        "content_items",
        "status in ('draft','pending_approval','approved','changes_requested','in_review','resubmitted','published','cancelled')",
    )
    op.drop_column("content_items", "waiting_note")
    op.drop_column("clients", "contract_uploaded_at")
    op.drop_column("clients", "contract_filename")
    op.drop_column("clients", "contract_key")
