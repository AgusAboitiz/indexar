from datetime import date

import psycopg2
from fastapi import FastAPI

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "indexar",
    "user": "indexar",
    "password": "indexar_dev_pass",
}

app = FastAPI(title="IndexAR API")


def get_conn():
    return psycopg2.connect(**DB_CONFIG)


def obtener_codigo_y_tipo(conn, serie_id):
    with conn.cursor() as cur:
        cur.execute("SELECT codigo, tipo FROM series WHERE serie_id = %s", (serie_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Serie '{serie_id}' no encontrada")
        return row


def obtener_valor_serie(conn, codigo, tipo, fecha):
    """Busca el último valor disponible de una serie tipo cotizacion/indice, en o antes de la fecha."""
    with conn.cursor() as cur:
        tabla = "cotizaciones" if tipo == "cotizacion" else "indices"
        columna = "venta" if tipo == "cotizacion" else "valor"
        cur.execute(
            f"""
            SELECT {columna} FROM {tabla}
            WHERE codigo = %s AND fecha <= %s
            ORDER BY fecha DESC LIMIT 1
            """,
            (codigo, fecha),
        )
        resultado = cur.fetchone()
        if resultado is None:
            raise ValueError(f"No hay datos en o antes de {fecha}")
        return float(resultado[0])


def calcular_ratio_directo(conn, serie_id, fecha_origen, fecha_destino):
    """Para series de nivel (UVA, dólar): ratio simple entre destino y origen."""
    codigo, tipo = obtener_codigo_y_tipo(conn, serie_id)
    valor_origen = obtener_valor_serie(conn, codigo, tipo, fecha_origen)
    valor_destino = obtener_valor_serie(conn, codigo, tipo, fecha_destino)
    return valor_destino / valor_origen

# TODO: no soporta fecha_destino < fecha_origen (bug conocido, arreglar) 
def calcular_inflacion_acumulada(conn, fecha_origen, fecha_destino):
    """
    Para inflación (variación % mensual): encadena los factores mensuales
    entre el mes siguiente al origen y el mes destino (inclusive).
    """
    codigo, _ = obtener_codigo_y_tipo(conn, "inflacion_mensual")
    fecha_origen_mes = fecha_origen.replace(day=1)
    fecha_destino_mes = fecha_destino.replace(day=1)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT valor FROM indices
            WHERE codigo = %s AND fecha > %s AND fecha <= %s
            ORDER BY fecha
            """,
            (codigo, fecha_origen_mes, fecha_destino_mes),
        )
        filas = cur.fetchall()

    if not filas:
        raise ValueError("No hay datos de inflación en el rango pedido")

    factor = 1.0
    for (valor,) in filas:
        factor *= (1 + float(valor) / 100)
    return factor


@app.get("/convertir")
def convertir(monto: float, fecha_origen: date, fecha_destino: date = None):
    if fecha_destino is None:
        fecha_destino = date.today()

    conn = get_conn()
    try:
        resultado = {}

        for serie_id in ["dolar_oficial", "dolar_mep", "uva"]:
            try:
                ratio = calcular_ratio_directo(conn, serie_id, fecha_origen, fecha_destino)
                resultado[serie_id] = round(monto * ratio, 2)
            except ValueError as e:
                resultado[serie_id] = {"error": str(e)}

        try:
            factor = calcular_inflacion_acumulada(conn, fecha_origen, fecha_destino)
            resultado["inflacion_mensual"] = round(monto * factor, 2)
        except ValueError as e:
            resultado["inflacion_mensual"] = {"error": str(e)}

        return {
            "monto_original": monto,
            "fecha_origen": fecha_origen.isoformat(),
            "fecha_destino": fecha_destino.isoformat(),
            "equivalentes": resultado,
        }
    finally:
        conn.close()
