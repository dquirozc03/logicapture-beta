from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database import get_db
from app.configuracion import settings
from app.models.ref_posicionamiento import RefPosicionamiento
from app.models.ref_booking_dam import RefBookingDam


router = APIRouter(prefix="/api/v1/sync", tags=["Sync"])


def normalizar(v: str | None) -> str | None:
    if v is None:
        return None
    v = " ".join(v.strip().split()).upper()
    return v or None


def validar_token(x_sync_token: str | None):
    if not x_sync_token or x_sync_token != settings.SYNC_TOKEN:
        raise HTTPException(status_code=401, detail="Token de sync inválido")


class PosicionamientoItem(BaseModel):
    booking: str
    o_beta: Optional[str] = None
    awb: Optional[str] = None


class DamItem(BaseModel):
    booking: str
    dam: str


@router.post("/posicionamiento")
def sync_posicionamiento(
    items: List[PosicionamientoItem],
    db: Session = Depends(get_db),
    x_sync_token: str | None = Header(default=None),
):
    validar_token(x_sync_token)

    upserts = 0
    for it in items:
        booking = normalizar(it.booking)
        if not booking:
            continue

        row = db.query(RefPosicionamiento).filter(RefPosicionamiento.booking == booking).first()
        if row:
            row.o_beta = normalizar(it.o_beta)
            row.awb = normalizar(it.awb)
        else:
            db.add(RefPosicionamiento(
                booking=booking,
                o_beta=normalizar(it.o_beta),
                awb=normalizar(it.awb),
            ))
        upserts += 1

    db.commit()
    return {"ok": True, "upserts": upserts}


@router.post("/dams")
def sync_dams(
    items: List[DamItem],
    db: Session = Depends(get_db),
    x_sync_token: str | None = Header(default=None),
):
    validar_token(x_sync_token)

    upserts = 0
    for it in items:
        booking = normalizar(it.booking)
        dam = normalizar(it.dam)
        if not booking or not dam:
            continue

        row = db.query(RefBookingDam).filter(RefBookingDam.booking == booking).first()
        if row:
            row.dam = dam
        else:
            db.add(RefBookingDam(booking=booking, dam=dam))
        upserts += 1

    db.commit()
    return {"ok": True, "upserts": upserts}
