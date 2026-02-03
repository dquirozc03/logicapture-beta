"""unicidad parcial para AWB y unica para historicos

Revision ID: 8379a6396418
Revises: 8e61a80b2532
Create Date: 2026-02-02 17:16:40.450207

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# tipos históricos que son únicos para siempre
TIPOS_HISTORICOS = (
    "O_BETA",
    "BOOKING",
    "TERMOGRAFO",
    "PS_BETA",
    "PS_ADUANA",
    "PS_OPERADOR",
    "SENASA_PS_LINEA",
)

# revision identifiers, used by Alembic.
revision: str = "8379a6396418"
down_revision: Union[str, Sequence[str], None] = "8e61a80b2532"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Cambia el modelo de unicidad:
    - Elimina UNIQUE(tipo, valor) global porque impide reutilizar AWB luego de liberarlo.
    - Crea un índice único parcial para históricos: UNIQUE(tipo, valor) donde tipo IN (...)
    - Crea un índice único parcial para AWB vigente: UNIQUE(tipo, valor) donde tipo='AWB' AND vigente=true
    """
    # 1) Drop constraint global (si existe) que fue creado por UniqueConstraint en el modelo
    op.drop_constraint("uq_unicos_tipo_valor", "his_unicos", type_="unique")

    # 2) Índice único parcial para históricos (para siempre)
    #    Esto garantiza que nunca se repitan esos valores en toda la historia.
    op.create_index(
        "ux_his_unicos_historicos_tipo_valor",
        "his_unicos",
        ["tipo", "valor"],
        unique=True,
        postgresql_where=sa.text(f"tipo IN {TIPOS_HISTORICOS}"),
    )

    # 3) Índice único parcial para AWB vigente
    #    Esto permite repetir AWB en el historial (vigente=false), pero bloquea si está vigente=true.
    op.create_index(
        "ux_his_unicos_awb_vigente",
        "his_unicos",
        ["tipo", "valor"],
        unique=True,
        postgresql_where=sa.text("tipo = 'AWB' AND vigente = true"),
    )


def downgrade() -> None:
    """
    Revierte los índices parciales y restaura el constraint global.
    (No recomendado para operación con AWB reutilizable, pero sirve como rollback.)
    """
    op.drop_index("ux_his_unicos_awb_vigente", table_name="his_unicos")
    op.drop_index("ux_his_unicos_historicos_tipo_valor", table_name="his_unicos")

    op.create_unique_constraint("uq_unicos_tipo_valor", "his_unicos", ["tipo", "valor"])
