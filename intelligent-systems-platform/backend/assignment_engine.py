"""
assignment_engine.py
---------------------
Algoritmo de asignación de guardias: 100% determinístico, sin IA.
Calcula un score por guardia candidata y devuelve el ranking completo
(no solo el ganador), para que triage_agent.py pueda pasárselo a
Gemma y que el modelo valide o corrija la elección según el contexto
clínico (ver ARQUITECTURA_TRIAGE.md, sección 6, para la fórmula y los
pesos elegidos).
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
UMBRAL_SATURACION_PCT = 85
VELOCIDAD_URBANA_KMH = 30


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
    """Heurística: minutos hasta ser atendido según cuántos pacientes
    más urgentes hay delante, repartido entre el personal de clínica
    general disponible (proxy de capacidad general del centro)."""
    cola = guardia["cola_por_nivel"]
    medicos = max(guardia["especialidades"].get("clinica", 1), 1)
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


def _penalizacion_saturacion(ocupacion_pct: int) -> float:
    """Crece de forma no lineal por encima del umbral, para evitar
    mandar más gente a un centro ya colapsado aunque esté cerca."""
    if ocupacion_pct < UMBRAL_SATURACION_PCT:
        return 0.0
    exceso = ocupacion_pct - UMBRAL_SATURACION_PCT
    return (exceso ** 1.5)  # crecimiento no lineal


def calcular_ranking(
    ubicacion_paciente: tuple[float, float],
    nivel_triaje: NivelTriaje,
    especialidad_requerida: Optional[str] = None,
) -> list[dict]:
    """Devuelve el ranking de guardias candidatas, de mejor a peor
    opción. Las guardias que no tienen la especialidad requerida se
    EXCLUYEN del ranking (restricción dura, no un costo más).

    Excepción: si nivel_triaje es ROJO, se ignora la restricción de
    saturación/score y se prioriza directamente la guardia más cercana
    con capacidad de emergencia (regla dura de seguridad clínica).
    """
    guardias = listar_guardias()

    if especialidad_requerida:
        candidatas = [g for g in guardias if g["especialidades"].get(especialidad_requerida, 0) > 0]
        if not candidatas:
            # Ninguna guardia tiene la especialidad: se devuelve igual
            # el ranking completo (sin excluir), marcado explícitamente,
            # para que Gemma pueda avisarle al paciente que no hay
            # cobertura y sugerir la alternativa menos mala.
            candidatas = guardias
    else:
        candidatas = guardias

    ranking = []
    for g in candidatas:
        distancia = _distancia_km(ubicacion_paciente, (g["lat"], g["lon"]))
        minutos_viaje = (distancia / VELOCIDAD_URBANA_KMH) * 60
        espera = _espera_estimada_min(g, nivel_triaje)
        penalizacion = _penalizacion_saturacion(g["ocupacion_pct"])

        if nivel_triaje == NivelTriaje.ROJO:
            # Emergencia real: el score se basa solo en cercanía.
            score = minutos_viaje
        else:
            score = (
                PESO_VIAJE * minutos_viaje
                + PESO_ESPERA * espera
                + PESO_SATURACION * penalizacion
            )

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
            "tiene_especialidad": (
                especialidad_requerida is None
                or g["especialidades"].get(especialidad_requerida, 0) > 0
            ),
            "score_total_min": round(score, 1),
        })

    ranking.sort(key=lambda c: c["score_total_min"])
    return ranking
