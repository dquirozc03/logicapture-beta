from fastapi import APIRouter, UploadFile, File, HTTPException, Query
from typing import Literal
import re
from io import BytesIO

from PIL import Image
import pytesseract

router = APIRouter(prefix="/api/v1/ocr", tags=["OCR"])

TipoOCR = Literal["DNI", "PS_BETA", "TERMOGRAFO", "BOOKING", "O_BETA", "AWB"]

# Si en tu PC tesseract no está en PATH, descomenta y ajusta:
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"


def ocr_imagen_pil(img: Image.Image) -> str:
    # Un poco de preproceso rápido (MVP)
    img = img.convert("L")  # escala de grises
    return pytesseract.image_to_string(img, lang="eng")  # eng suele leer mejor códigos; luego afinamos


def extraer_valores(texto: str, tipo: TipoOCR) -> list[str]:
    t = (texto or "").upper()

    if tipo == "DNI":
        # DNI Perú: 8 dígitos
        return re.findall(r"\b\d{8}\b", t)

    if tipo in ("PS_BETA",):
        # Precintos típicos: alfanumérico 6-20 (ajustable)
        # Permitimos también guiones
        vals = re.findall(r"\b[A-Z0-9\-]{6,20}\b", t)
        # Filtrar falsos positivos muy comunes (puedes ampliar)
        blacklist = {"BETA", "SENASA", "BOOKING", "AWB"}
        return [v for v in vals if v not in blacklist]

    if tipo == "TERMOGRAFO":
        # Termógrafos: suelen ser códigos alfanuméricos (ajustable)
        vals = re.findall(r"\b[A-Z0-9]{6,30}\b", t)
        return vals

    if tipo == "BOOKING":
        # Booking muchas navieras: alfanumérico 8-15
        vals = re.findall(r"\b[A-Z0-9]{8,15}\b", t)
        return vals

    if tipo == "O_BETA":
        # Orden Beta: en tu ejemplo luce como "BU2422" o similar.
        # Ajustable: 2-4 letras + 3-8 dígitos
        vals = re.findall(r"\b[A-Z]{2,4}\d{3,8}\b", t)
        return vals

    if tipo == "AWB":
        # Contenedor: a veces es estilo SEKU942505-7 o SEKU9425057
        # 4 letras + 6-7 dígitos + opcional - dígito
        vals = re.findall(r"\b[A-Z]{4}\d{6,7}(?:-\d)?\b", t)
        return vals

    return []


@router.post("/extraer")
async def extraer(
    tipo: TipoOCR = Query(...),
    archivo: UploadFile = File(...)
):
    nombre = (archivo.filename or "").lower()
    data = await archivo.read()

    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    texto = ""

    # Imagen
    if nombre.endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp")):
        img = Image.open(BytesIO(data))
        texto = ocr_imagen_pil(img)

    # PDF (MVP: primera página)
    elif nombre.endswith(".pdf"):
        try:
            from pdf2image import convert_from_bytes
        except Exception:
            raise HTTPException(status_code=500, detail="Falta instalar pdf2image o dependencias para PDF")

        try:
            paginas = convert_from_bytes(data, first_page=1, last_page=1)
            if not paginas:
                raise HTTPException(status_code=400, detail="No se pudo convertir el PDF a imagen")
            texto = ocr_imagen_pil(paginas[0])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error procesando PDF: {e}")

    else:
        raise HTTPException(status_code=415, detail="Formato no soportado. Usa imagen o PDF.")

    valores = extraer_valores(texto, tipo)
    # deduplicar manteniendo orden
    vistos = set()
    valores_unicos = []
    for v in valores:
        if v not in vistos:
            vistos.add(v)
            valores_unicos.append(v)

    return {
        "tipo": tipo,
        "texto": texto,
        "valores_detectados": valores_unicos,
        "mejor_valor": valores_unicos[0] if valores_unicos else None
    }
