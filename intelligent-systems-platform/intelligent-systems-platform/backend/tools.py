"""
tools.py
--------
Definición de herramientas (function calling, formato OpenAI/OpenRouter)
que usa TriageAgent. Separado del prompt de texto porque el schema debe
viajar en el parámetro `tools` de la llamada al modelo, no en el system
prompt.
"""

from __future__ import annotations

DERIVE_PATIENT_TOOL = {
    "type": "function",
    "function": {
        "name": "derive_patient",
        "description": "Envía al paciente al sistema de derivación inteligente basándose en el triaje realizado.",
        "parameters": {
            "type": "object",
            "properties": {
                "triage_level": {
                    "type": "string",
                    "enum": ["ROJO", "NARANJA", "AMARILLO", "VERDE", "AZUL"],
                    "description": "El nivel de urgencia asignado al paciente.",
                },
                "specialty": {
                    "type": "string",
                    "enum": [
                        "Traumatología", "Pediatría", "Cardiología", "Neurología",
                        "Clínica Médica", "Cirugía General", "Neumonología",
                        "Otorrinolaringología", "Psiquiatría",
                    ],
                    "description": "La especialidad médica requerida para el caso.",
                },
                "symptoms_summary": {
                    "type": "string",
                    "description": "Resumen breve y técnico de los síntomas para el médico de la guardia.",
                },
                "urgency_score": {
                    "type": "integer",
                    "description": "Valor del 1 al 10 donde 10 es riesgo vital inmediato.",
                },
            },
            "required": ["triage_level", "specialty", "symptoms_summary"],
        },
    },
}

# Mapeo de las especialidades del schema (español, con tildes, como las
# espera el modelo) a las claves internas usadas en guardias.especialidades
# (sin tildes, snake_case, como quedaron definidas en database.py).
MAPEO_ESPECIALIDAD = {
    "Traumatología": "traumatologia",
    "Pediatría": "pediatria",
    "Cardiología": "cardiologia",
    "Neurología": "neurologia",
    "Clínica Médica": "clinica",
    "Cirugía General": "cirugia_general",
    "Neumonología": "neumonologia",
    "Otorrinolaringología": "otorrinolaringologia",
    "Psiquiatría": "psiquiatria",
}
