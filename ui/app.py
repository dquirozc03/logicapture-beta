import streamlit as st
import requests
import pandas as pd
from io import BytesIO
from urllib.parse import quote

from PIL import ImageGrab, Image  # pillow

API_URL = "http://127.0.0.1:8000/api/v1"

st.set_page_config(page_title="LogiCapture - Registro Operativo", layout="wide")
st.title("📦 LogiCapture – Registro Operativo")
st.caption("UI operativa (MVP 2.2) · OCR + Autocompletado por BOOKING + Semáforo + Bandeja SAP")


# -------------------------
# Session State: inicialización
# -------------------------
def init_state():
    for k in [
        "o_beta", "booking", "awb", "dni", "placas", "ruc", "codigo_sap",
        "termografos", "ps_beta", "ps_aduana", "ps_operador", "senasa", "ps_linea",
        "nuevo_ps", "nuevo_tg",
    ]:
        st.session_state.setdefault(k, "")

    # referencias (posicionamiento/dams)
    st.session_state.setdefault("ref_found", False)
    st.session_state.setdefault("dam_ref", "")
    st.session_state.setdefault("o_beta_ref", "")
    st.session_state.setdefault("awb_ref", "")
    st.session_state.setdefault("last_autofill_ok", None)  # True/False/None

    # registro actual + historial SAP
    st.session_state.setdefault("registro_id", None)
    st.session_state.setdefault("sap_rows", [])          # lista de dicts (incluye REGISTRO_ID)
    st.session_state.setdefault("registro_estado", {})   # {id: "borrador"/"cerrado"}

    # OCR state
    st.session_state.setdefault("ocr_tipo", None)
    st.session_state.setdefault("ocr_mejor", None)
    st.session_state.setdefault("ocr_candidatos", [])
    st.session_state.setdefault("ocr_texto", "")


init_state()


# -------------------------
# Helpers
# -------------------------
def normalizar_txt(s: str) -> str:
    return " ".join((s or "").strip().split()).upper()


def join_slash(existing: str, nuevo: str) -> str:
    existing = (existing or "").strip().strip("/")
    nuevo = (nuevo or "").strip().strip("/")
    if not nuevo:
        return existing
    if not existing:
        return nuevo
    parts = [p for p in existing.split("/") if p.strip()]
    if nuevo not in parts:
        parts.append(nuevo)
    return "/".join(parts)


def aplicar_mejor_valor_ocr():
    tipo = st.session_state.ocr_tipo
    mejor = st.session_state.ocr_mejor
    if not tipo or not mejor:
        return

    mejor = normalizar_txt(mejor)
    if tipo == "BOOKING":
        st.session_state["booking"] = mejor
    elif tipo == "AWB":
        st.session_state["awb"] = mejor

    st.rerun()


def limpiar_referencias():
    st.session_state["ref_found"] = False
    st.session_state["dam_ref"] = ""
    st.session_state["o_beta_ref"] = ""
    st.session_state["awb_ref"] = ""
    st.session_state["last_autofill_ok"] = None
    st.info("Referencias limpiadas.")


def autocompletar_por_booking():
    b = normalizar_txt(st.session_state["booking"])
    if not b:
        st.warning("Ingresa BOOKING primero.")
        st.session_state["last_autofill_ok"] = False
        return

    try:
        resp = requests.get(f"{API_URL}/ref/booking/{quote(b)}", timeout=15)

        if resp.status_code != 200:
            st.session_state["ref_found"] = False
            st.session_state["dam_ref"] = ""
            st.session_state["o_beta_ref"] = ""
            st.session_state["awb_ref"] = ""
            st.session_state["last_autofill_ok"] = False
            st.warning(f"No encontré referencias para ese BOOKING (HTTP {resp.status_code}).")
            return

        data = resp.json()
        st.session_state["ref_found"] = True

        o_beta = (data.get("o_beta") or "").strip()
        awb = (data.get("awb") or "").strip()
        dam = (data.get("dam") or "").strip()

        st.session_state["o_beta_ref"] = o_beta
        st.session_state["awb_ref"] = awb
        st.session_state["dam_ref"] = dam

        # Rellenar campos visibles (sin pisar si ya tienen valor manual)
        if not st.session_state["o_beta"].strip() and o_beta:
            st.session_state["o_beta"] = o_beta
        if not st.session_state["awb"].strip() and awb:
            st.session_state["awb"] = awb

        st.session_state["last_autofill_ok"] = True

    except Exception as e:
        st.session_state["last_autofill_ok"] = False
        st.error(f"Error autocompletando: {e}")


