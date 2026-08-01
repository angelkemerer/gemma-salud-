"""
config.py
---------
Configuración centralizada de la plataforma.
Nada debe estar hardcodeado en el resto del código: todo valor
configurable (endpoint del LLM, modelo, parámetros, rutas, etc.)
vive aquí y se lee preferentemente desde variables de entorno.

Para usar variables de entorno desde un archivo .env, instalar
python-dotenv (ya incluido en requirements.txt) y crear un archivo
.env en la raíz del proyecto (ver .env.example).
"""

import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv es opcional: si no está instalado, se usan las
    # variables de entorno del sistema tal cual.
    pass


class Config:
    # --- Proveedor / Modelo ---
    # Por defecto corre 100% local contra Ollama (sin API key, sin
    # costo, sin depender de internet en la demo). Ollama expone un
    # endpoint compatible con la API de OpenAI en /v1, por eso el
    # resto del código (LLMAdapter) no cambia una línea.
    PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama")
    LLM_BASE_URL: str = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1")
    # Ollama ignora la api_key, pero el cliente OpenAI exige un string
    # no vacío. "ollama" es el valor convencional para eso.
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "ollama")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gemma4:e4b")

    # Modelos disponibles para mostrar/seleccionar en la UI.
    # Deben estar descargados localmente (`ollama pull <modelo>`).
    AVAILABLE_MODELS: list[str] = [
        "gemma4:e4b",
        "gemma4:e2b",
        "gemma3n:e4b",
    ]

    # --- Parámetros de generación ---
    TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    REQUEST_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

    # --- Plataforma ---
    PLATFORM_NAME: str = os.getenv("PLATFORM_NAME", "TriageFlow Paraná")

    # --- Rutas ---
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    PROMPTS_DIR: str = os.path.join(BASE_DIR, "prompts")
    HISTORY_DIR: str = os.path.join(BASE_DIR, "data")


config = Config()
