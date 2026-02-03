from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class RegistroCrear(BaseModel):
    # Entrada: puede venir manual o automático
    o_beta: Optional[str] = Field(None, max_length=50)
    booking: Optional[str] = Field(None, max_length=50)
    awb: Optional[str] = Field(None, max_length=50)

    # Referencias para autocompletar desde catálogos:
    dni: str = Field(..., description="DNI del chofer")
    placas: str = Field(..., description="Placas normalizadas tracto/carreta, ej: ABC123/XYZ987")

    # Transportista: puedes mandar ruc o codigo_sap (uno de los dos)
    ruc: Optional[str] = Field(None, max_length=20)
    codigo_sap: Optional[str] = Field(None, max_length=30)

    # Keyset
    termografos: Optional[str] = Field(None, description="Ej: T1/T2")
    ps_beta: Optional[str] = None
    ps_aduana: Optional[str] = None
    ps_operador: Optional[str] = None
    senasa: Optional[str] = None
    ps_linea: Optional[str] = None

    dam: Optional[str] = None


class RegistroRespuesta(BaseModel):
    id: int
    fecha_registro: datetime
    estado: str

    class Config:
        from_attributes = True


class FilaSapRespuesta(BaseModel):
    FECHA: str
    O_BETA: str
    BOOKING: str
    AWB: str
    MARCA: str
    PLACAS: str
    DNI: str
    CHOFER: str
    LICENCIA: str
    TERMOGRAFOS: str
    CODIGO_SAP: str
    TRANSPORTISTA: str
    PS_BETA: str
    PS_ADUANA: str
    PS_OPERADOR: str
    SENASA_PS_LINEA: str
    N_DAM: str
    P_REGISTRAL: str
    CER_VEHICULAR: str
