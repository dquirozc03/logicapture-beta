from pydantic import BaseModel, Field
from typing import Optional


# ---------- CHOFERES ----------
class ChoferCrear(BaseModel):
    dni: str = Field(..., max_length=20)
    primer_nombre: str = Field(..., max_length=80)
    apellido_paterno: str = Field(..., max_length=80)
    apellido_materno: Optional[str] = Field(None, max_length=80)
    licencia: Optional[str] = Field(None, max_length=50)
    estado: str = Field("activo", max_length=20)


class ChoferRespuesta(BaseModel):
    id: int
    dni: str
    primer_nombre: str
    apellido_paterno: str
    apellido_materno: Optional[str]
    licencia: Optional[str]
    estado: str
    nombre_para_sap: str

    class Config:
        from_attributes = True


# ---------- VEHICULOS ----------
from pydantic import BaseModel, Field
from typing import Optional, Literal


class VehiculoCrear(BaseModel):
    placa_tracto: str = Field(..., max_length=20, examples=["ABC123"])
    placa_carreta: Optional[str] = Field(None, max_length=20, examples=["XYZ987"])
    placas: str = Field(..., max_length=50, examples=["ABC123/XYZ987"])

    marca: Optional[str] = Field(None, max_length=50, examples=["VOLVO"])
    cert_vehicular: Optional[str] = Field(None, max_length=80, examples=["CERT-001"])

    # Medidas en METROS (m)
    largo_tracto: float = Field(..., gt=0, examples=[6.80])
    ancho_tracto: float = Field(..., gt=0, examples=[2.50])
    alto_tracto: float = Field(..., gt=0, examples=[3.20])

    largo_carreta: float = Field(..., gt=0, examples=[12.00])
    ancho_carreta: float = Field(..., gt=0, examples=[2.50])
    alto_carreta: float = Field(..., gt=0, examples=[3.20])

    configuracion_vehicular: Literal["T3/S3", "T3/S2", "T3/Se2"]

    # Pesos netos en KG
    peso_neto_carreta: int = Field(..., gt=0, examples=[8000])
    peso_neto_tracto: int = Field(..., gt=0, examples=[9000])

    estado: str = Field("activo", max_length=20)


class VehiculoRespuesta(BaseModel):
    id: int
    placa_tracto: str
    placa_carreta: Optional[str]
    placas: str
    marca: Optional[str]
    cert_vehicular: Optional[str]

    largo_tracto: float
    ancho_tracto: float
    alto_tracto: float
    largo_carreta: float
    ancho_carreta: float
    alto_carreta: float

    configuracion_vehicular: str
    peso_neto_carreta: int
    peso_neto_tracto: int
    peso_bruto_vehicular: int

    estado: str

    class Config:
        from_attributes = True


# ---------- TRANSPORTISTAS ----------
class TransportistaCrear(BaseModel):
    codigo_sap: str = Field(..., max_length=30)
    ruc: str = Field(..., max_length=20)
    nombre_transportista: str = Field(..., max_length=200)
    partida_registral: Optional[str] = Field(None, max_length=80)
    estado: str = Field("activo", max_length=20)


class TransportistaRespuesta(BaseModel):
    id: int
    codigo_sap: str
    ruc: str
    nombre_transportista: str
    partida_registral: Optional[str]
    estado: str

    class Config:
        from_attributes = True
