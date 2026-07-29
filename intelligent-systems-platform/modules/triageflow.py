"""
triageflow.py
-------------
Módulo: balanceador de demanda en la red sanitaria de Paraná.
Sugiere derivaciones cuando una guardia está saturada y hay
capacidad ociosa en otros centros.
"""

from __future__ import annotations

from typing import Any, Optional

from modules.base_module import BaseModule

# Mock de capacidad/ocupación por centro (reemplazable por datos reales).
RED_SANITARIA = [
    {"centro": "Guardia Hospital San Martín", "ocupacion_pct": 92, "espera_min": 140},
    {"centro": "Centro de Salud barrial (zona norte)", "ocupacion_pct": 30, "espera_min": 15},
    {"centro": "Hospital de San Benito", "ocupacion_pct": 45, "espera_min": 25},
]

UMBRAL_SATURACION_PCT = 85


class TriageFlowModule(BaseModule):
    nombre = "triageflow"
    nombre_visible = "TriageFlow Paraná"
    descripcion = "Detecta saturación en guardias y sugiere derivaciones a centros con capacidad disponible."
    archivo_prompt = "triageflow.txt"
    icono = "🚑"
    acepta_archivos = []

    def herramientas(self) -> list[str]:
        return ["Monitoreo de ocupación por centro", "Sugerencia de derivación automática"]

    def construir_contexto(
        self,
        pregunta: str,
        historial: Optional[list[dict]] = None,
        archivos: Optional[list[Any]] = None,
    ) -> str:
        saturados = [c for c in RED_SANITARIA if c["ocupacion_pct"] >= UMBRAL_SATURACION_PCT]
        disponibles = [c for c in RED_SANITARIA if c["ocupacion_pct"] < UMBRAL_SATURACION_PCT]

        estado = "\n".join(
            f"- {c['centro']}: {c['ocupacion_pct']}% de ocupación, espera estimada {c['espera_min']} min"
            for c in RED_SANITARIA
        )

        alerta = ""
        if saturados:
            nombres_saturados = ", ".join(c["centro"] for c in saturados)
            nombres_disponibles = ", ".join(c["centro"] for c in disponibles) or "ninguno con datos cargados"
            alerta = (
                f"\n\nALERTA: {nombres_saturados} supera el umbral de saturación "
                f"({UMBRAL_SATURACION_PCT}%). Centros con capacidad disponible: {nombres_disponibles}."
            )

        return f"Estado actual de la red sanitaria:\n{estado}{alerta}"
