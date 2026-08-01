"""
models.py
---------
Enums de dominio. Máquina de estados del paciente (versión recortada
a 5 estados para el alcance del hackathon, ver ARQUITECTURA_TRIAGE.md
sección 5 para la justificación de por qué se simplificó de 8 a 5).
"""

from __future__ import annotations

from enum import Enum


class NivelTriaje(str, Enum):
    ROJO = "rojo"
    NARANJA = "naranja"
    AMARILLO = "amarillo"
    VERDE = "verde"
    AZUL = "azul"


# Orden de prioridad clínica, de más a menos urgente (estándar Manchester).
ORDEN_PRIORIDAD_TRIAJE = [
    NivelTriaje.ROJO, NivelTriaje.NARANJA, NivelTriaje.AMARILLO,
    NivelTriaje.VERDE, NivelTriaje.AZUL,
]

# Tiempo de atención promedio por nivel (minutos), usado por el AssignmentEngine.
ATENCION_PROM_MIN = {
    NivelTriaje.ROJO: 25, NivelTriaje.NARANJA: 20, NivelTriaje.AMARILLO: 15,
    NivelTriaje.VERDE: 10, NivelTriaje.AZUL: 10,
}


class EstadoPaciente(str, Enum):
    EN_TRIAJE = "EnTriaje"          # el chat con Gemma todavía está en curso
    DERIVADO = "Derivado"           # Gemma determinó triaje + guardia asignada
    CONFIRMADO = "Confirmado"       # el paciente confirmó que va a ir
    EN_ATENCION = "EnAtencion"      # el admin de guardia marcó llegada + inicio
    ATENDIDO = "Atendido"           # estado terminal: alta
    CANCELADO = "Cancelado"         # estado terminal: el paciente canceló / no fue


# Transiciones válidas: origen -> conjunto de destinos permitidos.
# Cualquier transición no listada acá se considera inválida.
TRANSICIONES_VALIDAS: dict[EstadoPaciente, set[EstadoPaciente]] = {
    EstadoPaciente.EN_TRIAJE: {EstadoPaciente.DERIVADO},
    EstadoPaciente.DERIVADO: {EstadoPaciente.CONFIRMADO, EstadoPaciente.CANCELADO},
    EstadoPaciente.CONFIRMADO: {EstadoPaciente.EN_ATENCION, EstadoPaciente.CANCELADO},
    EstadoPaciente.EN_ATENCION: {EstadoPaciente.ATENDIDO},
    EstadoPaciente.ATENDIDO: set(),     # estado terminal
    EstadoPaciente.CANCELADO: set(),    # estado terminal
}


def transicion_es_valida(origen: str, destino: str) -> bool:
    try:
        origen_enum = EstadoPaciente(origen)
        destino_enum = EstadoPaciente(destino)
    except ValueError:
        return False
    return destino_enum in TRANSICIONES_VALIDAS.get(origen_enum, set())
