"""
rxaudit.py
----------
Módulo: pre-auditoría de recetas para evitar rechazos en obras
sociales / farmacias (PAMI, IOSPER, etc.).
"""

from __future__ import annotations

from typing import Any, Optional

from modules.base_module import BaseModule

# Checklist simulado de requisitos frecuentes de auditoría.
REQUISITOS_AUDITORIA = [
    "Firma y sello del profesional",
    "Código de diagnóstico (CIE-10)",
    "Dosis y frecuencia claramente indicadas",
    "Nombre y DNI del paciente",
    "Fecha de emisión vigente (no mayor a 30 días)",
]


class RxAuditModule(BaseModule):
    nombre = "rxaudit"
    nombre_visible = "RxAudit"
    descripcion = "Audita recetas contra los requisitos habituales de obras sociales antes de ir a la farmacia."
    archivo_prompt = "rxaudit.txt"
    icono = "🧾"
    acepta_archivos = ["pdf", "png", "jpg", "jpeg"]

    def herramientas(self) -> list[str]:
        return ["Checklist de requisitos de auditoría", "Detección de campos faltantes"]

    def construir_contexto(
        self,
        pregunta: str,
        historial: Optional[list[dict]] = None,
        archivos: Optional[list[Any]] = None,
    ) -> str:
        checklist = "\n".join(f"- {r}" for r in REQUISITOS_AUDITORIA)
        return (
            "Checklist de requisitos habituales que exigen las obras sociales locales:\n"
            f"{checklist}\n\n"
            "Compará la receta descripta por el usuario contra este checklist y señalá "
            "puntualmente qué falta o qué está mal, sin inventar datos que no estén en la consulta."
        )
