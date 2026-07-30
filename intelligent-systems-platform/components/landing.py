"""
landing.py
----------
Pantalla inicial: el usuario elige si entra como Paciente o como
Administrador de guardia. Es la primera pantalla que ve cualquiera
al abrir la app (sin necesidad de tocar la URL a mano).
"""

from __future__ import annotations

import streamlit as st

from backend import database


def render_landing() -> None:
    st.title("🩺 TriageFlow Paraná")
    st.write("Sistema de triaje médico y derivación inteligente a guardias.")
    st.divider()
    st.subheader("¿Cómo querés ingresar?")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 🧑 Paciente")
        st.caption("Iniciar una consulta y recibir una derivación.")
        if st.button("Ingresar como paciente", use_container_width=True):
            st.session_state["vista"] = "paciente"
            st.rerun()

    with col2:
        st.markdown("#### 🏥 Administrador de guardia")
        st.caption("Ver los pacientes derivados a tu centro de salud.")
        if st.button("Ingresar como administrador", use_container_width=True):
            st.session_state["vista"] = "seleccionar_guardia"
            st.rerun()


def render_seleccion_guardia() -> None:
    st.title("🏥 Ingreso de administrador")
    st.write("Seleccioná tu guardia:")

    guardias = database.listar_guardias()
    opciones = {g["nombre"]: g["token_admin"] for g in guardias}

    elegido = st.selectbox("Guardia", list(opciones.keys()))

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Ingresar", use_container_width=True):
            st.session_state["token_guardia_admin"] = opciones[elegido]
            st.session_state["vista"] = "admin"
            st.rerun()
    with col2:
        if st.button("← Volver", use_container_width=True):
            st.session_state.pop("vista", None)
            st.rerun()
