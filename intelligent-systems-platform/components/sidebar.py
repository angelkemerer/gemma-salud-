"""
sidebar.py
----------
Barra lateral de navegación. Es fija y genérica: nunca depende del
dominio de aplicación ni de qué módulos existen. Las páginas son
siempre las mismas: Dashboard, Chat, Modules, Files, History, Settings.
"""

import streamlit as st

PAGINAS = [
    ("Dashboard", "📊"),
    ("Chat", "💬"),
    ("Modules", "🧩"),
    ("Files", "📁"),
    ("History", "🕘"),
    ("Settings", "⚙️"),
]


def render_sidebar(platform_name: str) -> str:
    with st.sidebar:
        st.markdown(f'<div class="isp-sidebar-title">{platform_name}</div>', unsafe_allow_html=True)
        st.markdown('<div class="isp-sidebar-subtitle">Plataforma de asistentes IA</div>', unsafe_allow_html=True)
        st.markdown("---")

        pagina_actual = st.session_state.get("pagina_activa", "Dashboard")

        for nombre, icono in PAGINAS:
            seleccionado = nombre == pagina_actual
            estilo = "primary" if seleccionado else "secondary"
            if st.button(f"{icono}  {nombre}", key=f"nav_{nombre}", use_container_width=True, type=estilo):
                st.session_state["pagina_activa"] = nombre
                st.rerun()

        st.markdown("---")
        st.caption("v0.1 · Arquitectura modular")

    return st.session_state.get("pagina_activa", "Dashboard")
