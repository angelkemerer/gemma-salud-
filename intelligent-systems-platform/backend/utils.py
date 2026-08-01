"""
utils.py
--------
Funciones utilitarias compartidas por el backend (sin dependencias
de Streamlit: este módulo debe poder usarse también desde tests o
un futuro backend con otro frontend).
"""

from __future__ import annotations

from datetime import datetime


def formatear_fecha_hora(fecha: str, hora: str) -> str:
    return f"{fecha} {hora}"


def truncar_texto(texto: str, largo: int = 120) -> str:
    texto = texto.strip()
    return texto if len(texto) <= largo else texto[:largo].rstrip() + "…"


def marca_temporal() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def extraer_texto_archivo(uploaded_file) -> str:
    """Extrae texto plano de un archivo subido en Streamlit, según su
    extensión. Implementación mínima preparada para crecer: hoy
    soporta .txt directamente; el resto de los formatos (PDF, DOCX,
    XLSX, CSV, imágenes vía OCR) quedan como puntos de extensión
    claramente marcados, sin romper la interfaz de la función.
    """
    nombre = uploaded_file.name.lower()

    if nombre.endswith(".txt"):
        return uploaded_file.read().decode("utf-8", errors="ignore")

    if nombre.endswith(".csv"):
        return uploaded_file.read().decode("utf-8", errors="ignore")

    if nombre.endswith((".pdf", ".docx", ".xlsx", ".xls", ".png", ".jpg", ".jpeg")):
        # TODO: integrar extracción real (pypdf / python-docx / openpyxl / OCR).
        return f"[Archivo adjunto: {uploaded_file.name} — extracción de contenido pendiente de implementar]"

    return f"[Archivo adjunto: {uploaded_file.name} — formato no reconocido]"
