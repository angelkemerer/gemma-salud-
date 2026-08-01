"""
base_module.py
---------------
Contrato que debe cumplir cualquier módulo especializado
(StockHunter, QueueMatch, ChronoPill, RxAudit, TriageFlow, o
cualquier módulo futuro de un dominio distinto).

Agregar un módulo nuevo = crear una clase que herede de BaseModule
y registrarla en module_manager.py. Nada más del sistema debe
modificarse.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional


class BaseModule(ABC):
    """Interfaz que deben implementar todos los módulos."""

    # Identificador único usado internamente (minúsculas, sin espacios)
    nombre: str = "base_module"

    # Nombre visible en la UI
    nombre_visible: str = "Módulo base"

    # Descripción corta para el Dashboard / selector de módulos
    descripcion: str = "Módulo base sin implementar."

    # Nombre del archivo de prompt dentro de /prompts
    archivo_prompt: str = "base.txt"

    # Ícono para mostrar en la UI (emoji, simple y liviano)
    icono: str = "🧩"

    # Tipos de archivo que este módulo sabe procesar (subconjunto de
    # config.SUPPORTED_FILE_TYPES)
    acepta_archivos: list[str] = []

    def validar_entrada(self, pregunta: str, archivos: Optional[list[Any]] = None) -> tuple[bool, str]:
        """Validación mínima común. Los módulos pueden sobreescribirla
        para agregar reglas propias (ej. exigir que se adjunte una
        receta).
        Devuelve (es_valida, mensaje_error).
        """
        if not pregunta or not pregunta.strip():
            return False, "La consulta no puede estar vacía."
        return True, ""

    @abstractmethod
    def construir_contexto(
        self,
        pregunta: str,
        historial: Optional[list[dict]] = None,
        archivos: Optional[list[Any]] = None,
    ) -> str:
        """Construye el contexto adicional (datos de dominio, resultados
        de búsquedas internas, contenido de archivos, etc.) que se
        inyecta junto al prompt de sistema antes de llamar al modelo.
        Debe devolver un string (puede ser vacío si no aplica).
        """
        raise NotImplementedError

    def herramientas(self) -> list[str]:
        """Lista descriptiva de herramientas/capacidades del módulo
        (informativo, para mostrar en el Dashboard)."""
        return []

    def to_dict(self) -> dict:
        return {
            "nombre": self.nombre,
            "nombre_visible": self.nombre_visible,
            "descripcion": self.descripcion,
            "icono": self.icono,
            "acepta_archivos": self.acepta_archivos,
            "herramientas": self.herramientas(),
        }
