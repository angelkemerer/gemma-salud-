"""
database.py
------------
Capa de persistencia real (SQLite, sin dependencias externas más allá
de la librería estándar). Reemplaza al history.json para el dominio
de triaje: guardias, pacientes y consultas quedan en tablas reales,
consultables con SQL.

Se usa sqlite3 (stdlib) en vez de un ORM para no sumar dependencias
nuevas al proyecto (el requirements.txt actual solo tiene streamlit,
openai y python-dotenv).
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime
from typing import Any, Iterator, Optional

from config import config

DB_FILE = os.path.join(config.HISTORY_DIR, "triage.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS guardias (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    direccion TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    especialidades TEXT NOT NULL,        -- JSON: {"clinica": 3, "pediatria": 1, ...}
    nivel_complejidad INTEGER NOT NULL DEFAULT 1,  -- 1=centro barrial, 2=hospital general, 3=alta complejidad
    ocupacion_pct INTEGER NOT NULL,
    cola_por_nivel TEXT NOT NULL,        -- JSON: {"rojo": 0, "naranja": 1, ...} (heurística propia, por nivel de triaje)
    hospital_id_externo TEXT,            -- id en hospital_status.json (fuente de datos operativos en tiempo real)
    waiting_patients INTEGER,            -- pacientes en espera (dato real, de hospital_status.json)
    estimated_wait INTEGER,              -- minutos de espera estimados (dato real, reemplaza a la heurística cuando está presente)
    available_doctors INTEGER,           -- médicos disponibles (dato real)
    estado_operativo TEXT DEFAULT 'AVAILABLE',  -- AVAILABLE | SATURATED (dato real)
    token_admin TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pacientes (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    telefono TEXT,
    ubicacion_declarada TEXT
);

CREATE TABLE IF NOT EXISTS consultas (
    id TEXT PRIMARY KEY,
    paciente_id TEXT NOT NULL,
    motivo_consulta TEXT,
    nivel_triaje TEXT,                    -- rojo|naranja|amarillo|verde|azul|null (aún no determinado)
    especialidad_requerida TEXT,          -- clinica|pediatria|traumatologia|null
    guardia_asignada_id TEXT,
    score_calculado REAL,
    razon_gemma TEXT,
    estado TEXT NOT NULL DEFAULT 'EnTriaje',  -- ver models.EstadoPaciente
    historial_chat TEXT NOT NULL DEFAULT '[]',  -- JSON: [{"role": "...", "content": "..."}]
    hora_creacion TEXT NOT NULL,
    hora_estimada_llegada TEXT,
    FOREIGN KEY (paciente_id) REFERENCES pacientes(id),
    FOREIGN KEY (guardia_asignada_id) REFERENCES guardias(id)
);
"""

