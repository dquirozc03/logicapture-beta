from sqlalchemy import String, Integer, DateTime, func, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.database import Base

# Regla de negocio: peso bruto por configuración
PESO_BRUTO_POR_CONFIG = {
    "T3/S3": 48000,
    "T3/S2": 43000,
    "T3/Se2": 47000,
}


class Chofer(Base):
    __tablename__ = "cat_choferes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    dni: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)

    # Datos separados para formateo requerido
    primer_nombre: Mapped[str] = mapped_column(String(80), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(80), nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column(String(80), nullable=True)

    licencia: Mapped[str | None] = mapped_column(String(50), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="activo", nullable=False)

    creado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def nombre_para_sap(self) -> str:
        """
        Formato requerido: PrimerNombre + ApellidoPaterno + InicialApellidoMaterno.
        Ej: Daniel Quiroz C.
        """
        pn = (self.primer_nombre or "").strip()
        ap = (self.apellido_paterno or "").strip()
        am = (self.apellido_materno or "").strip()

        inicial = ""
        if am:
            inicial = f" {am[0].upper()}."
        return f"{pn} {ap}{inicial}".strip()


class Vehiculo(Base):
    __tablename__ = "cat_vehiculos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    placa_tracto: Mapped[str] = mapped_column(String(20), nullable=False)
    placa_carreta: Mapped[str | None] = mapped_column(String(20), nullable=True)
    placas: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)

    marca: Mapped[str | None] = mapped_column(String(50), nullable=True)
    cert_vehicular: Mapped[str | None] = mapped_column(String(80), nullable=True)

    # Medidas OBLIGATORIAS en METROS (m)
    # Numeric(6, 2) permite hasta 9999.99 (sobrado) y 2 decimales.
    largo_tracto: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    ancho_tracto: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    alto_tracto: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)

    largo_carreta: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    ancho_carreta: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    alto_carreta: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)

    # Configuración OBLIGATORIA
    configuracion_vehicular: Mapped[str] = mapped_column(String(20), nullable=False)

    # Pesos netos OBLIGATORIOS en KG
    peso_neto_carreta: Mapped[int] = mapped_column(Integer, nullable=False)
    peso_neto_tracto: Mapped[int] = mapped_column(Integer, nullable=False)

    # Peso bruto en KG (se calcula automáticamente)
    peso_bruto_vehicular: Mapped[int] = mapped_column(Integer, nullable=False)

    estado: Mapped[str] = mapped_column(String(20), default="activo", nullable=False)

    creado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def aplicar_reglas_configuracion(self) -> None:
        cfg = (self.configuracion_vehicular or "").strip()
        if cfg not in PESO_BRUTO_POR_CONFIG:
            raise ValueError(
                f"Configuración vehicular inválida: {cfg}. Permitidas: {', '.join(PESO_BRUTO_POR_CONFIG.keys())}"
            )

        self.configuracion_vehicular = cfg
        self.peso_bruto_vehicular = PESO_BRUTO_POR_CONFIG[cfg]


class Transportista(Base):
    __tablename__ = "cat_transportistas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    codigo_sap: Mapped[str] = mapped_column(String(30), unique=True, index=True, nullable=False)
    ruc: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    nombre_transportista: Mapped[str] = mapped_column(String(200), index=True, nullable=False)

    partida_registral: Mapped[str | None] = mapped_column(String(80), nullable=True)
    estado: Mapped[str] = mapped_column(String(20), default="activo", nullable=False)

    creado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now())
    actualizado_en: Mapped["DateTime"] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
