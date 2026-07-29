"""
history.py
----------
Persistencia del historial de conversaciones.

Implementación actual: archivo JSON en disco (simple y suficiente
para el hackathon). La interfaz pública (guardar_turno / listar /
obtener_conversacion) es la que debe respetar cualquier backend
futuro (SQLite, PostgreSQL, etc.) para que el resto del sistema no
note el cambio.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime
from typing import Optional

from config import config


class HistoryStore:
    def __init__(self, history_file: str | None = None):
        self._history_file = history_file or config.HISTORY_FILE
        os.makedirs(os.path.dirname(self._history_file), exist_ok=True)
        if not os.path.exists(self._history_file):
            self._escribir([])

    # ------------------------------------------------------------------
    # I/O interno
    # ------------------------------------------------------------------
    def _leer(self) -> list[dict]:
        with open(self._history_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def _escribir(self, data: list[dict]) -> None:
        with open(self._history_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # ------------------------------------------------------------------
    # API pública
    # ------------------------------------------------------------------
    def nueva_conversacion(self, modulo: str, modelo: str) -> str:
        conversaciones = self._leer()
        conv_id = str(uuid.uuid4())
        conversaciones.append({
            "id": conv_id,
            "fecha": datetime.now().strftime("%Y-%m-%d"),
            "hora": datetime.now().strftime("%H:%M:%S"),
            "modulo": modulo,
            "modelo": modelo,
            "turnos": [],
        })
        self._escribir(conversaciones)
        return conv_id

    def guardar_turno(self, conv_id: str, pregunta: str, respuesta: str) -> None:
        conversaciones = self._leer()
        for conv in conversaciones:
            if conv["id"] == conv_id:
                conv["turnos"].append({
                    "hora": datetime.now().strftime("%H:%M:%S"),
                    "pregunta": pregunta,
                    "respuesta": respuesta,
                })
                break
        self._escribir(conversaciones)

    def listar_conversaciones(self) -> list[dict]:
        return self._leer()

    def obtener_conversacion(self, conv_id: str) -> Optional[dict]:
        for conv in self._leer():
            if conv["id"] == conv_id:
                return conv
        return None

    def contar_conversaciones(self) -> int:
        return len(self._leer())

    def borrar_todo(self) -> None:
        self._escribir([])


history_store = HistoryStore()
