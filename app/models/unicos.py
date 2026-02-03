from __future__ import annotations

from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func, UniqueConstraint, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base


class Unico(Base):
    __tablename__ = "his_unicos"
    __table_args__ = (
        UniqueConstraint("tipo", "valor", name="uq_unicos_tipo_valor"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    tipo: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    valor: Mapped[str] = mapped_column(String(200), index=True, nullable=False)

    # Auditoría
    fecha_uso: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    referencia: Mapped[str | None] = mapped_column(String(80), nullable=True)
    usuario: Mapped[str | None] = mapped_column(String(80), nullable=True)
    origen: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Vigencia (opción A)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    liberado_en: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    creado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
