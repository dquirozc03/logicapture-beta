from __future__ import annotations
from typing import Iterable

def normalizar(valor: str | None) -> str | None:
    if valor is None:
        return None
    v = valor.strip()
    if not v:
        return None
    v = " ".join(v.split()).upper()
    return v

def dividir_por_slash(valor: str | None) -> list[str]:
    v = normalizar(valor)
    if not v:
        return []
    partes = [p.strip().upper() for p in v.split("/") if p.strip()]
    # deduplicar manteniendo orden
    vistos = set()
    salida = []
    for p in partes:
        if p not in vistos:
            vistos.add(p)
            salida.append(p)
    return salida

def unir_por_slash(valores: Iterable[str]) -> str | None:
    vals = [normalizar(v) for v in valores]
    vals = [v for v in vals if v]
    if not vals:
        return None
    return "/".join(vals)
