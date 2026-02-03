from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.catalogos import Chofer, Vehiculo, Transportista
from app.models.operacion import RegistroOperativo
from app.models.unicos import Unico

# ✅ NUEVO: referencias por booking
from app.models.ref_posicionamiento import RefPosicionamiento
from app.models.ref_booking_dam import RefBookingDam

from app.schemas.operacion import RegistroCrear, RegistroRespuesta, FilaSapRespuesta
from app.utils.unicidad import normalizar, dividir_por_slash, unir_por_slash

router = APIRouter(prefix="/api/v1/registros", tags=["Registros"])

# Únicos históricos (para siempre)
TIPOS_HISTORICOS = {
    "O_BETA",
    "BOOKING",
    "TERMOGRAFO",
    "PS_BETA",
    "PS_ADUANA",
    "PS_OPERADOR",
    "SENASA_PS_LINEA",
}

# Únicos vigentes (Opción A): solo bloquean mientras esté activo el registro
TIPOS_VIGENTES = {"AWB"}


def construir_senasa_ps_linea(senasa: str | None, ps_linea: str | None) -> str | None:
    senasa = (senasa or "").strip()
    ps_linea = (ps_linea or "").strip()

    if senasa and ps_linea:
        # Regla: SENASA/PS.LINXXXX (ps_linea ya trae LINXXXX normalmente)
        return f"{senasa}/PS.{ps_linea}"
    if ps_linea:
        return f"PS.{ps_linea}"
    return None


def safe_str(x) -> str:
    return (x or "").strip()


def obtener_refs_por_booking(db: Session, booking: str | None) -> dict:
    """
    Busca en tablas de referencia:
    - ref_posicionamiento: booking -> o_beta, awb
    - ref_booking_dam: booking -> dam
    Retorna dict con booking normalizado y los campos.
    """
    b = normalizar(booking)
    if not b:
        return {"booking": None, "o_beta": None, "awb": None, "dam": None}

    pos = db.query(RefPosicionamiento).filter(RefPosicionamiento.booking == b).first()
    dam = db.query(RefBookingDam).filter(RefBookingDam.booking == b).first()

    return {
        "booking": b,
        "o_beta": normalizar(pos.o_beta) if pos and pos.o_beta else None,
        "awb": normalizar(pos.awb) if pos and pos.awb else None,
        "dam": normalizar(dam.dam) if dam and dam.dam else None,
    }


def construir_items_unicos(payload: RegistroCrear, senasa_ps_linea_norm: str | None) -> list[tuple[str, str, bool]]:
    """
    Retorna lista de (tipo, valor, vigente)
    - vigente=True solo para AWB (candado temporal)
    - termógrafos y ps_beta se separan por "/"
    """
    items: list[tuple[str, str, bool]] = []

    def add(tipo: str, valor: str | None):
        v = normalizar(valor)
        if not v:
            return
        vigente = tipo in TIPOS_VIGENTES
        items.append((tipo, v, vigente))

    # Históricos
    add("O_BETA", payload.o_beta)
    add("BOOKING", payload.booking)

    # Vigente (temporal)
    add("AWB", payload.awb)

    # TERMOGRAFOS múltiples
    for t in dividir_por_slash(payload.termografos):
        add("TERMOGRAFO", t)

    # PS_BETA puede venir múltiple (hasta 4) separado por "/"
    for ps in dividir_por_slash(payload.ps_beta):
        add("PS_BETA", ps)

    add("PS_ADUANA", payload.ps_aduana)
    add("PS_OPERADOR", payload.ps_operador)

    # Calculado
    add("SENASA_PS_LINEA", senasa_ps_linea_norm)

    return items


