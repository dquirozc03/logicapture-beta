from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.catalogos import Vehiculo
from app.schemas.catalogos import VehiculoCrear, VehiculoRespuesta

router = APIRouter(prefix="/api/v1/vehiculos", tags=["Vehículos"])


@router.post("", response_model=VehiculoRespuesta)
def crear_vehiculo(payload: VehiculoCrear, db: Session = Depends(get_db)):
    existe = db.query(Vehiculo).filter(Vehiculo.placas == payload.placas).first()
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe un vehículo con esas placas")

    veh = Vehiculo(**payload.model_dump())

    try:
        veh.aplicar_reglas_configuracion()
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    db.add(veh)
    db.commit()
    db.refresh(veh)
    return veh


@router.get("", response_model=list[VehiculoRespuesta])
def listar_vehiculos(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    return db.query(Vehiculo).order_by(Vehiculo.id.desc()).offset(offset).limit(limit).all()


@router.get("/buscar", response_model=VehiculoRespuesta)
def buscar_por_placas(placas: str, db: Session = Depends(get_db)):
    veh = db.query(Vehiculo).filter(Vehiculo.placas == placas).first()
    if not veh:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado")
    return veh
