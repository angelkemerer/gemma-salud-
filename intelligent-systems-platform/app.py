"""
app.py
------
Punto de entrada de la interfaz (Streamlit).

REGLA DE ORO: esta capa NUNCA importa OpenRouter, ni llama al LLM
directamente. Solamente conoce al Agent:

    resultado = agent.consultar(pregunta, modulo, historial, archivos, conv_id)

Todo lo demás (prompts, adaptador de modelo, módulos de dominio,
historial) vive en backend/ y modules/, desacoplado de esta capa.
"""

import streamlit as st

from config import config
from backend.agent import agent
from backend.module_manager import module_manager
from backend.history import history_store

from components.header import render_header
from components.sidebar import render_sidebar
from components.dashboard import render_dashboard
from components.chat import render_chat
from components.input_box import render_input_box
from components.footer import render_footer


# ----------------------------------------------------------------------
# Configuración de página y estilos
# ----------------------------------------------------------------------
st.set_page_config(
    page_title=config.PLATFORM_NAME,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


def cargar_estilos() -> None:
    try:
        with open(config.STYLE_CSS, "r", encoding="utf-8") as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    except FileNotFoundError:
        pass


cargar_estilos()


# ----------------------------------------------------------------------
# Estado de sesión
# ----------------------------------------------------------------------
def inicializar_estado() -> None:
    defaults = {
        "pagina_activa": "Dashboard",
        "modulo_activo": config.DEFAULT_MODULE,
        "historial_chat": [],  # historial de la conversación EN CURSO
        "conv_id": None,
    }
    for clave, valor in defaults.items():
        if clave not in st.session_state:
            st.session_state[clave] = valor


inicializar_estado()


# ----------------------------------------------------------------------
# Barra superior + sidebar (siempre visibles, no dependen del dominio)
# ----------------------------------------------------------------------
render_header(
    platform_name=config.PLATFORM_NAME,
    modelo=agent.modelo_actual(),
    conectado=agent.conectado(),
    proveedor=config.PROVIDER.capitalize(),
)

pagina = render_sidebar(config.PLATFORM_NAME)


# ----------------------------------------------------------------------
# Helpers de página
# ----------------------------------------------------------------------
def _asegurar_conversacion() -> str:
    if not st.session_state["conv_id"]:
        st.session_state["conv_id"] = history_store.nueva_conversacion(
            modulo=st.session_state["modulo_activo"],
            modelo=agent.modelo_actual(),
        )
    return st.session_state["conv_id"]


def _enviar_pregunta(pregunta: str, archivos: list) -> None:
    conv_id = _asegurar_conversacion()
    with st.spinner("Pensando…"):
        resultado = agent.consultar(
            pregunta=pregunta,
            modulo=st.session_state["modulo_activo"],
            historial_chat=st.session_state["historial_chat"],
            archivos=archivos,
            conv_id=conv_id,
        )

    if resultado["ok"]:
        st.session_state["historial_chat"].append({
            "pregunta": pregunta,
            "respuesta": resultado["respuesta"],
        })
    else:
        st.error(f"No se pudo obtener respuesta: {resultado['error']}")

    st.rerun()


def _regenerar_ultima() -> None:
    if not st.session_state["historial_chat"]:
        return
    ultimo = st.session_state["historial_chat"].pop()
    _enviar_pregunta(ultimo["pregunta"], [])


def _limpiar_conversacion() -> None:
    st.session_state["historial_chat"] = []
    st.session_state["conv_id"] = None
    st.rerun()


# ----------------------------------------------------------------------
# Páginas
# ----------------------------------------------------------------------
def pagina_dashboard() -> None:
    conversaciones = history_store.listar_conversaciones()
    modulo_activo = module_manager.obtener_modulo(st.session_state["modulo_activo"])

    render_dashboard(
        modelo=agent.modelo_actual(),
        proveedor=config.PROVIDER.capitalize(),
        conectado=agent.conectado(),
        cantidad_conversaciones=len(conversaciones),
        tiempo_respuesta_promedio=agent.ultimo_tiempo_respuesta(),
        modulo_activo_nombre=modulo_activo.nombre_visible,
        modulos_disponibles=[m.to_dict() for m in module_manager.listar_modulos()],
    )


def pagina_chat() -> None:
    modulo_activo = module_manager.obtener_modulo(st.session_state["modulo_activo"])

    st.caption(f"Módulo activo: **{modulo_activo.icono} {modulo_activo.nombre_visible}** — {modulo_activo.descripcion}")

    render_chat(
        st.session_state["historial_chat"],
        on_regenerar=_regenerar_ultima,
        on_limpiar=_limpiar_conversacion,
    )

    pregunta, archivos = render_input_box(modulo_activo.acepta_archivos)
    if pregunta:
        _enviar_pregunta(pregunta, archivos)


def pagina_modules() -> None:
    st.markdown("## Modules")
    st.caption("Elegí el módulo especializado que va a atender la conversación.")

    modulos = module_manager.listar_modulos()
    cols = st.columns(3)

    for i, mod in enumerate(modulos):
        with cols[i % 3]:
            activo = mod.nombre == st.session_state["modulo_activo"]
            st.markdown(
                f'<div class="isp-module-card">'
                f'<div class="isp-module-icon">{mod.icono}</div>'
                f'<div class="isp-module-title">{mod.nombre_visible}</div>'
                f'<div class="isp-module-desc">{mod.descripcion}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            herramientas = mod.herramientas()
            if herramientas:
                st.caption("🔧 " + " · ".join(herramientas))

            if st.button(
                "✅ Activo" if activo else "Usar este módulo",
                key=f"activar_{mod.nombre}",
                use_container_width=True,
                disabled=activo,
            ):
                st.session_state["modulo_activo"] = mod.nombre
                st.session_state["historial_chat"] = []
                st.session_state["conv_id"] = None
                st.session_state["pagina_activa"] = "Chat"
                st.rerun()


def pagina_files() -> None:
    st.markdown("## Files")
    st.caption(
        "La plataforma está preparada para recibir archivos de distintos formatos. "
        "El adjunto se hace desde la caja de entrada del Chat, según lo que acepte el módulo activo."
    )
    st.markdown("**Formatos soportados por la arquitectura:**")
    st.write(", ".join(f".{ext}" for ext in config.SUPPORTED_FILE_TYPES))

    modulo_activo = module_manager.obtener_modulo(st.session_state["modulo_activo"])
    st.markdown(f"**Formatos que acepta el módulo activo ({modulo_activo.nombre_visible}):**")
    if modulo_activo.acepta_archivos:
        st.write(", ".join(f".{ext}" for ext in modulo_activo.acepta_archivos))
    else:
        st.write("Este módulo todavía no procesa archivos adjuntos.")


def pagina_history() -> None:
    st.markdown("## History")
    conversaciones = history_store.listar_conversaciones()

    if not conversaciones:
        st.info("Todavía no hay conversaciones guardadas.")
        return

    for conv in reversed(conversaciones):
        titulo = f"{conv['fecha']} {conv['hora']} · {conv['modulo']} · {conv['modelo']} · {len(conv['turnos'])} turnos"
        with st.expander(titulo):
            for turno in conv["turnos"]:
                st.markdown(f"**🧑 {turno['pregunta']}**")
                st.markdown(f"🤖 {turno['respuesta']}")
                st.markdown("---")


def pagina_settings() -> None:
    st.markdown("## Settings")

    st.markdown("### Modelo")
    modelos = agent.modelos_disponibles()
    modelo_actual = agent.modelo_actual()
    indice = modelos.index(modelo_actual) if modelo_actual in modelos else 0

    nuevo_modelo = st.selectbox("Modelo activo", modelos, index=indice)
    if nuevo_modelo != modelo_actual:
        agent.cambiar_modelo(nuevo_modelo)
        st.success(f"Modelo cambiado a {nuevo_modelo}")
        st.rerun()

    st.markdown("### Proveedor")
    st.text_input("Proveedor", value=config.PROVIDER, disabled=True)
    st.text_input("Base URL", value=config.OPENROUTER_BASE_URL, disabled=True)

    st.markdown("### Historial")
    if st.button("🗑️ Borrar todo el historial", type="secondary"):
        history_store.borrar_todo()
        st.success("Historial borrado.")
        st.rerun()


# ----------------------------------------------------------------------
# Router
# ----------------------------------------------------------------------
PAGINAS = {
    "Dashboard": pagina_dashboard,
    "Chat": pagina_chat,
    "Modules": pagina_modules,
    "Files": pagina_files,
    "History": pagina_history,
    "Settings": pagina_settings,
}

PAGINAS.get(pagina, pagina_dashboard)()

render_footer(config.PLATFORM_NAME)