def validar_duplicados(db: Session, items: list[tuple[str, str, bool]]) -> list[dict]:
    """
    - Históricos: choca si existe cualquier registro con mismo tipo/valor.
    - Vigentes (AWB): choca solo si existe vigente=True.
    """
    duplicados: list[dict] = []

    for tipo, valor, vigente in items:
        q = db.query(Unico).filter(Unico.tipo == tipo, Unico.valor == valor)
        if vigente:
            q = q.filter(Unico.vigente == True)  # noqa: E712
        existe = q.first()

        if existe:
            duplicados.append(
                {
                    "tipo": tipo,
                    "valor": valor,
                    "mensaje": "Valor ya utilizado (bloqueado por unicidad)"
                    if not vigente
                    else "Valor en uso actualmente (candado vigente)",
                }
            )

    return duplicados


@router.post("", response_model=RegistroRespuesta)
def crear_registro(payload: RegistroCrear, db: Session = Depends(get_db)):
    # 1) Resolver chofer por DNI
    chofer = db.query(Chofer).filter(Chofer.dni == payload.dni).first()
    if not chofer:
        raise HTTPException(status_code=404, detail="Chofer no encontrado por DNI")

    # 2) Resolver vehículo por placas
    vehiculo = db.query(Vehiculo).filter(Vehiculo.placas == payload.placas).first()
    if not vehiculo:
        raise HTTPException(status_code=404, detail="Vehículo no encontrado por placas")

    # 3) Resolver transportista por RUC o Código SAP
    if not payload.ruc and not payload.codigo_sap:
        raise HTTPException(
            status_code=422,
            detail="Debes enviar ruc o codigo_sap para identificar al transportista",
        )

    transportista = (
        db.query(Transportista)
        .filter(
            or_(
                Transportista.ruc == (payload.ruc or "__NO__"),
                Transportista.codigo_sap == (payload.codigo_sap or "__NO__"),
            )
        )
        .first()
    )
    if not transportista:
        raise HTTPException(status_code=404, detail="Transportista no encontrado por RUC o Código SAP")

    # 4) Autocompletar desde referencias por BOOKING (si existe)
    #    - NO pisa lo que el usuario ya envió.
    refs = obtener_refs_por_booking(db, payload.booking)
    if refs["booking"]:
        # normaliza booking sí o sí
        payload.booking = refs["booking"]

        if not normalizar(payload.o_beta) and refs["o_beta"]:
            payload.o_beta = refs["o_beta"]

        if not normalizar(payload.awb) and refs["awb"]:
            payload.awb = refs["awb"]

        # DAM: si en el futuro quitas el campo del request, esto seguirá funcionando
        # mientras el schema lo tenga. Si lo quitas, entonces lo llenaremos en el modelo directamente.
        if hasattr(payload, "dam"):
            if not normalizar(payload.dam) and refs["dam"]:
                payload.dam = refs["dam"]

    # 5) Calcular SENASA/PS.LINEA y normalizarlo
    senasa_ps_linea = construir_senasa_ps_linea(payload.senasa, payload.ps_linea)
    senasa_ps_linea_norm = normalizar(senasa_ps_linea)

    # 6) Normalizar campos que guardaremos en el registro
    o_beta_norm = normalizar(payload.o_beta)
    booking_norm = normalizar(payload.booking)
    awb_norm = normalizar(payload.awb)

    termografos_norm = unir_por_slash(dividir_por_slash(payload.termografos))
    ps_beta_norm = unir_por_slash(dividir_por_slash(payload.ps_beta))

    ps_aduana_norm = normalizar(payload.ps_aduana)
    ps_operador_norm = normalizar(payload.ps_operador)

    senasa_norm = normalizar(payload.senasa)
    ps_linea_norm = normalizar(payload.ps_linea)

    # DAM puede venir o autocompletarse
    dam_norm = normalizar(getattr(payload, "dam", None))

    # 7) Construir items únicos y validar duplicados (después del autocompletado)
    items_unicos = construir_items_unicos(payload, senasa_ps_linea_norm)
    duplicados = validar_duplicados(db, items_unicos)
    if duplicados:
        raise HTTPException(status_code=409, detail={"duplicados": duplicados})

    # 8) Guardar registro + candados en una sola transacción
    reg = RegistroOperativo(
        o_beta=o_beta_norm,
        booking=booking_norm,
        awb=awb_norm,
        chofer_id=chofer.id,
        vehiculo_id=vehiculo.id,
        transportista_id=transportista.id,
        termografos=termografos_norm,
        ps_beta=ps_beta_norm,
        ps_aduana=ps_aduana_norm,
        ps_operador=ps_operador_norm,
        senasa=senasa_norm,
        ps_linea=ps_linea_norm,
        senasa_ps_linea=senasa_ps_linea_norm,
        dam=dam_norm,
        estado="borrador",
    )

    try:
        db.add(reg)
        db.flush()  # obtiene reg.id sin commit

        referencia = f"REG-{reg.id}"

        for tipo, valor, vigente in items_unicos:
            db.add(
                Unico(
                    tipo=tipo,
                    valor=valor,
                    referencia=referencia,
                    usuario="sistema",  # luego lo conectamos a usuarios reales
                    origen="registro",
                    vigente=vigente,
                )
            )

        db.commit()
        db.refresh(reg)
        return reg

    except IntegrityError:
        db.rollback()
        duplicados = validar_duplicados(db, items_unicos)
        if duplicados:
            raise HTTPException(status_code=409, detail={"duplicados": duplicados})
        raise HTTPException(status_code=409, detail="Conflicto de unicidad.")


