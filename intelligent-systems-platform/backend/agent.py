"""
agent.py
--------
El Agent es el ÚNICO punto de entrada que la interfaz (Streamlit)
conoce. La UI solamente hace:

    respuesta = agente.consultar(pregunta, modulo, archivos)

El Agent:
1. Valida la entrada según las reglas del módulo activo.
2. Construye el contexto (dominio + historial + archivos) llamando
   al módulo correspondiente vía Module Manager.
3. Resuelve el prompt de sistema vía Prompt Manager.
4. Arma los mensajes en formato chat y llama al LLM Adapter.
5. Persiste el turno en el historial.
6. Devuelve ÚNICAMENTE el texto de la respuesta (o un error legible).

La interfaz nunca sabe que por debajo hay OpenRouter, Gemma, prompts
en archivos de texto, etc.
"""

from __future__ import annotations

import time
from typing import Any, Optional

from backend.llm_adapter import LLMAdapter, LLMAdapterError
from backend.module_manager import module_manager
from backend.prompt_manager import prompt_manager
from backend.history import history_store


class Agent:
    def __init__(self, llm_adapter: Optional[LLMAdapter] = None):
        self._llm = llm_adapter or LLMAdapter()
        self._ultimo_tiempo_respuesta: float = 0.0

    # ------------------------------------------------------------------
    # Punto de entrada único para la UI
    # ------------------------------------------------------------------
    def consultar(
        self,
        pregunta: str,
        modulo: str,
        historial_chat: Optional[list[dict]] = None,
        archivos: Optional[list[Any]] = None,
        conv_id: Optional[str] = None,
    ) -> dict:
        """Devuelve un dict: {"ok": bool, "respuesta": str, "error": str|None}"""

        mod = module_manager.obtener_modulo(modulo)

        es_valida, error = mod.validar_entrada(pregunta, archivos)
        if not es_valida:
            return {"ok": False, "respuesta": "", "error": error}

        contexto_dominio = mod.construir_contexto(pregunta, historial_chat, archivos)
        prompt_sistema = prompt_manager.obtener_prompt(mod.archivo_prompt)

        mensajes = self._construir_mensajes(
            prompt_sistema=prompt_sistema,
            contexto_dominio=contexto_dominio,
            historial_chat=historial_chat or [],
            pregunta=pregunta,
        )

        inicio = time.perf_counter()
        try:
            respuesta = self._llm.generar_respuesta(mensajes)
        except LLMAdapterError as exc:
            return {"ok": False, "respuesta": "", "error": str(exc)}
        finally:
            self._ultimo_tiempo_respuesta = time.perf_counter() - inicio

        if conv_id:
            history_store.guardar_turno(conv_id, pregunta, respuesta)

        return {"ok": True, "respuesta": respuesta, "error": None}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _construir_mensajes(
        self,
        prompt_sistema: str,
        contexto_dominio: str,
        historial_chat: list[dict],
        pregunta: str,
    ) -> list[dict]:
        system_content = prompt_sistema
        if contexto_dominio:
            system_content += f"\n\n--- Contexto de dominio (datos reales del sistema) ---\n{contexto_dominio}"

        mensajes = [{"role": "system", "content": system_content}]

        # Historial reciente de la conversación (para dar continuidad)
        for turno in historial_chat[-6:]:
            mensajes.append({"role": "user", "content": turno["pregunta"]})
            mensajes.append({"role": "assistant", "content": turno["respuesta"]})

        mensajes.append({"role": "user", "content": pregunta})
        return mensajes

    # ------------------------------------------------------------------
    # Info para el Dashboard
    # ------------------------------------------------------------------
    def modelo_actual(self) -> str:
        return self._llm.obtener_modelo_actual()

    def modelos_disponibles(self) -> list[str]:
        return self._llm.obtener_modelos()

    def cambiar_modelo(self, modelo: str) -> None:
        self._llm.cambiar_modelo(modelo)

    def conectado(self) -> bool:
        return self._llm.verificar_conexion()

    def ultimo_tiempo_respuesta(self) -> float:
        return self._ultimo_tiempo_respuesta


agent = Agent()
