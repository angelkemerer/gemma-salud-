"""
panel_guardia.py
-----------------
Vista del administrador de guardia. Acceso simplificado por token en
la URL (?guardia=TOKEN), sin sistema de login completo (ver
ARQUITECTURA_TRIAGE.md, sección 8, justificación de este recorte de
alcance para el hackathon).
"""

from __future__ import annotations

import streamlit as st

from backend import database
from backend.models import EstadoPaciente, transicion_es_valida

ETIQUETAS_ESTADO = {
    "EnTriaje": "⏳ En triaje",
    "Derivado": "📍 Derivado",
    "Confirmado": "✅ Confirmó asistencia",
    "EnAtencion": "🩺 En atención",
    "Atendido": "🏁 Atendido (alta)",
    "Cancelado": "❌ Cancelado",
}

# Próximo estado sugerido por cada estado actual (para el botón de acción rápida).
SIGUIENTE_ESTADO_SUGERIDO = {
    "Confirmado": "EnAtencion",
    "EnAtencion": "Atendido",
}


def render_panel_guardia(token: str) -> None:
    guardia = database.guardia_por_token(token)
    if guardia is None:
        st.error("Token de guardia inválido. Verificá el link de acceso.")
        return

    st.header(f"🏥 Panel — {guardia['nombre']}")
    st.caption(guardia["direccion"])

    consultas = database.listar_consultas_por_guardia(guardia["id"])
    consultas_activas = [c for c in consultas if c["estado"] not in ("Atendido", "Cancelado")]
    consultas_cerradas = [c for c in consultas if c["estado"] in ("Atendido", "Cancelado")]

    st.subheader(f"Pacientes derivados ({len(consultas_activas)} activos)")

    if not consultas_activas:
        st.info("No hay pacientes derivados a esta guardia por el momento.")
    else:
        for c in consultas_activas:
            _render_fila_consulta(c)

    if consultas_cerradas:
        with st.expander(f"Ver histórico ({len(consultas_cerradas)})"):
            for c in consultas_cerradas:
                _render_fila_consulta(c, permitir_accion=False)


def _render_fila_consulta(consulta: dict, permitir_accion: bool = True) -> None:
    col1, col2, col3, col4 = st.columns([3, 2, 2, 2])

    with col1:
        st.markdown(f"**{consulta['paciente_nombre']}**")
        st.caption(consulta.get("motivo_consulta") or "—")
    with col2:
        nivel = consulta.get("nivel_triaje") or "—"
        st.write(f"Triaje: {nivel}")
    with col3:
        st.write(ETIQUETAS_ESTADO.get(consulta["estado"], consulta["estado"]))
    with col4:
        if permitir_accion:
            siguiente = SIGUIENTE_ESTADO_SUGERIDO.get(consulta["estado"])
            if siguiente and transicion_es_valida(consulta["estado"], siguiente):
                etiqueta_boton = ETIQUETAS_ESTADO[siguiente]
                if st.button(f"→ {etiqueta_boton}", key=f"btn_{consulta['id']}"):
                    database.actualizar_estado(consulta["id"], siguiente)
                    st.rerun()

    st.divider()