@router.post("/{registro_id}/cerrar")
def cerrar_registro(registro_id: int, db: Session = Depends(get_db)):
    reg = db.query(RegistroOperativo).filter(RegistroOperativo.id == registro_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    if reg.estado == "cerrado":
        return {"estado": "ya estaba cerrado"}

    reg.estado = "cerrado"

    referencia = f"REG-{reg.id}"
    ahora = datetime.now(timezone.utc)

    # Liberar solo los tipos vigentes (AWB)
    db.query(Unico).filter(
        Unico.referencia == referencia,
        Unico.tipo.in_(list(TIPOS_VIGENTES)),
        Unico.vigente == True  # noqa: E712
    ).update(
        {"vigente": False, "liberado_en": ahora},
        synchronize_session=False
    )

    db.commit()
    return {"estado": "cerrado", "awbs_liberados": True}


@router.get("/{registro_id}/sap", response_model=FilaSapRespuesta)
def obtener_fila_sap(registro_id: int, db: Session = Depends(get_db)):
    reg = (
        db.query(RegistroOperativo)
        .options(
            joinedload(RegistroOperativo.chofer),
            joinedload(RegistroOperativo.vehiculo),
            joinedload(RegistroOperativo.transportista),
        )
        .filter(RegistroOperativo.id == registro_id)
        .first()
    )
    if not reg:
        raise HTTPException(status_code=404, detail="Registro no encontrado")

    fecha_txt = reg.fecha_registro.date().isoformat()

    chofer = reg.chofer
    veh = reg.vehiculo
    tra = reg.transportista

    fila = FilaSapRespuesta(
        FECHA=fecha_txt,
        O_BETA=safe_str(reg.o_beta),
        BOOKING=safe_str(reg.booking),
        AWB=safe_str(reg.awb),
        MARCA=safe_str(veh.marca),
        PLACAS=safe_str(veh.placas),
        DNI=safe_str(chofer.dni),
        CHOFER=chofer.nombre_para_sap,
        LICENCIA=safe_str(chofer.licencia),
        TERMOGRAFOS=safe_str(reg.termografos),
        CODIGO_SAP=safe_str(tra.codigo_sap),
        TRANSPORTISTA=safe_str(tra.nombre_transportista),
        PS_BETA=safe_str(reg.ps_beta),
        PS_ADUANA=safe_str(reg.ps_aduana),
        PS_OPERADOR=safe_str(reg.ps_operador),
        SENASA_PS_LINEA=safe_str(reg.senasa_ps_linea),
        N_DAM=safe_str(reg.dam),
        P_REGISTRAL=safe_str(tra.partida_registral),
        CER_VEHICULAR=safe_str(veh.cert_vehicular),
    )
    return fila
