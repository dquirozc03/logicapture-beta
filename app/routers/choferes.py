from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.catalogos import Chofer
from app.schemas.catalogos import ChoferCrear, ChoferRespuesta

router = APIRouter(prefix="/api/v1/choferes", tags=["Choferes"])


@router.post("", response_model=ChoferRespuesta)
def crear_chofer(payload: ChoferCrear, db: Session = Depends(get_db)):
    existe = db.query(Chofer).filter(Chofer.dni == payload.dni).first()
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe un chofer con ese DNI")

    chofer = Chofer(**payload.model_dump())
    db.add(chofer)
    db.commit()
    db.refresh(chofer)

    # Pydantic no “ve” property automáticamente a veces; la incluimos manualmente en respuesta
    data = ChoferRespuesta.model_validate(chofer).model_dump()
    data["nombre_para_sap"] = chofer.nombre_para_sap
    return data


@router.get("", response_model=list[ChoferRespuesta])
def listar_choferes(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    items = db.query(Chofer).order_by(Chofer.id.desc()).offset(offset).limit(limit).all()
    resp = []
    for ch in items:
        d = ChoferRespuesta.model_validate(ch).model_dump()
        d["nombre_para_sap"] = ch.nombre_para_sap
        resp.append(d)
    return resp


@router.get("/buscar", response_model=ChoferRespuesta)
def buscar_por_dni(dni: str, db: Session = Depends(get_db)):
    ch = db.query(Chofer).filter(Chofer.dni == dni).first()
    if not ch:
        raise HTTPException(status_code=404, detail="Chofer no encontrado")
    d = ChoferRespuesta.model_validate(ch).model_dump()
    d["nombre_para_sap"] = ch.nombre_para_sap
    return d
