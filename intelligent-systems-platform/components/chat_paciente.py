"""
chat_paciente.py
-----------------
Vista del paciente: alta inicial (nombre + ubicación) y luego el chat
de triaje multi-turno hasta que se genera la derivación.
"""

from __future__ import annotations

import streamlit as st

from backend import database
from backend.triage_agent import triage_agent


def render_chat_paciente() -> None:
    st.header("🩺 Consulta médica")

    if "consulta_id" not in st.session_state:
        _render_formulario_inicial()
        return

    if st.session_state.get("derivacion"):
        _render_tarjeta_derivacion(st.session_state["derivacion"])
        return

    _render_chat_en_curso()


def _render_formulario_inicial() -> None:
    st.write("Contanos brevemente qué te pasa y te vamos a ir guiando.")
    with st.form("form_inicio_consulta"):
        nombre = st.text_input("Tu nombre")
        ubicacion = st.text_input(
            "¿En qué zona de Paraná estás? (ej: centro, zona norte, San Benito, microcentro)"
        )
        motivo = st.text_area("Contanos qué te pasa")
        enviado = st.form_submit_button("Iniciar consulta")

    if enviado:
        if not nombre or not motivo:
            st.error("Completá al menos tu nombre y el motivo de consulta.")
            return

        paciente_id = database.crear_paciente(nombre, telefono=None, ubicacion_declarada=ubicacion)
        consulta_id = database.crear_consulta(paciente_id)

        st.session_state["consulta_id"] = consulta_id
        st.session_state["paciente_id"] = paciente_id
        st.session_state["mensajes_chat"] = []

        _procesar_turno(motivo)
        st.rerun()


def _render_chat_en_curso() -> None:
    for m in st.session_state["mensajes_chat"]:
        with st.chat_message(m["role"]):
            st.write(m["content"])

    respuesta_paciente = st.chat_input("Escribí tu respuesta...")
    if respuesta_paciente:
        _procesar_turno(respuesta_paciente)
        st.rerun()


def _procesar_turno(mensaje_paciente: str) -> None:
    st.session_state["mensajes_chat"].append({"role": "user", "content": mensaje_paciente})

    resultado = triage_agent.enviar_mensaje(st.session_state["consulta_id"], mensaje_paciente)

    if not resultado["ok"]:
        st.session_state["mensajes_chat"].append(
            {"role": "assistant", "content": f"⚠️ Ocurrió un error: {resultado['error']}"}
        )
        return

    st.session_state["mensajes_chat"].append(
        {"role": "assistant", "content": resultado["mensaje_para_mostrar"]}
    )

    if resultado["finalizado"]:
        st.session_state["derivacion"] = resultado["derivacion"]


def _render_tarjeta_derivacion(derivacion: dict) -> None:
    colores_triaje = {
        "rojo": "🔴", "naranja": "🟠", "amarillo": "🟡", "verde": "🟢", "azul": "🔵",
    }
    icono = colores_triaje.get(derivacion["nivel_triaje"], "⚪")

    st.success("Ya tenemos tu derivación lista")
    st.markdown(f"### {icono} Nivel de triaje: {derivacion['nivel_triaje'].capitalize()}")

    st.markdown(f"""
**Guardia recomendada:** {derivacion['guardia_nombre']}
**Dirección:** {derivacion['direccion']}
**Distancia:** {derivacion['distancia_km']} km (~{derivacion['minutos_viaje']:.0f} min de viaje)
**Espera estimada:** {derivacion['espera_estimada_min']:.0f} min
**Hora estimada de llegada sugerida:** {derivacion['hora_estimada_llegada']}
""")

    st.link_button("📍 Abrir en Google Maps", derivacion["link_maps"])
    st.caption(derivacion["razon"])

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Confirmo que voy a ir", use_container_width=True):
            database.actualizar_estado(st.session_state["consulta_id"], "Confirmado")
            st.toast("¡Confirmado! Te esperan en la guardia.")
    with col2:
        if st.button("❌ No voy a poder ir", use_container_width=True):
            database.actualizar_estado(st.session_state["consulta_id"], "Cancelado")
            st.toast("Consulta cancelada.")

    if st.button("Iniciar una nueva consulta"):
        for key in ["consulta_id", "paciente_id", "mensajes_chat", "derivacion"]:
            st.session_state.pop(key, None)
        st.rerun()