# Datos mock de guardias: identidad (nombre/dirección/coordenadas/
# especialidades/complejidad) todavía simulada; los datos OPERATIVOS
# (ocupación, cola, médicos, estado) se sincronizan desde
# data/hospital_status.json vía sincronizar_estado_hospitales() más
# abajo, usando "hospital_id_externo" como clave de unión.
# TODO: cuando haya nombre/dirección/coordenadas reales para los otros
# 17 hospitales de hospital_status.json, agregarlos acá con el mismo
# formato y listo, no hay que tocar nada más del sistema.
GUARDIAS_SEED = [
    {
        "id": "san_martin",
        "nombre": "Guardia Hospital San Martín",
        "direccion": "Av. San Martín 1230, Paraná",
        "lat": -31.7333, "lon": -60.5238,
        "especialidades": {
            "clinica": 3, "pediatria": 1, "traumatologia": 2, "cardiologia": 1,
            "cirugia_general": 1,
        },
        "nivel_complejidad": 2,
        "hospital_id_externo": "HSP-001",
        "ocupacion_pct": 45,
        "cola_por_nivel": {"rojo": 1, "naranja": 3, "amarillo": 4, "verde": 8, "azul": 6},
        "token_admin": "sm-2026-demo",
    },
    {
        "id": "zona_norte",
        "nombre": "Centro de Salud barrial (zona norte)",
        "direccion": "Calle Perú 450, Paraná",
        "lat": -31.7050, "lon": -60.5100,
        "especialidades": {"clinica": 1},
        "nivel_complejidad": 1,
        "hospital_id_externo": "HSP-002",
        "ocupacion_pct": 82,
        "cola_por_nivel": {"rojo": 0, "naranja": 0, "amarillo": 1, "verde": 2, "azul": 3},
        "token_admin": "zn-2026-demo",
    },
    {
        "id": "san_benito",
        "nombre": "Hospital de San Benito",
        "direccion": "Ruta 11 Km 4, San Benito",
        "lat": -31.7550, "lon": -60.4950,
        "especialidades": {
            "clinica": 2, "pediatria": 2, "traumatologia": 1, "neurologia": 1,
            "cardiologia": 1, "neumonologia": 1, "otorrinolaringologia": 1, "psiquiatria": 1,
        },
        "nivel_complejidad": 3,
        "hospital_id_externo": "HSP-003",
        "ocupacion_pct": 31,
        "cola_por_nivel": {"rojo": 0, "naranja": 1, "amarillo": 2, "verde": 5, "azul": 4},
        "token_admin": "sb-2026-demo",
    },
]


@contextmanager
def get_conn() -> Iterator[sqlite3.Connection]:
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


# Columnas que se agregaron después de la primera versión del schema.
# Si alguien ya tiene una data/triage.db vieja (sin estas columnas),
# esta migración simple las agrega sin perder los datos existentes.
_COLUMNAS_NUEVAS = [
    ("nivel_complejidad", "INTEGER NOT NULL DEFAULT 1"),
    ("hospital_id_externo", "TEXT"),
    ("waiting_patients", "INTEGER"),
    ("estimated_wait", "INTEGER"),
    ("available_doctors", "INTEGER"),
    ("estado_operativo", "TEXT DEFAULT 'AVAILABLE'"),
    ("medicos_nombres", "TEXT DEFAULT '[]'"),  # JSON: [{"nombre": "...", "especialidad": "..."}]
]


def _migrar_columnas_faltantes(conn: sqlite3.Connection) -> None:
    columnas_actuales = {fila["name"] for fila in conn.execute("PRAGMA table_info(guardias)")}
    for nombre, definicion in _COLUMNAS_NUEVAS:
        if nombre not in columnas_actuales:
            conn.execute(f"ALTER TABLE guardias ADD COLUMN {nombre} {definicion}")


def inicializar_db() -> None:
    """Crea las tablas si no existen, migra columnas nuevas si hace
    falta, y siembra las guardias mock (solo si la tabla está vacía,
    para no duplicar en cada reinicio)."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrar_columnas_faltantes(conn)
        existentes = conn.execute("SELECT COUNT(*) AS c FROM guardias").fetchone()["c"]
        if existentes == 0:
            for g in GUARDIAS_SEED:
                conn.execute(
                    """INSERT INTO guardias
                       (id, nombre, direccion, lat, lon, especialidades, nivel_complejidad,
                        ocupacion_pct, cola_por_nivel, hospital_id_externo, token_admin)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        g["id"], g["nombre"], g["direccion"], g["lat"], g["lon"],
                        json.dumps(g["especialidades"]), g["nivel_complejidad"],
                        g["ocupacion_pct"], json.dumps(g["cola_por_nivel"]),
                        g.get("hospital_id_externo"), g["token_admin"],
                    ),
                )


