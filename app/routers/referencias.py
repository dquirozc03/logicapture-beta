from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.ref_posicionamiento import RefPosicionamiento
from app.models.ref_booking_dam import RefBookingDam

router = APIRouter(prefix="/api/v1/ref", tags=["Referencias"])

def normalizar(v: str) -> str:
    return " ".join(v.strip().split()).upper()

@router.get("/booking/{booking}")
def ref_por_booking(booking: str, db: Session = Depends(get_db)):
    b = normalizar(booking)

    pos = db.query(RefPosicionamiento).filter(RefPosicionamiento.booking == b).first()
    dam = db.query(RefBookingDam).filter(RefBookingDam.booking == b).first()

    if not pos and not dam:
        raise HTTPException(status_code=404, detail="Booking no encontrado en referencias")

    return {
        "booking": b,
        "o_beta": pos.o_beta if pos else None,
        "awb": pos.awb if pos else None,
        "dam": dam.dam if dam else None,
    }
