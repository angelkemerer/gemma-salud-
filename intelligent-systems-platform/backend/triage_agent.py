"""
triage_agent.py
-----------------
Orquestador del flujo completo de triaje conversacional. Reemplaza,
para este dominio específico, al Agent genérico multi-módulo: acá
Gemma SIEMPRE responde en el protocolo JSON definido en
prompts/triage_chat.txt, hasta que decide que tiene información
suficiente (listo=true). En ese momento:

  1. Se geocodifica la ubicación declarada del paciente (mock simple
     por barrio; ver GEOCODIFICACION_BARRIOS más abajo).
  2. Se llama al AssignmentEngine (sin IA) para obtener el ranking de
     guardias candidatas.
  3. Se le pide a Gemma que valide o corrija el ranking, con el prompt
     de prompts/triage_validacion.txt.
  4. Se persiste todo en la base de datos (database.cerrar_triaje).

La UI (Streamlit) solo llama a TriageAgent.enviar_mensaje(...) y
recibe un dict con lo que tiene que mostrar. Nunca sabe que por
debajo hay dos llamados a Gemma, un algoritmo de ranking, y SQLite.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta
from typing import Optional

from backend.assignment_engine import calcular_ranking
from backend.llm_adapter import LLMAdapter, LLMAdapterError
from backend.models import NivelTriaje
from backend.prompt_manager import prompt_manager
from backend import database

# Geocodificación mock: barrio de Paraná mencionado en el texto -> coords.
# TODO: reemplazar por geolocalización real del navegador/dispositivo.
GEOCODIFICACION_BARRIOS = {
    "centro": (-31.7333, -60.5238),
    "zona norte": (-31.7000, -60.5050),
    "san benito": (-31.7500, -60.5000),
    "microcentro": (-31.7320, -60.5260),
}
UBICACION_DEFAULT = GEOCODIFICACION_BARRIOS["centro"]


def _geocodificar(texto_ubicacion: str) -> tuple[float, float]:
    texto = (texto_ubicacion or "").lower()
    for barrio, coords in GEOCODIFICACION_BARRIOS.items():
        if barrio in texto:
            return coords
    return UBICACION_DEFAULT


def _extraer_json(texto: str) -> dict:
    """Extrae un objeto JSON de la respuesta del modelo, tolerando que
    venga envuelto en ```json ... ``` o con texto alrededor."""
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", texto, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        inicio = texto.find("{")
        fin = texto.rfind("}")
        if inicio == -1 or fin == -1:
            raise ValueError(f"No se encontró JSON en la respuesta del modelo: {texto}")
        json_str = texto[inicio:fin + 1]
    return json.loads(json_str)


class TriageAgent:
    def __init__(self, llm_adapter: Optional[LLMAdapter] = None):
        self._llm = llm_adapter or LLMAdapter()

    # ------------------------------------------------------------------
    # Punto de entrada único para la UI (vista Paciente)
    # ------------------------------------------------------------------
    def enviar_mensaje(self, consulta_id: str, mensaje_paciente: str) -> dict:
        """Procesa un turno del chat. Devuelve:
        {
          "ok": bool,
          "finalizado": bool,        # true cuando ya hay derivación
          "mensaje_para_mostrar": str,
          "derivacion": dict | None, # presente solo si finalizado=True
          "error": str | None,
        }
        """
        consulta = database.obtener_consulta(consulta_id)
        if consulta is None:
            return {"ok": False, "finalizado": False, "mensaje_para_mostrar": "",
                     "derivacion": None, "error": "Consulta no encontrada."}

        historial = consulta["historial_chat"]
        historial.append({"role": "user", "content": mensaje_paciente})

        prompt_sistema = prompt_manager.obtener_prompt("triage_chat.txt")
        mensajes = [{"role": "system", "content": prompt_sistema}] + historial

        try:
            respuesta_cruda = self._llm.generar_respuesta(mensajes)
            resultado = _extraer_json(respuesta_cruda)
        except (LLMAdapterError, ValueError, json.JSONDecodeError) as exc:
            return {"ok": False, "finalizado": False, "mensaje_para_mostrar": "",
                     "derivacion": None, "error": f"Error al procesar la respuesta del modelo: {exc}"}

        historial.append({"role": "assistant", "content": resultado["mensaje_paciente"]})
        database.actualizar_historial_chat(consulta_id, historial)

        if not resultado.get("listo", False):
            return {
                "ok": True, "finalizado": False,
                "mensaje_para_mostrar": resultado["mensaje_paciente"],
                "derivacion": None, "error": None,
            }

        # listo=True: tenemos nivel de triaje + especialidad. Calculamos
        # la derivación (ranking sin IA + validación con IA).
        return self._finalizar_triaje(consulta_id, consulta["paciente_id"], resultado)

    # ------------------------------------------------------------------
    # Cierre del triaje: ranking + validación por Gemma + persistencia
    # ------------------------------------------------------------------
    def _finalizar_triaje(self, consulta_id: str, paciente_id: str, resultado_triaje: dict) -> dict:
        paciente = self._obtener_ubicacion_paciente(paciente_id)
        nivel_triaje = NivelTriaje(resultado_triaje["nivel_triaje"])
        especialidad = resultado_triaje.get("especialidad_requerida")

        ranking = calcular_ranking(paciente, nivel_triaje, especialidad)
        if not ranking:
            return {"ok": False, "finalizado": False, "mensaje_para_mostrar": "",
                     "derivacion": None, "error": "No hay guardias disponibles en el sistema."}

        try:
            validacion = self._validar_ranking(ranking, resultado_triaje)
        except (LLMAdapterError, ValueError, json.JSONDecodeError):
            # Fallback: si la validación por IA falla, usamos directamente
            # el primer resultado del ranking calculado (nunca dejamos al
            # paciente sin derivación por un error de parseo del modelo).
            mejor = ranking[0]
            validacion = {
                "guardia_id_elegida": mejor["guardia_id"],
                "razon_gemma": "Asignación automática por score más bajo (fallback sin validación de IA).",
                "mensaje_paciente_final": (
                    f"Te recomendamos dirigirte a {mejor['nombre']}, "
                    f"a {mejor['distancia_km']} km de tu ubicación."
                ),
            }

        elegida = next(
            (g for g in ranking if g["guardia_id"] == validacion["guardia_id_elegida"]),
            ranking[0],
        )

        eta = datetime.now() + timedelta(minutes=elegida["minutos_viaje"] + elegida["espera_estimada_min"])

        database.cerrar_triaje(
            consulta_id=consulta_id,
            motivo_consulta=resultado_triaje.get("motivo_consulta_resumen", ""),
            nivel_triaje=nivel_triaje.value,
            especialidad_requerida=especialidad,
            guardia_asignada_id=elegida["guardia_id"],
            score_calculado=elegida["score_total_min"],
            razon_gemma=validacion["razon_gemma"],
            hora_estimada_llegada=eta.isoformat(),
        )

        derivacion = {
            "guardia_nombre": elegida["nombre"],
            "direccion": elegida["direccion"],
            "distancia_km": elegida["distancia_km"],
            "minutos_viaje": elegida["minutos_viaje"],
            "espera_estimada_min": elegida["espera_estimada_min"],
            "hora_estimada_llegada": eta.strftime("%H:%M"),
            "nivel_triaje": nivel_triaje.value,
            "link_maps": f"https://www.google.com/maps/dir/?api=1&destination={elegida['lat']},{elegida['lon']}",
            "razon": validacion["razon_gemma"],
        }

        return {
            "ok": True, "finalizado": True,
            "mensaje_para_mostrar": validacion["mensaje_paciente_final"],
            "derivacion": derivacion, "error": None,
        }

    def _validar_ranking(self, ranking: list[dict], resultado_triaje: dict) -> dict:
        prompt_sistema = prompt_manager.obtener_prompt("triage_validacion.txt")
        contexto = (
            f"Resumen clínico: {resultado_triaje.get('motivo_consulta_resumen')}\n"
            f"Nivel de triaje: {resultado_triaje.get('nivel_triaje')}\n"
            f"Especialidad requerida: {resultado_triaje.get('especialidad_requerida')}\n\n"
            f"Ranking calculado:\n{json.dumps(ranking, ensure_ascii=False, indent=2)}"
        )
        mensajes = [
            {"role": "system", "content": prompt_sistema},
            {"role": "user", "content": contexto},
        ]
        respuesta_cruda = self._llm.generar_respuesta(mensajes)
        return _extraer_json(respuesta_cruda)

    def _obtener_ubicacion_paciente(self, paciente_id: str) -> tuple[float, float]:
        # La ubicación declarada del paciente se guardó como texto libre
        # al crear el registro (ver database.crear_paciente).
        with database.get_conn() as conn:
            fila = conn.execute(
                "SELECT ubicacion_declarada FROM pacientes WHERE id = ?", (paciente_id,)
            ).fetchone()
        texto = fila["ubicacion_declarada"] if fila else ""
        return _geocodificar(texto)


triage_agent = TriageAgent()
