from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.catalogos import Transportista
from app.schemas.catalogos import TransportistaCrear, TransportistaRespuesta

router = APIRouter(prefix="/api/v1/transportistas", tags=["Transportistas"])


@router.post("", response_model=TransportistaRespuesta)
def crear_transportista(payload: TransportistaCrear, db: Session = Depends(get_db)):
    existe = db.query(Transportista).filter(
        or_(Transportista.ruc == payload.ruc, Transportista.codigo_sap == payload.codigo_sap)
    ).first()
    if existe:
        raise HTTPException(status_code=409, detail="Ya existe un transportista con ese RUC o Código SAP")

    t = Transportista(**payload.model_dump())
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


@router.get("", response_model=list[TransportistaRespuesta])
def listar_transportistas(db: Session = Depends(get_db), limit: int = 50, offset: int = 0):
    return db.query(Transportista).order_by(Transportista.id.desc()).offset(offset).limit(limit).all()


@router.get("/buscar", response_model=list[TransportistaRespuesta])
def buscar(texto: str, db: Session = Depends(get_db), limit: int = 20):
    """
    - Si 'texto' parece RUC (solo dígitos), busca exacto.
    - Si no, busca por nombre (contiene, case-insensitive).
    """
    texto = texto.strip()
    q = db.query(Transportista)

    if texto.isdigit():
        res = q.filter(Transportista.ruc == texto).limit(limit).all()
    else:
        res = q.filter(Transportista.nombre_transportista.ilike(f"%{texto}%")).limit(limit).all()

    if not res:
        raise HTTPException(status_code=404, detail="No se encontraron transportistas")
    return res
