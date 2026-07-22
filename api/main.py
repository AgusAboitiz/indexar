from datetime import date

import psycopg2
from cachetools import TTLCache
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "indexar",
    "user": "indexar",
    "password": "indexar_dev_pass",
}

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="IndexAR API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

cache = TTLCache(maxsize=1000, ttl=300)


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
    codigo, tipo = obtener_codigo_y_tipo(conn, serie_id)
    valor_origen = obtener_valor_serie(conn, codigo, tipo, fecha_origen)
    valor_destino = obtener_valor_serie(conn, codigo, tipo, fecha_destino)
    return valor_destino / valor_origen


def calcular_inflacion_acumulada(conn, fecha_origen, fecha_destino):
    codigo, _ = obtener_codigo_y_tipo(conn, "inflacion_mensual")

    hacia_atras = fecha_destino < fecha_origen
    inicio = min(fecha_origen, fecha_destino).replace(day=1)
    fin = max(fecha_origen, fecha_destino).replace(day=1)

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT valor FROM indices
            WHERE codigo = %s AND fecha > %s AND fecha <= %s
            ORDER BY fecha
            """,
            (codigo, inicio, fin),
        )
        filas = cur.fetchall()

    if not filas:
        raise ValueError("No hay datos de inflación en el rango pedido")

    factor = 1.0
    for (valor,) in filas:
        factor *= (1 + float(valor) / 100)

    return (1 / factor) if hacia_atras else factor


def calcular_conversion(monto, fecha_origen, fecha_destino):
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


@app.get("/convertir")
@limiter.limit("60/minute")
def convertir(request: Request, monto: float, fecha_origen: date, fecha_destino: str = None):
    if fecha_destino:
        try:
            fecha_destino = date.fromisoformat(fecha_destino)
        except ValueError:
            raise HTTPException(status_code=422, detail="fecha_destino invalida")
    else:
        fecha_destino = date.today()

    clave = (monto, fecha_origen, fecha_destino)
    if clave in cache:
        return cache[clave]

    respuesta = calcular_conversion(monto, fecha_origen, fecha_destino)
    cache[clave] = respuesta
    return respuesta


@app.get("/series")
@limiter.limit("60/minute")
def listar_series(request: Request):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT serie_id, nombre, tipo, periodicidad, fuente_default FROM series ORDER BY codigo"
            )
            filas = cur.fetchall()
        return [
            {
                "serie_id": f[0],
                "nombre": f[1],
                "tipo": f[2],
                "periodicidad": f[3],
                "fuente_default": f[4],
            }
            for f in filas
        ]
    finally:
        conn.close()


@app.get("/series/{serie_id}")
@limiter.limit("60/minute")
def obtener_serie(request: Request, serie_id: str, desde: date = None, hasta: date = None):
    conn = get_conn()
    try:
        try:
            codigo, tipo = obtener_codigo_y_tipo(conn, serie_id)
        except ValueError:
            raise HTTPException(status_code=404, detail=f"Serie '{serie_id}' no encontrada")

        tabla = "cotizaciones" if tipo == "cotizacion" else "indices"
        columnas = "fecha, compra, venta" if tipo == "cotizacion" else "fecha, valor"

        condiciones = ["codigo = %s"]
        params = [codigo]
        if desde is not None:
            condiciones.append("fecha >= %s")
            params.append(desde)
        if hasta is not None:
            condiciones.append("fecha <= %s")
            params.append(hasta)

        with conn.cursor() as cur:
            cur.execute(
                f"SELECT {columnas} FROM {tabla} WHERE {' AND '.join(condiciones)} ORDER BY fecha",
                params,
            )
            filas = cur.fetchall()

        if tipo == "cotizacion":
            datos = [
                {"fecha": f[0].isoformat(), "compra": float(f[1]) if f[1] is not None else None, "venta": float(f[2])}
                for f in filas
            ]
        else:
            datos = [{"fecha": f[0].isoformat(), "valor": float(f[1])} for f in filas]

        return {"serie_id": serie_id, "cantidad": len(datos), "datos": datos}
    finally:
        conn.close()
