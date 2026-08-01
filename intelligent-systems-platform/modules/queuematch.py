"""
queuematch.py
-------------
Módulo: estimador de tiempos de espera en guardias, a partir de datos
(simulados) de triaje en tiempo real.
"""

from __future__ import annotations

from typing import Any, Optional

from modules.base_module import BaseModule

# Mock de estado de triaje en tiempo real (reemplazable por consulta
# real al sistema hospitalario).
ESTADO_TRIAJE = {
    "Hospital San Martín": {"nivel_4": 12, "codigo_rojo": 2, "personal_disponible": 3},
    "Hospital de San Benito": {"nivel_4": 3, "codigo_rojo": 0, "personal_disponible": 2},
}


class QueueMatchModule(BaseModule):
    nombre = "queuematch"
    nombre_visible = "QueueMatch"
    descripcion = "Estima tiempos de espera realistas en guardias según el estado del triaje en tiempo real."
    archivo_prompt = "queuematch.txt"
    icono = "⏳"
    acepta_archivos = []

    def herramientas(self) -> list[str]:
        return ["Lectura de estado de triaje en tiempo real", "Estimación explicada de tiempos de espera"]

    def construir_contexto(
        self,
        pregunta: str,
        historial: Optional[list[dict]] = None,
        archivos: Optional[list[Any]] = None,
    ) -> str:
        bloques = []
        for centro, datos in ESTADO_TRIAJE.items():
            bloques.append(
                f"{centro}: {datos['nivel_4']} pacientes Nivel 4, "
                f"{datos['codigo_rojo']} código rojo en shockroom, "
                f"{datos['personal_disponible']} profesionales disponibles."
            )
        return "Estado actual de triaje:\n" + "\n".join(bloques)