def agregar_ps_beta():
    v = normalizar_txt(st.session_state["nuevo_ps"])
    if not v:
        return

    actuales = [p for p in (st.session_state["ps_beta"] or "").split("/") if p.strip()]
    if v in actuales:
        st.session_state["nuevo_ps"] = ""
        st.warning("Ese PS BETA ya está agregado.")
        return
    if len(actuales) >= 4:
        st.warning("PS BETA máximo 4 (según operación).")
        return

    st.session_state["ps_beta"] = join_slash(st.session_state["ps_beta"], v)
    st.session_state["nuevo_ps"] = ""
    st.rerun()


def agregar_termografo():
    v = normalizar_txt(st.session_state["nuevo_tg"])
    if not v:
        return
    st.session_state["termografos"] = join_slash(st.session_state["termografos"], v)
    st.session_state["nuevo_tg"] = ""
    st.rerun()


def ocr_enviar_bytes(tipo: str, contenido: bytes, filename: str, mime: str):
    files = {"archivo": (filename, contenido, mime)}
    return requests.post(
        f"{API_URL}/ocr/extraer",
        params={"tipo": tipo},
        files=files,
        timeout=90
    )


def ocr_desde_clipboard(tipo: str):
    clip = ImageGrab.grabclipboard()
    if not isinstance(clip, Image.Image):
        st.warning("No se detectó imagen en el portapapeles. Usa Win+Shift+S y vuelve a intentar.")
        return None

    buf = BytesIO()
    clip.save(buf, format="PNG")
    contenido = buf.getvalue()
    return ocr_enviar_bytes(tipo, contenido, "clipboard.png", "image/png")


def guardar_resultado_ocr(tipo: str, data: dict):
    st.session_state.ocr_tipo = tipo
    st.session_state.ocr_mejor = data.get("mejor_valor")
    st.session_state.ocr_candidatos = data.get("valores_detectados", []) or []
    st.session_state.ocr_texto = data.get("texto", "") or ""


def fetch_y_apilar_sap(registro_id: int):
    try:
        r = requests.get(f"{API_URL}/registros/{registro_id}/sap", timeout=15)
        if r.status_code != 200:
            st.error(f"No se pudo obtener SAP-ready: {r.status_code} - {r.text}")
            return
        fila = r.json()
        fila = {"REGISTRO_ID": str(registro_id), **fila}
        st.session_state.sap_rows.append(fila)
        st.success("Fila SAP-ready agregada a la bandeja.")
    except Exception as e:
        st.error(f"Error obteniendo SAP-ready: {e}")


def cerrar_registro_backend(registro_id: int):
    try:
        r = requests.post(f"{API_URL}/registros/{registro_id}/cerrar", timeout=15)
        if r.status_code != 200:
            st.error(f"No se pudo cerrar: {r.status_code} - {r.text}")
            return
        st.session_state.registro_estado[str(registro_id)] = "cerrado"
        st.success(f"Registro {registro_id} cerrado. AWB liberado.")
    except Exception as e:
        st.error(f"Error cerrando registro: {e}")


# -------------------------
# Semáforo (completitud)
# -------------------------
def evaluar_semaforo():
    faltantes_criticos = []
    faltantes_recomendados = []
    avisos = []

    booking = normalizar_txt(st.session_state["booking"])
    dni = (st.session_state["dni"] or "").strip()
    placas = (st.session_state["placas"] or "").strip()

    ruc = (st.session_state["ruc"] or "").strip()
    codigo_sap = (st.session_state["codigo_sap"] or "").strip()

    ps_beta = (st.session_state["ps_beta"] or "").strip()
    termografos = (st.session_state["termografos"] or "").strip()
    ps_aduana = (st.session_state["ps_aduana"] or "").strip()
    ps_operador = (st.session_state["ps_operador"] or "").strip()

    o_beta = (st.session_state["o_beta"] or "").strip()
    awb = (st.session_state["awb"] or "").strip()
    dam_ref = (st.session_state.get("dam_ref") or "").strip()

    # Críticos (bloquean)
    if not booking:
        faltantes_criticos.append("BOOKING")
    if not dni:
        faltantes_criticos.append("DNI")
    if not placas:
        faltantes_criticos.append("PLACAS")
    if not (ruc or codigo_sap):
        faltantes_criticos.append("RUC o CÓDIGO SAP")
    if not ps_beta:
        faltantes_criticos.append("PS BETA")
    if not termografos:
        faltantes_criticos.append("TERMÓGRAFOS")
    if not ps_aduana:
        faltantes_criticos.append("PS ADUANA")
    if not ps_operador:
        faltantes_criticos.append("PS OPERADOR")

    # Recomendados (no bloquean)
    if not awb:
        faltantes_recomendados.append("AWB (si no viene en refs, usar OCR)")
    if not o_beta:
        faltantes_recomendados.append("O/BETA (si no viene en refs)")

    if booking and not st.session_state.get("ref_found", False):
        avisos.append("No se encontró BOOKING en referencias. Puedes crear igual, pero revisa con Autocompletar.")
    if booking and not dam_ref:
        avisos.append("DAM no encontrada aún para ese BOOKING (si la encargada aún no lo cargó, es normal).")

    if faltantes_criticos:
        return "rojo", faltantes_criticos, faltantes_recomendados, avisos
    if faltantes_recomendados or avisos:
        return "amarillo", faltantes_criticos, faltantes_recomendados, avisos
    return "verde", faltantes_criticos, faltantes_recomendados, avisos


