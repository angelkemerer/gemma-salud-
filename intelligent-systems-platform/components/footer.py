"""
footer.py
---------
Pie de página simple y genérico.
"""

import streamlit as st


def render_footer(platform_name: str) -> None:
    st.markdown(
        f'<div class="isp-footer">{platform_name} · Arquitectura modular · '
        f'Motor de IA intercambiable vía LLM Adapter</div>',
        unsafe_allow_html=True,
    )
