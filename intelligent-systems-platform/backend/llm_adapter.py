"""
llm_adapter.py
--------------
Única clase de todo el sistema que sabe cómo hablar con un proveedor
de LLM concreto (hoy Ollama local / Gemma 4 E4B).

Ollama expone un endpoint HTTP compatible con la API de chat de
OpenAI (http://localhost:11434/v1), así que reutilizamos el SDK
`openai` apuntándolo a ese endpoint en vez de a la nube. Si el día de
mañana se cambia Ollama por OpenRouter, la API de Gemini o la de
Claude, ÚNICAMENTE este archivo (y config.py) deben modificarse. El
resto de la plataforma (Agent, Module Manager, UI) no debe enterarse
nunca del cambio.
"""

from __future__ import annotations

from typing import Optional
from openai import OpenAI

from config import config


class LLMAdapter:
    """Encapsula toda la comunicación con el proveedor de modelos."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        self._api_key = api_key or config.LLM_API_KEY
        self._base_url = base_url or config.LLM_BASE_URL
        self._model = model or config.DEFAULT_MODEL
        self._temperature = config.TEMPERATURE
        self._max_tokens = config.MAX_TOKENS

        self._client = OpenAI(base_url=self._base_url, api_key=self._api_key)

    # ------------------------------------------------------------------
    # Configuración en caliente
    # ------------------------------------------------------------------
    def cambiar_modelo(self, modelo: str) -> None:
        """Cambia el modelo activo sin recrear el cliente."""
        self._model = modelo

    def configurar_temperatura(self, temperatura: float) -> None:
        self._temperature = max(0.0, min(2.0, temperatura))

    def configurar_max_tokens(self, max_tokens: int) -> None:
        self._max_tokens = max_tokens

    def obtener_modelos(self) -> list[str]:
        """Devuelve la lista de modelos disponibles configurados.

        (Ollama expone también un endpoint /api/tags con los modelos
        realmente descargados en la máquina; se puede reemplazar esta
        implementación estática por una consulta real sin afectar al
        resto del sistema).
        """
        return config.AVAILABLE_MODELS

    def obtener_modelo_actual(self) -> str:
        return self._model

    # ------------------------------------------------------------------
    # Generación
    # ------------------------------------------------------------------
    def generar_respuesta(
        self,
        mensajes: list[dict],
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Envía una lista de mensajes (formato OpenAI chat) al modelo
        y devuelve únicamente el texto de la respuesta.
        """
        try:
            respuesta = self._client.chat.completions.create(
                model=self._model,
                messages=mensajes,
                temperature=temperatura if temperatura is not None else self._temperature,
                max_tokens=max_tokens if max_tokens is not None else self._max_tokens,
            )
            return respuesta.choices[0].message.content or ""
        except Exception as exc:  # noqa: BLE001
            # El adaptador nunca deja propagar excepciones "crudas" del
            # SDK hacia el resto del sistema: las traduce a un mensaje
            # entendible. El Agent decide qué hacer con el error.
            raise LLMAdapterError(f"Error al comunicarse con el proveedor: {exc}") from exc

    def generar_con_herramientas(
        self,
        mensajes: list[dict],
        herramientas: list[dict],
        tool_choice: str = "auto",
        temperatura: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ):
        """Igual que generar_respuesta, pero habilitando function calling
        (formato OpenAI 'tools'). Devuelve el objeto `message` completo
        del SDK (no solo el texto), porque el llamador necesita poder
        inspeccionar `.tool_calls` para saber si el modelo decidió
        invocar una función en vez de responder en texto libre.
        """
        try:
            respuesta = self._client.chat.completions.create(
                model=self._model,
                messages=mensajes,
                tools=herramientas,
                tool_choice=tool_choice,
                temperature=temperatura if temperatura is not None else self._temperature,
                max_tokens=max_tokens if max_tokens is not None else self._max_tokens,
            )
            return respuesta.choices[0].message
        except Exception as exc:  # noqa: BLE001
            raise LLMAdapterError(f"Error al comunicarse con el proveedor (tools): {exc}") from exc

    def verificar_conexion(self) -> bool:
        """Chequeo liviano de que el servidor de Ollama está arriba.

        Con un proveedor local no tiene sentido chequear una api_key
        (siempre hay una, aunque sea el valor dummy "ollama"): lo que
        puede fallar es que `ollama serve` no esté corriendo. Golpea
        el endpoint /api/tags (liviano, no genera tokens) con timeout
        corto para no trabar la UI si el servicio está caído.
        """
        import requests

        try:
            base_sin_v1 = self._base_url.rstrip("/").removesuffix("/v1")
            resp = requests.get(f"{base_sin_v1}/api/tags", timeout=2)
            return resp.ok
        except Exception:
            return False


class LLMAdapterError(Exception):
    """Error de comunicación con el proveedor de LLM."""
