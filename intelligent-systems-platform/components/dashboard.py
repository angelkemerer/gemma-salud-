"""
dashboard.py
------------
Pantalla inicial: tarjetas con el estado general del sistema.
Genérico: no sabe nada de un dominio en particular, solo pide datos
resumidos al Agent / History / Module Manager.
"""

import streamlit as st


def render_dashboard(
    modelo: str,
    proveedor: str,
    conectado: bool,
    cantidad_conversaciones: int,
    tiempo_respuesta_promedio: float,
    modulo_activo_nombre: str,
    modulos_disponibles: list,
) -> None:
    st.markdown("## Dashboard")
    st.caption("Estado general de la plataforma en este momento.")

    c1, c2, c3 = st.columns(3)
    c1.markdown(_tarjeta("Modelo conectado", modelo, "🤖"), unsafe_allow_html=True)
    c2.markdown(_tarjeta("Proveedor", proveedor, "☁️"), unsafe_allow_html=True)
    c3.markdown(_tarjeta("Estado", "🟢 Online" if conectado else "🔴 Offline", "📡"), unsafe_allow_html=True)

    c4, c5, c6 = st.columns(3)
    c4.markdown(_tarjeta("Conversaciones", str(cantidad_conversaciones), "💬"), unsafe_allow_html=True)
    c5.markdown(
        _tarjeta("Tiempo de respuesta prom.", f"{tiempo_respuesta_promedio:.2f} s", "⏱️"),
        unsafe_allow_html=True,
    )
    c6.markdown(_tarjeta("Módulo activo", modulo_activo_nombre, "🧩"), unsafe_allow_html=True)

    st.markdown("### Módulos disponibles")
    cols = st.columns(min(len(modulos_disponibles), 3) or 1)
    for i, mod in enumerate(modulos_disponibles):
        with cols[i % len(cols)]:
            st.markdown(
                f'<div class="isp-module-card">'
                f'<div class="isp-module-icon">{mod["icono"]}</div>'
                f'<div class="isp-module-title">{mod["nombre_visible"]}</div>'
                f'<div class="isp-module-desc">{mod["descripcion"]}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )


def _tarjeta(titulo: str, valor: str, icono: str) -> str:
    return (
        f'<div class="isp-card">'
        f'<div class="isp-card-icon">{icono}</div>'
        f'<div class="isp-card-label">{titulo}</div>'
        f'<div class="isp-card-value">{valor}</div>'
        f'</div>'
    )
