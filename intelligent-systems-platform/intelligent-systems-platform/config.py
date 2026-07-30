"""
config.py
---------
Configuración centralizada de la plataforma.
Nada debe estar hardcodeado en el resto del código: todo valor
configurable (API keys, modelo, parámetros del LLM, rutas, etc.)
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
    PROVIDER: str = os.getenv("LLM_PROVIDER", "openrouter")
    OPENROUTER_BASE_URL: str = os.getenv(
        "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
    )
    OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")
    DEFAULT_MODEL: str = os.getenv(
        "DEFAULT_MODEL", "google/gemma-4-26b-a4b-it:free"
    )

    # Modelos disponibles para mostrar/seleccionar en la UI.
    # Se puede ampliar sin tocar el resto del sistema.
    AVAILABLE_MODELS: list[str] = [
        "google/gemma-4-26b-a4b-it:free",
        "google/gemma-2-27b-it:free",
        "meta-llama/llama-3.1-8b-instruct:free",
    ]

    # --- Parámetros de generación ---
    TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.4"))
    MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))
    REQUEST_TIMEOUT: int = int(os.getenv("LLM_TIMEOUT", "60"))

    # --- Plataforma ---
    PLATFORM_NAME: str = os.getenv("PLATFORM_NAME", "Intelligent Systems Platform")
    DEFAULT_MODULE: str = os.getenv("DEFAULT_MODULE", "stockhunter")

    # --- Rutas ---
    BASE_DIR: str = os.path.dirname(os.path.abspath(__file__))
    PROMPTS_DIR: str = os.path.join(BASE_DIR, "prompts")
    HISTORY_DIR: str = os.path.join(BASE_DIR, "data")
    HISTORY_FILE: str = os.path.join(HISTORY_DIR, "history.json")
    STYLE_CSS: str = os.path.join(BASE_DIR, "styles", "style.css")
    ASSETS_DIR: str = os.path.join(BASE_DIR, "assets")

    # --- Archivos soportados (preparado, no todos implementados aún) ---
    SUPPORTED_FILE_TYPES: list[str] = [
        "pdf", "csv", "xlsx", "xls", "docx", "txt", "json",
        "png", "jpg", "jpeg",
    ]


config = Config()