def sincronizar_estado_hospitales(ruta_json: str) -> int:
    """Lee un archivo tipo hospital_status.json (lista de objetos con
    hospital_id, occupancy, waiting_patients, estimated_wait,
    available_doctors, status) y actualiza las guardias cuyo
    hospital_id_externo matchee con algún hospital_id del archivo.

    Devuelve la cantidad de guardias actualizadas. Guardias sin
    hospital_id_externo asignado, o cuyo id no aparece en el archivo,
    quedan con los valores mock/anteriores (no se tocan).
    """
    if not os.path.exists(ruta_json):
        return 0

    with open(ruta_json, "r", encoding="utf-8") as f:
        datos_hospitales = json.load(f)

    por_id = {h["hospital_id"]: h for h in datos_hospitales}
    actualizadas = 0

    with get_conn() as conn:
        guardias = conn.execute(
            "SELECT id, hospital_id_externo FROM guardias WHERE hospital_id_externo IS NOT NULL"
        ).fetchall()
        for g in guardias:
            hsp = por_id.get(g["hospital_id_externo"])
            if hsp is None:
                continue
            conn.execute(
                """UPDATE guardias SET
                     ocupacion_pct = ?,
                     waiting_patients = ?,
                     estimated_wait = ?,
                     available_doctors = ?,
                     estado_operativo = ?
                   WHERE id = ?""",
                (
                    round(hsp["occupancy"] * 100),
                    hsp["waiting_patients"],
                    hsp["estimated_wait"],
                    hsp["available_doctors"],
                    hsp["status"],
                    g["id"],
                ),
            )
            actualizadas += 1

    return actualizadas


def cargar_medicos_desde_txt(ruta_txt: str) -> int:
    """Parsea un archivo con el formato:
        # Nombre exacto de la guardia
        - Nombre del médico (Especialidad)
        - ...
    y actualiza medicos_nombres (JSON) de cada guardia cuyo nombre
    matchee exactamente con un encabezado "# ...".

    Es un mock/simulación (ver TODO en data/medicos_guardia.txt) hasta
    que haya una integración real con el sistema de guardias del
    hospital. Devuelve la cantidad de guardias actualizadas.
    """
    if not os.path.exists(ruta_txt):
        return 0

    medicos_por_guardia: dict[str, list[dict]] = {}
    guardia_actual: Optional[str] = None

    with open(ruta_txt, "r", encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#---") or (linea.startswith("#") and "---" in linea):
                continue
            if linea.startswith("# "):
                guardia_actual = linea[2:].strip()
                medicos_por_guardia.setdefault(guardia_actual, [])
            elif linea.startswith("- ") and guardia_actual:
                match = re.match(r"-\s*(.+?)\s*\((.+?)\)\s*$", linea)
                if match:
                    nombre_medico, especialidad = match.group(1), match.group(2)
                    medicos_por_guardia[guardia_actual].append(
                        {"nombre": nombre_medico, "especialidad": especialidad}
                    )

    actualizadas = 0
    with get_conn() as conn:
        for nombre_guardia, medicos in medicos_por_guardia.items():
            resultado = conn.execute(
                "UPDATE guardias SET medicos_nombres = ? WHERE nombre = ?",
                (json.dumps(medicos, ensure_ascii=False), nombre_guardia),
            )
            if resultado.rowcount > 0:
                actualizadas += 1

    return actualizadas


# ---------------------------------------------------------------------
# Helpers de acceso (usados por assignment_engine y triage_agent)
# ---------------------------------------------------------------------
def listar_guardias() -> list[dict]:
    with get_conn() as conn:
        filas = conn.execute("SELECT * FROM guardias").fetchall()
    guardias = []
    for f in filas:
        g = dict(f)
        g["especialidades"] = json.loads(g["especialidades"])
        g["cola_por_nivel"] = json.loads(g["cola_por_nivel"])
        g["medicos_nombres"] = json.loads(g["medicos_nombres"]) if g.get("medicos_nombres") else []
        guardias.append(g)
    return guardias


def crear_paciente(nombre: str, telefono: Optional[str], ubicacion_declarada: str) -> str:
    paciente_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO pacientes (id, nombre, telefono, ubicacion_declarada) VALUES (?, ?, ?, ?)",
            (paciente_id, nombre, telefono, ubicacion_declarada),
        )
    return paciente_id


