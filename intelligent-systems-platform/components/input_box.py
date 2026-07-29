"""
input_box.py
------------
Caja de entrada inferior: área de texto, contador de caracteres,
botón de adjuntar archivo y botón enviar.

CRÍTICO: este componente nunca llama al modelo directamente. Al
enviar, únicamente devuelve un string (y opcionalmente archivos) hacia
app.py, que es quien invoca a agente.consultar(...).
"""

import streamlit as st

MAX_CARACTERES = 4000


def render_input_box(acepta_archivos: list[str]) -> tuple[str | None, list]:
    """Devuelve (texto_enviado, archivos) o (None, []) si no se envió nada."""

    texto = st.text_area(
        "Mensaje",
        key="isp_input_text",
        height=100,
        placeholder="Escribí tu consulta acá…",
        label_visibility="collapsed",
    )

    col_count, col_attach, col_send = st.columns([3, 1, 1])

    with col_count:
        largo = len(texto) if texto else 0
        color = "isp-count-warning" if largo > MAX_CARACTERES else "isp-count-normal"
        st.markdown(f'<span class="{color}">{largo} / {MAX_CARACTERES} caracteres</span>', unsafe_allow_html=True)

    with col_attach:
        archivos = st.file_uploader(
            "Adjuntar",
            type=acepta_archivos or None,
            accept_multiple_files=True,
            label_visibility="collapsed",
            key="isp_file_uploader",
        )

    with col_send:
        enviar = st.button("➤ Enviar", type="primary", use_container_width=True)

    if enviar and texto and texto.strip() and len(texto) <= MAX_CARACTERES:
        return texto.strip(), archivos or []

    if enviar and (not texto or not texto.strip()):
        st.warning("Escribí una consulta antes de enviar.")

    return None, []
