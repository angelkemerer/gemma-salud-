"""
module_manager.py
------------------
Responsable de registrar y entregar instancias de módulos.

Agregar un módulo nuevo:
1. Crear modules/mi_modulo.py con una clase que herede de BaseModule.
2. Crear prompts/mi_modulo.txt con su prompt de sistema.
3. Agregar la clase al diccionario _REGISTRO de abajo.

Nada más del sistema (Agent, UI, etc.) necesita modificarse.
"""

from __future__ import annotations

from modules.base_module import BaseModule
from modules.stockhunter import StockHunterModule
from modules.queuematch import QueueMatchModule
from modules.chronopill import ChronoPillModule
from modules.rxaudit import RxAuditModule
from modules.triageflow import TriageFlowModule

_REGISTRO: dict[str, type[BaseModule]] = {
    "stockhunter": StockHunterModule,
    "queuematch": QueueMatchModule,
    "chronopill": ChronoPillModule,
    "rxaudit": RxAuditModule,
    "triageflow": TriageFlowModule,
}


class ModuleManager:
    def __init__(self):
        # Se instancian una sola vez y se reutilizan (los módulos son
        # stateless respecto de la conversación: el estado vive en el
        # historial, no en la instancia).
        self._instancias: dict[str, BaseModule] = {
            nombre: cls() for nombre, cls in _REGISTRO.items()
        }

    def listar_modulos(self) -> list[BaseModule]:
        return list(self._instancias.values())

    def obtener_modulo(self, nombre: str) -> BaseModule:
        if nombre not in self._instancias:
            raise ValueError(f"Módulo '{nombre}' no está registrado.")
        return self._instancias[nombre]

    def registrar_modulo(self, nombre: str, instancia: BaseModule) -> None:
        """Permite registrar módulos en runtime (por ejemplo, cargados
        dinámicamente desde un plugin externo)."""
        self._instancias[nombre] = instancia


module_manager = ModuleManager()
