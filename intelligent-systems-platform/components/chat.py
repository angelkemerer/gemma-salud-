"""
chat.py
-------
Área de conversación estilo ChatGPT: historial con avatares, soporte
de markdown/código/tablas nativo de Streamlit, botón de copiar
(nativo en los bloques de código de st.chat_message) y acciones de
regenerar / limpiar conversación.

Este componente SOLO pinta. No sabe nada de OpenRouter ni de módulos:
recibe el historial ya armado y funciones callback para actuar.
"""

import streamlit as st


def render_chat(historial_chat: list[dict], on_regenerar=None, on_limpiar=None) -> None:
    header_col, actions_col = st.columns([5, 1.6])
    with header_col:
        st.markdown("### Chat")
    with actions_col:
        sub1, sub2 = st.columns(2)
        with sub1:
            if st.button("🔄 Regenerar", use_container_width=True, disabled=not historial_chat):
                if on_regenerar:
                    on_regenerar()
        with sub2:
            if st.button("🗑️ Limpiar", use_container_width=True, disabled=not historial_chat):
                if on_limpiar:
                    on_limpiar()

    chat_container = st.container(height=480)
    with chat_container:
        if not historial_chat:
            st.info("Escribí tu consulta abajo para empezar la conversación con el módulo activo.")

        for turno in historial_chat:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(turno["pregunta"])
            with st.chat_message("assistant", avatar="🤖"):
                st.markdown(turno["respuesta"])
