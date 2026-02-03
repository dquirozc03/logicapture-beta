from sqlalchemy import String, Integer, DateTime, func, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class RegistroOperativo(Base):
    __tablename__ = "ope_registros"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    # FECHA del registro (auto)
    fecha_registro: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    # Datos operativos (pueden venir de correo/OCR o manual)
    o_beta: Mapped[str | None] = mapped_column(String(50), nullable=True)
    booking: Mapped[str | None] = mapped_column(String(50), nullable=True)
    awb: Mapped[str | None] = mapped_column(String(50), nullable=True)  # contenedor

    # Relaciones con catálogos
    chofer_id: Mapped[int] = mapped_column(ForeignKey("cat_choferes.id"), nullable=False)
    vehiculo_id: Mapped[int] = mapped_column(ForeignKey("cat_vehiculos.id"), nullable=False)
    transportista_id: Mapped[int] = mapped_column(ForeignKey("cat_transportistas.id"), nullable=False)

    # Keyset / unicidad (por ahora solo guardamos; luego validaremos)
    termografos: Mapped[str | None] = mapped_column(String(200), nullable=True)

    ps_beta: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ps_aduana: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ps_operador: Mapped[str | None] = mapped_column(String(80), nullable=True)

    senasa: Mapped[str | None] = mapped_column(String(80), nullable=True)
    ps_linea: Mapped[str | None] = mapped_column(String(80), nullable=True)
    senasa_ps_linea: Mapped[str | None] = mapped_column(String(120), nullable=True)

    dam: Mapped[str | None] = mapped_column(String(80), nullable=True)

    estado: Mapped[str] = mapped_column(String(20), default="borrador", nullable=False)

    creado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    actualizado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    # Relaciones ORM (solo para joins fáciles)
    chofer = relationship("Chofer")
    vehiculo = relationship("Vehiculo")
    transportista = relationship("Transportista")
