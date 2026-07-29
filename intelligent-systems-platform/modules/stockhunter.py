"""
stockhunter.py
--------------
Módulo: Buscador de stock de medicamentos en la red pública de salud.

Cruza el pedido del usuario (nombre del medicamento, extraído de una
receta escrita o adjunta) contra una base de datos de stock por
centro de salud, y arma el contexto que luego el Agent le pasa al LLM
para redactar una respuesta clara con la ruta óptima de retiro.

La "base de datos" es un mock en memoria/JSON para el hackathon.
Reemplazarla por una consulta real a la red de salud (API, CSV del
remito, base SQL) no requiere tocar nada fuera de este archivo.
"""

from __future__ import annotations

from typing import Any, Optional

from modules.base_module import BaseModule

# --- Mock de stock por centro de salud (reemplazable por datos reales) ---
STOCK_CENTROS = [
    {"centro": "Centro de Salud Carrillo", "medicamento": "Insulina NPH", "unidades": 0},
    {"centro": "Hospital San Martín", "medicamento": "Insulina NPH", "unidades": 15},
    {"centro": "Centro de Salud Corrales", "medicamento": "Insulina NPH", "unidades": 8},
    {"centro": "Centro de Salud Carrillo", "medicamento": "Clonazepam 2mg", "unidades": 3},
    {"centro": "Hospital San Martín", "medicamento": "Clonazepam 2mg", "unidades": 0},
    {"centro": "Hospital de San Benito", "medicamento": "Clonazepam 2mg", "unidades": 20},
    {"centro": "Centro de Salud Corrales", "medicamento": "Levotiroxina 100mcg", "unidades": 12},
]


class StockHunterModule(BaseModule):
    nombre = "stockhunter"
    nombre_visible = "StockHunter"
    descripcion = "Busca stock de medicamentos en la red pública y arma la ruta de retiro más conveniente."
    archivo_prompt = "stockhunter.txt"
    icono = "💊"
    acepta_archivos = ["pdf", "png", "jpg", "jpeg", "txt"]

    def herramientas(self) -> list[str]:
        return ["Búsqueda de stock por centro", "Cálculo de ruta óptima", "Reserva de turno de retiro (simulada)"]

    def _buscar_stock(self, medicamento: str) -> list[dict]:
        medicamento_norm = medicamento.strip().lower()
        return [
            fila for fila in STOCK_CENTROS
            if medicamento_norm in fila["medicamento"].lower()
        ]

    def construir_contexto(
        self,
        pregunta: str,
        historial: Optional[list[dict]] = None,
        archivos: Optional[list[Any]] = None,
    ) -> str:
        # Heurística simple para el demo: buscamos cualquier medicamento
        # conocido mencionado en la pregunta. En una versión productiva,
        # este paso se resolvería con extracción de entidades (o el
        # propio LLM) sobre el texto de la receta / archivo adjunto.
        medicamentos_conocidos = {fila["medicamento"] for fila in STOCK_CENTROS}
        encontrados = [m for m in medicamentos_conocidos if m.lower().split()[0] in pregunta.lower()]

        if not encontrados:
            return (
                "No se detectó un medicamento reconocido en la base de stock simulada. "
                "Pedile al usuario el nombre exacto del medicamento."
            )

        bloques = []
        for medicamento in encontrados:
            resultados = self._buscar_stock(medicamento)
            resultados_txt = "\n".join(
                f"- {r['centro']}: {r['unidades']} unidades" for r in resultados
            )
            bloques.append(f"Stock actual de {medicamento}:\n{resultados_txt}")

        return "\n\n".join(bloques)
