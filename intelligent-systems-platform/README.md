# Intelligent Systems Platform

Plataforma web modular y genérica para construir asistentes inteligentes
basados en LLMs (Gemma 4 vía OpenRouter, intercambiable). Diseñada para
que agregar un nuevo dominio (salud, educación, logística, etc.) sea
simplemente **agregar un módulo**, sin tocar el resto del sistema.

## Arquitectura

```
Streamlit (app.py + components/)
        ↓  agente.consultar(pregunta, modulo, historial, archivos)
Agent (backend/agent.py)
        ↓
Module Manager (backend/module_manager.py) ──→ Modules (modules/*.py)
        ↓                                              ↓
Prompt Manager (backend/prompt_manager.py) ←── prompts/*.txt
        ↓
LLM Adapter (backend/llm_adapter.py)
        ↓
OpenRouter → Gemma 4
```

- **La interfaz nunca conoce OpenRouter.** Solo llama a `agent.consultar(...)`.
- **Cambiar de proveedor de modelo** (Ollama, Gemini, Claude, etc.) implica
  modificar únicamente `backend/llm_adapter.py`.
- **Agregar un módulo nuevo** (dominio distinto) implica:
  1. Crear `modules/mi_modulo.py` heredando de `BaseModule`.
  2. Crear `prompts/mi_modulo.txt` con su prompt de sistema.
  3. Registrarlo en `backend/module_manager.py` (una línea).

  Nada más del sistema se toca.

## Módulos incluidos (demo, dominio salud/Paraná)

| Módulo | Qué hace |
|---|---|
| 💊 StockHunter | Busca stock de medicamentos en la red pública y sugiere la ruta de retiro. |
| ⏳ QueueMatch | Estima tiempos de espera en guardias según datos de triaje. |
| ⏰ ChronoPill AI | Arma cronogramas de medicación evitando interacciones horarias. |
| 🧾 RxAudit | Audita recetas contra el checklist de obras sociales antes de ir a la farmacia. |
| 🚑 TriageFlow Paraná | Detecta saturación de guardias y sugiere derivaciones. |

Todos usan datos **mock** (en el propio código de cada módulo) fáciles de
reemplazar por una base real (API, CSV, SQL) sin tocar el resto del sistema.

## Cómo correrlo

```bash
# 1. Crear entorno virtual (opcional pero recomendado)
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env y completar OPENROUTER_API_KEY

# 4. Correr la app
streamlit run app.py
```

## Estructura del proyecto

```
project/
├── app.py                  # Punto de entrada Streamlit
├── config.py                # Configuración centralizada (nada hardcodeado)
├── backend/
│   ├── agent.py              # Orquestador central
│   ├── llm_adapter.py         # Única clase que conoce OpenRouter
│   ├── module_manager.py       # Registro y carga de módulos
│   ├── prompt_manager.py        # Carga de prompts desde /prompts
│   ├── history.py               # Persistencia de conversaciones (JSON hoy)
│   └── utils.py                  # Utilidades sin dependencia de Streamlit
├── modules/
│   ├── base_module.py             # Contrato / clase abstracta
│   ├── stockhunter.py
│   ├── queuematch.py
│   ├── chronopill.py
│   ├── rxaudit.py
│   └── triageflow.py
├── prompts/
│   └── *.txt                        # Un prompt de sistema por módulo
├── components/
│   ├── header.py, sidebar.py, dashboard.py
│   └── chat.py, input_box.py, footer.py
├── styles/style.css
├── data/history.json                  # Se crea automáticamente
├── .env.example
└── requirements.txt
```

## Próximos pasos sugeridos

- Reemplazar `data/history.json` por SQLite/PostgreSQL (la interfaz de
  `HistoryStore` ya está pensada para eso).
- Implementar extracción real de PDF/DOCX/XLSX/imágenes en
  `backend/utils.py::extraer_texto_archivo` (hoy son puntos de extensión
  marcados con `TODO`).
- Sumar autenticación de usuarios si la plataforma se expone públicamente.
- Reemplazar los datos *mock* de cada módulo por integraciones reales
  (API de stock, sistema de triaje, etc.).
