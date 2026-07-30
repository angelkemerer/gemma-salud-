# TriageFlow Paraná

Sistema de triaje médico conversacional y derivación inteligente de
pacientes a guardias/centros de salud, construido con **Gemma 4**
para el **Hackathon Gemma 4 × UNER — IA para la Salud** (CiEV, Facultad
de Ingeniería, UNER).

Un paciente describe su motivo de consulta por chat. Gemma 4 lo
interroga (con criterio clínico, una pregunta atómica por vez),
determina el nivel de triaje y la especialidad requerida, y el sistema
calcula matemáticamente cuál es el centro de salud más adecuado según
distancia, ocupación, especialidad disponible y complejidad del
centro — Gemma valida esa recomendación y se la explica al paciente
en lenguaje claro.

## El problema que resuelve

Evitar que todos los pacientes se deriven al hospital más cercano
cuando está saturado, mientras hay centros con capacidad disponible
más lejos. Y evitar el caso inverso: que un caso crítico termine en un
centro de baja complejidad solo por estar cerca, cuando hay un
hospital de alta complejidad a poca distancia con las herramientas
necesarias.

## Cómo está armado (arquitectura)

```
Streamlit (app.py + components/)
        │
        ├── Landing: elegís Paciente o Administrador de guardia
        │
        ├── Vista Paciente (components/chat_paciente.py)
        │        │
        │        ▼
        │   TriageAgent (backend/triage_agent.py)
        │        │
        │        ├─ 1. Chat multi-turno con Gemma, vía function calling
        │        │     (backend/tools.py: función `derive_patient`)
        │        │     hasta que el modelo tiene nivel de triaje +
        │        │     especialidad + resumen clínico.
        │        │
        │        ├─ 2. Geocodifica la ubicación del paciente
        │        │     (backend/geocoding.py: Nominatim real, con
        │        │     fallback offline si no hay internet)
        │        │
        │        ├─ 3. AssignmentEngine calcula el ranking de centros
        │        │     — 100% determinístico, SIN IA
        │        │     (backend/assignment_engine.py: distancia +
        │        │     espera + ocupación + especialidad + complejidad)
        │        │
        │        ├─ 4. Gemma valida o corrige el ranking según el
        │        │     cuadro clínico (prompts/triage_validacion.txt)
        │        │
        │        └─ 5. Se persiste todo en SQLite (backend/database.py)
        │
        └── Vista Admin de guardia (components/panel_guardia.py)
                 → lista de pacientes derivados a esa guardia, con
                   cambio de estado (Derivado → Confirmado → En
                   atención → Atendido)

LLMAdapter (backend/llm_adapter.py) es la ÚNICA clase que sabe hablar
con el proveedor del modelo (hoy OpenRouter/Gemma 4). Cambiar de
proveedor (Ollama, otra API) implica tocar solo ese archivo.
```

### Por qué el ranking de centros no lo calcula el modelo

Es una decisión de diseño deliberada. La distancia, la ocupación y la
disponibilidad de especialistas son datos objetivos y auditables: los
calcula una fórmula matemática (`AssignmentEngine`), no un LLM. Gemma
entra recién después, para la parte que la matemática no puede
resolver: interpretar el cuadro clínico en lenguaje natural y decidir
si esa recomendación objetiva sigue siendo la mejor, o si hay que
corregirla (por ejemplo, si el centro más cercano no tiene la
especialidad necesaria).

## Funcionalidades

- **Chat de triaje multi-turno** con Gemma 4, usando *function
  calling* real (no texto libre parseado a mano): el modelo invoca
  `derive_patient` con los datos estructurados cuando ya tiene
  información suficiente.
- **Protocolo de trauma catastrófico**: ante hallazgos como fractura
  expuesta, pérdida de un ojo, amputación, hemorragia incontrolable,
  etc., el triaje cierra en ROJO de inmediato, sin seguir preguntando,
  con tono profesional y directo.
- **Razonamiento adaptado al motivo de consulta**: la primera pregunta
  de seguimiento cambia según el cuadro (dolor de pecho, dificultad
  respiratoria, fiebre, dolor abdominal, trauma, pediatría, salud
  mental), no una pregunta genérica siempre igual.
- **Algoritmo de asignación determinístico**, con reglas duras:
  - Excluye centros sin la especialidad requerida (salvo que ninguno
    la tenga).
  - Para niveles ROJO/NARANJA, exige centros de complejidad mínima
    (un caso crítico no va a un centro de atención primaria si hay un
    hospital de alta complejidad cerca).
  - Penaliza centros saturados o con alta ocupación.
- **Geocoding real** (Nominatim/OpenStreetMap, gratuito) con capas de
  respaldo offline, para que el triaje nunca se trabe por falta de
  internet en el momento de la demo.
- **Datos operativos en tiempo real**: sincroniza ocupación, cola de
  espera, médicos disponibles y estado (`AVAILABLE`/`SATURATED`) desde
  `data/hospital_status.json`.
