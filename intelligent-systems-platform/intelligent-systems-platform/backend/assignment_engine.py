"""
assignment_engine.py
---------------------
Algoritmo de asignación de guardias: 100% determinístico, sin IA.
Calcula un score por guardia candidata y devuelve el ranking completo
(no solo el ganador), para que triage_agent.py pueda pasárselo a
Gemma y que el modelo valide o corrija la elección según el contexto
clínico (ver ARQUITECTURA_TRIAGE.md, sección 6, para la fórmula base).

Variables que entran en juego (en orden de aplicación):
1. Especialidad requerida  -> filtro duro (excluye, salvo que nadie la tenga).
2. Complejidad del centro  -> filtro duro solo para ROJO/NARANJA (un caso
   crítico no debería ir a un centro de baja complejidad si hay uno de
   mayor complejidad disponible con la especialidad necesaria).
3. Distancia (Haversine)   -> siempre pesa.
4. Espera / ocupación / médicos disponibles -> datos reales de
   hospital_status.json cuando existen (ver database.sincronizar_estado_hospitales),
   si no, heurística propia por cola_por_nivel.
5. Estado operativo SATURATED -> penalización dura adicional.
"""

from __future__ import annotations

import math
from typing import Optional

from backend.database import listar_guardias
from backend.models import ATENCION_PROM_MIN, NivelTriaje, ORDEN_PRIORIDAD_TRIAJE

# Pesos de la función de score (ver justificación en ARQUITECTURA_TRIAGE.md).
PESO_VIAJE = 1.0
PESO_ESPERA = 1.0
PESO_SATURACION = 2.0
PENALIZACION_ESTADO_SATURATED = 60.0  # penalización dura fija (minutos "virtuales")
UMBRAL_SATURACION_PCT = 85
VELOCIDAD_URBANA_KMH = 30

# Para casos críticos (ROJO/NARANJA), complejidad mínima exigida al centro
# (1=centro barrial, 2=hospital general, 3=alta complejidad/todas las herramientas).
COMPLEJIDAD_MINIMA_POR_NIVEL = {
    NivelTriaje.ROJO: 2,
    NivelTriaje.NARANJA: 2,
}


def _distancia_km(coord_a: tuple[float, float], coord_b: tuple[float, float]) -> float:
    """Fórmula de Haversine: distancia en km entre dos coordenadas."""
    lat1, lon1 = coord_a
    lat2, lon2 = coord_b
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.asin(math.sqrt(a))


def _espera_estimada_min(guardia: dict, nivel_paciente: NivelTriaje) -> float:
    """Devuelve la espera estimada en minutos. Prioriza el dato REAL
    (estimated_wait, sincronizado desde hospital_status.json) por sobre
    la heurística propia calculada a partir de cola_por_nivel."""
    if guardia.get("estimated_wait") is not None:
        return float(guardia["estimated_wait"])

    # Fallback: heurística propia (para guardias sin dato real sincronizado).
    cola = guardia["cola_por_nivel"]
    medicos = max(guardia.get("available_doctors") or guardia["especialidades"].get("clinica", 1), 1)
    idx_paciente = ORDEN_PRIORIDAD_TRIAJE.index(nivel_paciente)

    minutos = 0.0
    for nivel in ORDEN_PRIORIDAD_TRIAJE:
        idx_nivel = ORDEN_PRIORIDAD_TRIAJE.index(nivel)
        cantidad = cola.get(nivel.value, 0)
        atencion = ATENCION_PROM_MIN[nivel]
        if idx_nivel < idx_paciente:
            minutos += cantidad * atencion
        elif idx_nivel == idx_paciente:
            minutos += (cantidad * 0.5) * atencion
    return round(minutos / medicos, 1)


def _penalizacion_saturacion(guardia: dict) -> float:
    """Combina dos señales: la ocupación porcentual (crece de forma no
    lineal por encima del umbral) y el estado operativo explícito
    ('SATURATED' en hospital_status.json), que suma una penalización
    dura adicional aunque el % de ocupación todavía no sea extremo."""
    ocupacion_pct = guardia["ocupacion_pct"]
    penalizacion = 0.0
    if ocupacion_pct >= UMBRAL_SATURACION_PCT:
        penalizacion += (ocupacion_pct - UMBRAL_SATURACION_PCT) ** 1.5
    if guardia.get("estado_operativo") == "SATURATED":
        penalizacion += PENALIZACION_ESTADO_SATURATED
    return penalizacion


def calcular_ranking(
    ubicacion_paciente: tuple[float, float],
    nivel_triaje: NivelTriaje,
    especialidad_requerida: Optional[str] = None,
) -> list[dict]:
    """Devuelve el ranking de guardias candidatas, de mejor a peor
    opción.

    Filtros duros aplicados en orden:
    1. Especialidad requerida (si ninguna la tiene, no se excluye a
       nadie, para que Gemma pueda avisar que no hay cobertura).
    2. Complejidad mínima para ROJO/NARANJA (si ninguna la cumple,
       tampoco se excluye a nadie: es preferible una opción imperfecta
       a ninguna opción).
    """
    guardias = listar_guardias()
    candidatas = guardias

    if especialidad_requerida:
        con_especialidad = [g for g in candidatas if g["especialidades"].get(especialidad_requerida, 0) > 0]
        if con_especialidad:
            candidatas = con_especialidad

    complejidad_minima = COMPLEJIDAD_MINIMA_POR_NIVEL.get(nivel_triaje)
    if complejidad_minima is not None:
        con_complejidad = [g for g in candidatas if g["nivel_complejidad"] >= complejidad_minima]
        if con_complejidad:
            candidatas = con_complejidad

    ranking = []
    for g in candidatas:
        distancia = _distancia_km(ubicacion_paciente, (g["lat"], g["lon"]))
        minutos_viaje = (distancia / VELOCIDAD_URBANA_KMH) * 60
        espera = _espera_estimada_min(g, nivel_triaje)
        penalizacion = _penalizacion_saturacion(g)

        score = (
            PESO_VIAJE * minutos_viaje
            + PESO_ESPERA * espera
            + PESO_SATURACION * penalizacion
        )

        medicos_nombres = g.get("medicos_nombres") or []
        # Cantidad: si hay nombres cargados (dato del .txt), se usa esa
        # cantidad; si no, se cae al número real de hospital_status.json.
        medicos_cantidad = len(medicos_nombres) if medicos_nombres else g.get("available_doctors")

        ranking.append({
            "guardia_id": g["id"],
            "nombre": g["nombre"],
            "direccion": g["direccion"],
            "lat": g["lat"],
            "lon": g["lon"],
            "distancia_km": round(distancia, 1),
            "minutos_viaje": round(minutos_viaje, 0),
            "espera_estimada_min": espera,
            "ocupacion_pct": g["ocupacion_pct"],
            "estado_operativo": g.get("estado_operativo", "AVAILABLE"),
            "medicos_disponibles_cantidad": medicos_cantidad,
            "medicos_disponibles_nombres": medicos_nombres,
            "nivel_complejidad": g["nivel_complejidad"],
            "tiene_especialidad": (
                especialidad_requerida is None
                or g["especialidades"].get(especialidad_requerida, 0) > 0
            ),
            "cumple_complejidad_minima": (
                complejidad_minima is None or g["nivel_complejidad"] >= complejidad_minima
            ),
            "score_total_min": round(score, 1),
        })

    ranking.sort(key=lambda c: c["score_total_min"])
    return ranking
