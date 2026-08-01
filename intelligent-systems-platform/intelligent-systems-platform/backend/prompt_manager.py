"""
prompt_manager.py
-----------------
Responsable únicamente de leer los prompts de sistema desde disco
(carpeta /prompts). Los prompts NUNCA viven hardcodeados en el código
de los módulos: cada módulo referencia el nombre de su archivo .txt
y este manager lo resuelve y cachea.
"""

from __future__ import annotations

import os
from functools import lru_cache

from config import config


class PromptManager:
    def __init__(self, prompts_dir: str | None = None):
        self._prompts_dir = prompts_dir or config.PROMPTS_DIR

    @lru_cache(maxsize=None)
    def _leer_archivo(self, nombre_archivo: str) -> str:
        ruta = os.path.join(self._prompts_dir, nombre_archivo)
        if not os.path.exists(ruta):
            raise FileNotFoundError(
                f"No se encontró el prompt '{nombre_archivo}' en {self._prompts_dir}"
            )
        with open(ruta, "r", encoding="utf-8") as f:
            return f.read().strip()

    def obtener_prompt(self, nombre_archivo: str) -> str:
        """Devuelve el contenido del prompt de sistema de un módulo."""
        return self._leer_archivo(nombre_archivo)


prompt_manager = PromptManager()
