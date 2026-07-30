"""
geocoding.py
------------
Convierte una dirección en texto libre a coordenadas (lat, lon) reales,
usando Nominatim (OpenStreetMap): gratuito, sin API key, cumple el
requisito del reglamento de "herramientas accesibles sin costo".

Esto reemplaza al mock anterior (4 barrios fijos por palabra clave)
como fuente PRINCIPAL de "dónde está el paciente". El mock no
desaparece: queda como capa de respaldo offline (ver
_geocodificar_por_barrio_mock), para que el triaje nunca se trabe si
falla la conexión a internet justo en el momento de la demo — la
derivación es más importante que la precisión geográfica perfecta.
"""

from __future__ import annotations

from typing import Optional

import requests

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
UBICACION_DEFAULT = (-31.7333, -60.5238)  # Centro de Paraná, último fallback

# Mock offline (igual al que ya existía): funciona sin internet, se usa
# solo si el geocoding real falla o no está disponible.
BARRIOS_MOCK = {
    "centro": (-31.7333, -60.5238),
    "zona norte": (-31.7000, -60.5050),
    "san benito": (-31.7500, -60.5000),
    "microcentro": (-31.7320, -60.5260),
    "oro verde": (-31.8228, -60.5192),
}


def _geocodificar_real(texto: str) -> Optional[tuple[float, float]]:
    """Intenta geocodificar contra Nominatim. Devuelve None si falla
    por cualquier motivo (sin internet, timeout, sin resultados) — el
    llamador decide qué hacer con ese None, esta función nunca lanza
    una excepción hacia afuera."""
    query = texto.strip()
    if not any(c in query.lower() for c in ["paraná", "parana", "oro verde", "entre ríos", "entre rios"]):
        query = f"{query}, Paraná, Entre Ríos, Argentina"

    try:
        resp = requests.get(
            NOMINATIM_URL,
            params={"q": query, "format": "json", "limit": 1},
            headers={"User-Agent": "TriageFlowParana-Hackathon-UNER/1.0"},
            timeout=4,
        )
        resp.raise_for_status()
        resultados = resp.json()
        if resultados:
            return float(resultados[0]["lat"]), float(resultados[0]["lon"])
    except Exception:
        # Cualquier error de red/parseo cae al fallback. No queremos
        # que un problema de geocoding tumbe el triaje de un paciente.
        pass
    return None


def _geocodificar_por_barrio_mock(texto: str) -> Optional[tuple[float, float]]:
    texto_low = texto.lower()
    for barrio, coords in BARRIOS_MOCK.items():
        if barrio in texto_low:
            return coords
    return None


def geocodificar(texto_ubicacion: str) -> tuple[float, float]:
    """Punto de entrada único. Orden de intentos:
    1. Geocoding real (Nominatim) — dirección exacta si hay internet.
    2. Match de barrio mock — funciona offline.
    3. Centro de Paraná — último recurso, nunca deja al paciente sin
       una ubicación para poder calcular el ranking de guardias.
    """
    if not texto_ubicacion or not texto_ubicacion.strip():
        return UBICACION_DEFAULT

    real = _geocodificar_real(texto_ubicacion)
    if real is not None:
        return real

    mock = _geocodificar_por_barrio_mock(texto_ubicacion)
    if mock is not None:
        return mock

    return UBICACION_DEFAULT
