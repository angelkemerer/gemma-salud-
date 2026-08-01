"""
header.py
---------
Barra superior de la plataforma. NUNCA cambia según el módulo activo:
siempre muestra nombre de la plataforma, modelo conectado, estado del
servidor y proveedor. No conoce OpenRouter directamente: recibe todo
como parámetros simples desde app.py.
"""

import streamlit as st


def render_header(platform_name: str, modelo: str, conectado: bool, proveedor: str) -> None:
    estado_texto = "🟢 Connected" if conectado else "🔴 Disconnected"

    col1, col2, col3, col4 = st.columns([3, 2, 1.4, 1.4])

    with col1:
        st.markdown(f'<div class="isp-brand">🧠 {platform_name}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f'<div class="isp-pill isp-pill-model">🤖 {modelo}</div>', unsafe_allow_html=True)

    with col3:
        st.markdown(f'<div class="isp-pill isp-pill-status">{estado_texto}</div>', unsafe_allow_html=True)

    with col4:
        st.markdown(f'<div class="isp-pill isp-pill-provider">☁️ {proveedor}</div>', unsafe_allow_html=True)

    st.markdown('<hr class="isp-header-divider" />', unsafe_allow_html=True)
