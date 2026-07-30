"""
app.py
------
Punto de entrada de la plataforma de triaje médico y derivación
inteligente.

Flujo de pantallas:
1. Landing: elegís Paciente o Administrador de guardia.
2a. Paciente -> chat de triaje.
2b. Administrador -> selecciona su guardia -> panel de derivados.

Atajo opcional: abrir la app con ?guardia=<token> en la URL salta
directo al panel de esa guardia (útil para compartir un link fijo),
sin pasar por la pantalla de selección.
"""

from __future__ import annotations

import os

import streamlit as st

from backend.database import inicializar_db, sincronizar_estado_hospitales, cargar_medicos_desde_txt
from components.chat_paciente import render_chat_paciente
from components.landing import render_landing, render_seleccion_guardia
from components.panel_guardia import render_panel_guardia
from config import config

st.set_page_config(page_title=config.PLATFORM_NAME, page_icon="🩺", layout="centered")

# Crea las tablas (si no existen) y siembra las guardias mock al arrancar.
inicializar_db()

# Sincroniza ocupación/cola/médicos/estado real desde hospital_status.json
# (se ejecuta en cada arranque, así los datos operativos quedan al día
# sin tener que reiniciar manualmente la base).
_ruta_estado_hospitales = os.path.join(config.HISTORY_DIR, "hospital_status.json")
sincronizar_estado_hospitales(_ruta_estado_hospitales)

# Carga los médicos disponibles (nombre + especialidad) por guardia.
_ruta_medicos = os.path.join(config.HISTORY_DIR, "medicos_guardia.txt")
cargar_medicos_desde_txt(_ruta_medicos)

# Atajo por URL: ?guardia=<token> salta directo al panel de esa guardia.
token_url = st.query_params.get("guardia")
if token_url and "vista" not in st.session_state:
    st.session_state["vista"] = "admin"
    st.session_state["token_guardia_admin"] = token_url

vista = st.session_state.get("vista")

# Botón para volver al inicio, visible en cualquier vista que no sea la landing.
if vista:
    with st.sidebar:
        if st.button("← Volver al inicio"):
            for key in ["vista", "token_guardia_admin", "consulta_id", "paciente_id",
                        "mensajes_chat", "derivacion"]:
                st.session_state.pop(key, None)
            st.query_params.clear()
            st.rerun()

if vista == "paciente":
    render_chat_paciente()
elif vista == "seleccionar_guardia":
    render_seleccion_guardia()
elif vista == "admin":
    render_panel_guardia(st.session_state["token_guardia_admin"])
else:
    render_landing()