def crear_consulta(paciente_id: str) -> str:
    consulta_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO consultas (id, paciente_id, estado, historial_chat, hora_creacion)
               VALUES (?, ?, 'EnTriaje', '[]', ?)""",
            (consulta_id, paciente_id, datetime.now().isoformat()),
        )
    return consulta_id


def actualizar_historial_chat(consulta_id: str, historial: list[dict]) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE consultas SET historial_chat = ? WHERE id = ?",
            (json.dumps(historial, ensure_ascii=False), consulta_id),
        )


def cerrar_triaje(
    consulta_id: str,
    motivo_consulta: str,
    nivel_triaje: str,
    especialidad_requerida: Optional[str],
    guardia_asignada_id: str,
    score_calculado: float,
    razon_gemma: str,
    hora_estimada_llegada: str,
) -> None:
    """Guarda el resultado final del triaje + la derivación calculada."""
    with get_conn() as conn:
        conn.execute(
            """UPDATE consultas SET
                 motivo_consulta = ?,
                 nivel_triaje = ?,
                 especialidad_requerida = ?,
                 guardia_asignada_id = ?,
                 score_calculado = ?,
                 razon_gemma = ?,
                 hora_estimada_llegada = ?,
                 estado = 'Derivado'
               WHERE id = ?""",
            (
                motivo_consulta, nivel_triaje, especialidad_requerida,
                guardia_asignada_id, score_calculado, razon_gemma,
                hora_estimada_llegada, consulta_id,
            ),
        )


def obtener_consulta(consulta_id: str) -> Optional[dict]:
    with get_conn() as conn:
        fila = conn.execute("SELECT * FROM consultas WHERE id = ?", (consulta_id,)).fetchone()
    if not fila:
        return None
    c = dict(fila)
    c["historial_chat"] = json.loads(c["historial_chat"])
    return c


def listar_consultas_por_guardia(guardia_id: str) -> list[dict]:
    with get_conn() as conn:
        filas = conn.execute(
            """SELECT consultas.*, pacientes.nombre AS paciente_nombre
               FROM consultas
               JOIN pacientes ON pacientes.id = consultas.paciente_id
               WHERE consultas.guardia_asignada_id = ?
               ORDER BY
                 CASE nivel_triaje
                   WHEN 'rojo' THEN 1 WHEN 'naranja' THEN 2 WHEN 'amarillo' THEN 3
                   WHEN 'verde' THEN 4 WHEN 'azul' THEN 5 ELSE 6 END,
                 hora_estimada_llegada ASC""",
            (guardia_id,),
        ).fetchall()
    return [dict(f) for f in filas]


def actualizar_estado(consulta_id: str, nuevo_estado: str) -> None:
    with get_conn() as conn:
        conn.execute("UPDATE consultas SET estado = ? WHERE id = ?", (nuevo_estado, consulta_id))


def guardia_por_token(token: str) -> Optional[dict]:
    with get_conn() as conn:
        fila = conn.execute("SELECT * FROM guardias WHERE token_admin = ?", (token,)).fetchone()
    if not fila:
        return None
    g = dict(fila)
    g["especialidades"] = json.loads(g["especialidades"])
    g["cola_por_nivel"] = json.loads(g["cola_por_nivel"])
    g["medicos_nombres"] = json.loads(g["medicos_nombres"]) if g.get("medicos_nombres") else []
    return g


def guardia_por_id(guardia_id: str) -> Optional[dict]:
    with get_conn() as conn:
        fila = conn.execute("SELECT * FROM guardias WHERE id = ?", (guardia_id,)).fetchone()
    if not fila:
        return None
    g = dict(fila)
    g["especialidades"] = json.loads(g["especialidades"])
    g["cola_por_nivel"] = json.loads(g["cola_por_nivel"])
    g["medicos_nombres"] = json.loads(g["medicos_nombres"]) if g.get("medicos_nombres") else []
    return g
