"""
chronopill.py
-------------
Módulo: optimizador de horarios para pacientes polimedicados.

Recibe la lista de medicamentos (escrita o extraída de fotos de
recetas) y arma un contexto con reglas conocidas de interacción /
incompatibilidad horaria para que el LLM genere un cronograma diario
sin cruces.
"""

from __future__ import annotations

from typing import Any, Optional

from modules.base_module import BaseModule

# Reglas simplificadas de interacción (mock, no es información médica
# validada: solo para demostrar el mecanismo del módulo).
REGLAS_INTERACCION = [
    {
        "drogas": ("calcio", "hierro"),
        "regla": "Separar por al menos 2 horas: el calcio reduce la absorción del hierro.",
    },
    {
        "drogas": ("levotiroxina", "alimento"),
        "regla": "Levotiroxina en ayunas, esperar 30-60 min antes de comer o tomar otros fármacos.",
    },
    {
        "drogas": ("levotiroxina", "calcio"),
        "regla": "No tomar junto al calcio: separar por al menos 4 horas.",
    },
]


class ChronoPillModule(BaseModule):
    nombre = "chronopill"
    nombre_visible = "ChronoPill AI"
    descripcion = "Arma un cronograma diario de medicación evitando cruces e interacciones horarias."
    archivo_prompt = "chronopill.txt"
    icono = "⏰"
    acepta_archivos = ["png", "jpg", "jpeg", "pdf", "txt"]

    def herramientas(self) -> list[str]:
        return ["Detección de interacciones conocidas", "Generación de cronograma horario"]

    def construir_contexto(
        self,
        pregunta: str,
        historial: Optional[list[dict]] = None,
        archivos: Optional[list[Any]] = None,
    ) -> str:
        pregunta_norm = pregunta.lower()
        reglas_aplicables = [
            r["regla"] for r in REGLAS_INTERACCION
            if all(droga in pregunta_norm for droga in r["drogas"])
        ]

        if not reglas_aplicables:
            return (
                "No se detectaron interacciones conocidas en la base simulada para las "
                "drogas mencionadas. Generá igualmente un cronograma equilibrado a lo "
                "largo del día, dejando aclarado que ante dudas se debe consultar al médico o farmacéutico."
            )

        return "Reglas de interacción detectadas para este caso:\n" + "\n".join(
            f"- {r}" for r in reglas_aplicables
        )
