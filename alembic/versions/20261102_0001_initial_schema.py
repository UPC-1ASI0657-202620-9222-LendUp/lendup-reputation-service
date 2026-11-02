"""Create reputation service schema.

Revision ID: 20261102_0001
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "20261102_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "evaluaciones",
        sa.Column("id", sa.Uuid(as_uuid=True, native_uuid=False), primary_key=True),
        sa.Column("prestamo_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False),
        sa.Column("evaluador_usuario_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False),
        sa.Column("evaluado_usuario_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False),
        sa.Column("puntaje", sa.Integer(), nullable=False),
        sa.Column("comentario", sa.String(400)),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("puntaje BETWEEN 1 AND 5", name="ck_evaluaciones_puntaje"),
        sa.UniqueConstraint(
            "prestamo_id", "evaluador_usuario_id", name="uq_evaluacion_prestamo_evaluador"
        ),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_evaluaciones_prestamo_id", "evaluaciones", ["prestamo_id"])
    op.create_index(
        "ix_evaluaciones_evaluado_fecha",
        "evaluaciones",
        ["evaluado_usuario_id", "registrada_en"],
    )

    op.create_table(
        "prestamos_evaluables",
        sa.Column("prestamo_id", sa.Uuid(as_uuid=True, native_uuid=False), primary_key=True),
        sa.Column(
            "prestamista_usuario_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False
        ),
        sa.Column(
            "prestatario_usuario_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False
        ),
        sa.Column("finalizado_en", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "source_event_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False, unique=True
        ),
        sa.Column("aggregate_version", sa.BigInteger()),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_prestamos_evaluables_prestamista_usuario_id",
        "prestamos_evaluables",
        ["prestamista_usuario_id"],
    )
    op.create_index(
        "ix_prestamos_evaluables_prestatario_usuario_id",
        "prestamos_evaluables",
        ["prestatario_usuario_id"],
    )

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Uuid(as_uuid=True, native_uuid=False), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_attempt_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("claimed_by", sa.String(100)),
        sa.Column("claimed_at", sa.DateTime(timezone=True)),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_outbox_pending", "outbox_events", ["published_at", "next_attempt_at"])

    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.Uuid(as_uuid=True, native_uuid=False), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("aggregate_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False),
        sa.Column("aggregate_version", sa.BigInteger()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_processed_events_aggregate_id", "processed_events", ["aggregate_id"])

    op.create_table(
        "registro_auditoria",
        sa.Column("id", sa.Uuid(as_uuid=True, native_uuid=False), primary_key=True),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("actor_usuario_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False),
        sa.Column("entity_id", sa.Uuid(as_uuid=True, native_uuid=False), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("registrada_en", sa.DateTime(timezone=True), nullable=False),
        mysql_charset="utf8mb4",
    )
    op.create_index(
        "ix_audit_actor_time", "registro_auditoria", ["actor_usuario_id", "registrada_en"]
    )


def downgrade() -> None:
    op.drop_table("registro_auditoria")
    op.drop_table("processed_events")
    op.drop_table("outbox_events")
    op.drop_table("prestamos_evaluables")
    op.drop_table("evaluaciones")
