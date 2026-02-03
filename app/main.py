from fastapi import FastAPI
from app.routers import choferes, vehiculos, transportistas, registros, ocr, sync, referencias

app = FastAPI(
    title="BETA LogiCapture 1.0",
    version="0.2.0",
    description="Catálogos + control de unicidad + preparación SAP."
)

app.include_router(choferes.router)
app.include_router(vehiculos.router)
app.include_router(transportistas.router)
app.include_router(registros.router)
app.include_router(ocr.router)
app.include_router(sync.router)
app.include_router(referencias.router)

@app.get("/salud")
def salud():
    return {"estado": "ok"}

@app.get("/")
def root():
    return {"status": "ok"}

