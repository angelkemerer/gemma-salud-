"""
app.py
------
Punto de entrada de la plataforma de triaje médico y derivación
inteligente. Reemplaza al sistema multi-módulo genérico anterior
(ver README para el detalle de qué se sacó y por qué).

Dos vistas, seleccionadas por query param:
- Sin parámetros: vista Paciente (chat de triaje).
- ?guardia=<token>: vista Admin de guardia (panel de derivados).
"""

from __future__ import annotations

import streamlit as st

from backend.database import inicializar_db
from components.chat_paciente import render_chat_paciente
from components.panel_guardia import render_panel_guardia
from config import config

st.set_page_config(page_title=config.PLATFORM_NAME, page_icon="🩺", layout="centered")

# Crea las tablas (si no existen) y siembra las guardias mock al arrancar.
inicializar_db()

token_guardia = st.query_params.get("guardia")

if token_guardia:
    render_panel_guardia(token_guardia)
else:
    render_chat_paciente()
