from __future__ import annotations
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

class RefPosicionamiento(Base):
    __tablename__ = "ref_posicionamiento"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)

    o_beta: Mapped[str | None] = mapped_column(String(30), nullable=True)
    awb: Mapped[str | None] = mapped_column(String(30), nullable=True)

    actualizado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