def render_semaforo():
    nivel, crit, rec, avisos = evaluar_semaforo()

    if nivel == "rojo":
        emoji = "🔴"
        titulo = "Bloqueado: faltan datos críticos"
        color = "#ffdddd"
        borde = "#ff4d4d"
    elif nivel == "amarillo":
        emoji = "🟡"
        titulo = "Casi listo: faltan recomendados / avisos"
        color = "#fff6d6"
        borde = "#ffcc00"
    else:
        emoji = "🟢"
        titulo = "Listo para crear"
        color = "#ddffdd"
        borde = "#3cb371"

    st.markdown(
        f"""
        <div style="
            padding: 12px 14px;
            border: 2px solid {borde};
            border-radius: 12px;
            background: {color};
            margin-bottom: 12px;
        ">
            <div style="font-size: 18px; font-weight: 700;">
                {emoji} Semáforo · {titulo}
            </div>
            <div style="margin-top: 6px; font-size: 14px;">
                <b>Críticos:</b> {("✅ Ninguno" if not crit else "❌ " + ", ".join(crit))}<br/>
                <b>Recomendados:</b> {("✅ Ninguno" if not rec else "⚠️ " + ", ".join(rec))}
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if avisos:
        with st.expander("ℹ️ Avisos"):
            for a in avisos:
                st.write(f"• {a}")

    return nivel


# -------------------------
# UI
# -------------------------
tab_captura, tab_salida = st.tabs(["📝 Captura", "📤 Salida SAP (Bandeja)"])

with tab_captura:
    nivel_semaforo = render_semaforo()

    st.subheader("🧾 Datos del embarque (BOOKING → O/BETA / AWB / DAM)")

    a1, a2, a3, a4 = st.columns([2, 2, 2, 2])
    with a1:
        st.text_input("BOOKING", key="booking")
    with a2:
        st.button("🔄 Autocompletar por BOOKING", on_click=autocompletar_por_booking, use_container_width=True)
    with a3:
        st.button("🧼 Limpiar refs", on_click=limpiar_referencias, use_container_width=True)
    with a4:
        st.caption("Fuente: Power Automate → Postgres (refs)")

    # Panel de resultado del autocompletado (VISIBLE aquí mismo)
    if st.session_state.get("last_autofill_ok") is True:
        st.success("✅ Autocompletado aplicado desde referencias.")
    elif st.session_state.get("last_autofill_ok") is False:
        st.error("❌ No se pudo autocompletar (revisa BOOKING / API / refs).")

    m1, m2, m3, m4 = st.columns([1, 1, 1, 1])
    with m1:
        st.metric("Refs", "✅" if st.session_state.get("ref_found") else "—")
    with m2:
        st.metric("O/BETA (ref)", st.session_state.get("o_beta_ref") or "—")
    with m3:
        st.metric("AWB (ref)", st.session_state.get("awb_ref") or "—")
    with m4:
        st.metric("DAM (ref)", st.session_state.get("dam_ref") or "—")

    o_beta_disabled = bool(st.session_state["ref_found"] and st.session_state["o_beta_ref"])
    st.text_input("O/BETA", key="o_beta", disabled=o_beta_disabled)
    st.text_input("AWB (Contenedor)", key="awb")
    st.text_input("DAM (solo lectura)", value=st.session_state.get("dam_ref", ""), disabled=True)

    st.divider()

    st.subheader("📸 Captura asistida (OCR: BOOKING / AWB)")
    c1, c2 = st.columns([1, 2])
    with c1:
        tipo_ocr = st.selectbox("Dato a extraer", ["BOOKING", "AWB"], key="tipo_ocr_select")
    with c2:
        archivo = st.file_uploader("Sube imagen/PDF (opcional)", type=["png", "jpg", "jpeg", "pdf"], key="archivo_ocr")

    cx, cy, cz = st.columns([1, 1, 3])
    with cx:
        btn_clip = st.button("📋 Leer recorte (Win+Shift+S)", use_container_width=True)
    with cy:
        btn_file = st.button("✨ OCR (archivo)", use_container_width=True)
    with cz:
        st.caption("Recorta SOLO el dato con Win+Shift+S y usa “Leer recorte”.")

    if btn_clip:
        resp = ocr_desde_clipboard(tipo_ocr)
        if resp is not None:
            if resp.status_code != 200:
                st.error(f"OCR falló: {resp.status_code} - {resp.text}")
            else:
                guardar_resultado_ocr(tipo_ocr, resp.json())
                st.success("OCR completado desde portapapeles ✅")

    if btn_file:
        if not archivo:
            st.warning("Sube una imagen o PDF primero.")
        else:
            try:
                files = {"archivo": (archivo.name, archivo.getvalue(), archivo.type)}
                resp = requests.post(
                    f"{API_URL}/ocr/extraer",
                    params={"tipo": tipo_ocr},
                    files=files,
                    timeout=90
                )
                if resp.status_code != 200:
                    st.error(f"OCR falló: {resp.status_code} - {resp.text}")
                else:
                    guardar_resultado_ocr(tipo_ocr, resp.json())
                    st.success("OCR completado ✅")
            except Exception as e:
                st.error(f"No se pudo ejecutar OCR: {e}")

    if st.session_state.ocr_tipo:
        st.info("OCR listo")
        st.write("**Tipo:**", st.session_state.ocr_tipo)
        st.write("**Mejor valor detectado:**", st.session_state.ocr_mejor or "—")
        if st.session_state.ocr_candidatos:
            st.write("**Candidatos:**", st.session_state.ocr_candidatos)

        b1, b2, _ = st.columns([1, 1, 6])
        with b1:
            st.button("✅ Usar mejor valor en formulario", on_click=aplicar_mejor_valor_ocr)
        with b2:
            if st.button("🧹 Limpiar OCR"):
                st.session_state.ocr_tipo = None
                st.session_state.ocr_mejor = None
                st.session_state.ocr_candidatos = []
                st.session_state.ocr_texto = ""
                st.rerun()

        with st.expander("🔎 Texto OCR (debug)"):
            st.text_area("Texto OCR", st.session_state.ocr_texto, height=160)

    st.divider()

    st.subheader("🚚 Datos operativos (catálogos)")
    b1, b2, b3 = st.columns(3)
    with b1:
        st.text_input("DNI Chofer (pistola)", key="dni")
    with b2:
        st.text_input("Placas (TRACTO/CARRETA)", key="placas")
    with b3:
        st.text_input("RUC Transportista", key="ruc")

    st.text_input("Código SAP (opcional si usas RUC)", key="codigo_sap")

    st.divider()

    st.subheader("🔫 Escaneo rápido (sin escribir ‘/’)")
    s1, s2 = st.columns(2)

    with s1:
        st.text_input("Escanear PS BETA (uno por uno, máx 4)", key="nuevo_ps")
        x1, x2 = st.columns([1, 1])
        with x1:
            st.button("➕ Agregar PS BETA", on_click=agregar_ps_beta, use_container_width=True)
        with x2:
            if st.button("🧹 Limpiar PS BETA", use_container_width=True):
                st.session_state["ps_beta"] = ""
                st.session_state["nuevo_ps"] = ""
                st.rerun()
        st.text_input("PS BETA (resultado)", key="ps_beta")

    with s2:
        st.text_input("Escanear Termógrafo (uno por uno)", key="nuevo_tg")
        y1, y2 = st.columns([1, 1])
        with y1:
            st.button("➕ Agregar Termógrafo", on_click=agregar_termografo, use_container_width=True)
        with y2:
            if st.button("🧹 Limpiar Termógrafos", use_container_width=True):
                st.session_state["termografos"] = ""
                st.session_state["nuevo_tg"] = ""
                st.rerun()
        st.text_input("Termógrafos (resultado)", key="termografos")

    st.divider()

    st.subheader("🔒 Precintos / SENASA")
    p1, p2, p3 = st.columns(3)
    with p1:
        st.text_input("PS ADUANA", key="ps_aduana")
    with p2:
        st.text_input("PS OPERADOR", key="ps_operador")
    with p3:
        st.text_input("SENASA", key="senasa")

    st.text_input("PS LÍNEA", key="ps_linea")
    st.caption("SENASA/PS.LINEA se calcula en backend automáticamente.")

    st.divider()

    st.subheader("✅ Crear registro")

    def crear_registro():
        payload = {
            "o_beta": st.session_state["o_beta"] or None,
            "booking": st.session_state["booking"] or None,
            "awb": st.session_state["awb"] or None,
            "dni": st.session_state["dni"],
            "placas": st.session_state["placas"],
            "ruc": st.session_state["ruc"] or None,
            "codigo_sap": st.session_state["codigo_sap"] or None,
            "termografos": st.session_state["termografos"] or None,
            "ps_beta": st.session_state["ps_beta"] or None,
            "ps_aduana": st.session_state["ps_aduana"] or None,
            "ps_operador": st.session_state["ps_operador"] or None,
            "senasa": st.session_state["senasa"] or None,
            "ps_linea": st.session_state["ps_linea"] or None,
        }

        try:
            resp = requests.post(f"{API_URL}/registros", json=payload, timeout=25)

            if resp.status_code == 200:
                data = resp.json()
                rid = data["id"]
                st.session_state["registro_id"] = rid
                st.session_state.registro_estado[str(rid)] = "borrador"
                st.success(f"Registro creado correctamente (ID {rid})")
                fetch_y_apilar_sap(rid)

            elif resp.status_code == 409:
                error = resp.json()
                st.error("❌ Error de unicidad")
                if isinstance(error.get("detail"), dict):
                    duplicados = error["detail"].get("duplicados", [])
                    for d in duplicados:
                        st.warning(f"{d.get('tipo','')}: {d.get('valor','')}")
                else:
                    st.warning(str(error))

            else:
                st.error(f"Error {resp.status_code}: {resp.text}")

        except Exception as e:
            st.error(f"No se pudo conectar al backend: {e}")

    disabled_create = (nivel_semaforo == "rojo")
    label_btn = "🚀 Crear Registro y agregar a bandeja SAP" if not disabled_create else "🚫 Completa los críticos para crear"
    st.button(label_btn, on_click=crear_registro, use_container_width=True, disabled=disabled_create)

    if st.session_state["registro_id"]:
        rid = int(st.session_state["registro_id"])
        cA, cB, cC = st.columns([1, 1, 2])
        with cA:
            if st.button("🔄 Re-traer SAP del último", use_container_width=True):
                fetch_y_apilar_sap(rid)
        with cB:
            if st.button("🔒 Cerrar último (libera AWB)", use_container_width=True):
                cerrar_registro_backend(rid)
        with cC:
            st.caption(f"Último registro: {rid} · Estado: {st.session_state.registro_estado.get(str(rid), 'borrador')}")

with tab_salida:
    st.subheader("📤 Salida SAP (Bandeja)")

    if not st.session_state.sap_rows:
        st.info("Aún no hay filas en la bandeja. Crea un registro en la pestaña Captura.")
    else:
        df = pd.DataFrame(st.session_state.sap_rows)
        cols = ["REGISTRO_ID"] + [c for c in df.columns if c != "REGISTRO_ID"]
        df = df[cols]

        st.dataframe(df, use_container_width=True, hide_index=True, height=260)

        st.markdown("### Acciones rápidas")
        ids = [row.get("REGISTRO_ID") for row in st.session_state.sap_rows if row.get("REGISTRO_ID")]
        ids = list(dict.fromkeys(ids))

        col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
        with col1:
            sel = st.selectbox("Selecciona REGISTRO_ID", ids, key="sel_registro_id")
        with col2:
            if st.button("🔄 Traer SAP de ese registro", use_container_width=True):
                fetch_y_apilar_sap(int(sel))
        with col3:
            if st.button("🔒 Cerrar registro (libera AWB)", use_container_width=True):
                cerrar_registro_backend(int(sel))
        with col4:
            if st.button("🧹 Limpiar bandeja", use_container_width=True):
                st.session_state.sap_rows = []
                st.rerun()

        estado = st.session_state.registro_estado.get(str(sel), "borrador")
        st.caption(f"Estado guardado (UI): {estado}  ·  (El backend es la fuente real al cerrar)")
        st.caption("La bandeja es una lista de trabajo de la sesión actual. Luego la exportamos a Excel/CSV si lo deseas.")