- **Centros médicos reales**: 11 centros de Oro Verde y Paraná
  cargados desde `data/centros_medicos.json`, con sus médicos
  (nombre + especialidad) tal como están en el sistema.
- **Panel de administrador de guardia**: sin login completo (acceso
  simplificado por token en la URL), muestra los pacientes derivados
  ordenados por urgencia, con cambio de estado.
- **Persistencia real en SQLite** (no JSON): tablas `guardias`,
  `pacientes`, `consultas`, con migración automática de columnas y
  auto-corrección de datos desactualizados en cada arranque.
- **Tiempos separados y sin ambigüedad**: hora de llegada al centro y
  hora estimada de atención van por separado (antes se mezclaban en
  un solo número), con timestamps ISO 8601 para consumo por API y
  formato legible para la interfaz.

## Cómo correrlo

```bash
# 1. Crear entorno virtual
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Configurar variables de entorno
cp .env.example .env
# Editar .env y completar OPENROUTER_API_KEY (ver openrouter.ai/keys)

# 4. Correr la app
streamlit run app.py
```

La primera vez que arranca, crea `data/triage.db` (SQLite) solo, sin
pasos manuales adicionales.

> Si estás actualizando desde una versión anterior del proyecto y
> hacías pruebas antes de que existiera `nivel_complejidad`/`estimated_wait`,
> borrá `data/triage.db` una vez (se regenera solo, con los datos
> correctos). De ahí en adelante no hace falta repetirlo: el sistema
> se auto-corrige en cada arranque.

## Estructura del proyecto

```
intelligent-systems-platform/
├── app.py                       # Punto de entrada Streamlit (landing + routing)
├── config.py                    # Configuración centralizada (.env)
├── backend/
│   ├── triage_agent.py            # Orquestador del triaje (chat + ranking + validación)
│   ├── assignment_engine.py        # Algoritmo de ranking de centros (sin IA)
│   ├── database.py                  # Persistencia SQLite + migraciones + carga de datos
│   ├── geocoding.py                  # Geocoding real (Nominatim) con fallback offline
│   ├── llm_adapter.py                 # Única clase que habla con OpenRouter/Gemma 4
│   ├── tools.py                        # Schema de la función derive_patient (function calling)
│   ├── prompt_manager.py                # Carga de prompts desde /prompts
│   └── models.py                         # Enums: NivelTriaje, EstadoPaciente, máquina de estados
├── components/
│   ├── landing.py                 # Selección de rol (paciente / admin)
│   ├── chat_paciente.py            # Vista del paciente (formulario + chat + tarjeta de derivación)
│   └── panel_guardia.py             # Vista del admin de guardia
├── prompts/
│   ├── triage_chat.txt             # Prompt del chat de triaje (reglas + red flags + ramas de razonamiento)
│   └── triage_validacion.txt        # Prompt de validación del ranking calculado
├── data/
│   ├── centros_medicos.json        # 11 centros reales (Oro Verde + Paraná), con médicos
│   ├── hospital_status.json         # Ocupación/cola/médicos/estado en tiempo real (mock)
│   ├── medicos_guardia.txt           # Médicos por guardia mock (formato legible, TXT)
│   └── triage.db                      # SQLite, se genera solo al arrancar
├── styles/style.css
├── .env.example
└── requirements.txt
```

## Criterios de evaluación del hackathon, y cómo los cubre el proyecto

| Criterio | Cómo lo resuelve TriageFlow |
|---|---|
| Integración de Gemma | Function calling real para el triaje + validación de ranking; el modelo es el núcleo del razonamiento clínico, no un adorno de texto |
| Innovación e impacto | Distribución inteligente de pacientes entre guardias reales de Paraná/Oro Verde, evitando saturación |
| Funcionalidad | Corre en vivo, con datos reales de centros médicos y estado operativo |
| Presentación | Tarjeta de derivación clara, con tiempos, complejidad, médicos disponibles y link a Google Maps |

## Limitaciones conocidas (para ser honestos en el writeup)

- Las coordenadas de los centros de `centros_medicos.json` son
  aproximadas (no hay geocoding exacto por dirección puntual todavía;
  ver `backend/database.py::_coordenadas_centro`).
- `hospital_status.json` es un dataset simulado de ocupación/cola, no
  una integración real con un sistema hospitalario.
- No hay autenticación real de usuarios (el acceso del admin de
  guardia es por token simple en la URL, suficiente para el alcance
  de un hackathon de un día).
- El geocoding real depende de Nominatim (OpenStreetMap), que tiene
  política de uso limitado — para producción real convendría un
  servicio con mayor cuota.

## Próximos pasos (fuera del alcance de este sprint)

- Reemplazar el acceso del admin por autenticación real.
- Confirmación de llegada del paciente por QR o check-in.
- Integración real con sistemas hospitalarios (HL7/FHIR).
- Notificación por WhatsApp cuando falten pocos turnos.
