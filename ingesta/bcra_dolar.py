from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2

from common import DB_CONFIG, obtener_codigo_serie, get_paginado

SERIE_ID = "dolar_oficial"
BCRA_URL = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD"


def obtener_datos_bcra(fecha_desde, fecha_hasta):
    params_base = {"fechaDesde": fecha_desde, "fechaHasta": fecha_hasta}
    return get_paginado(
        BCRA_URL,
        params_base,
        extraer_items=lambda data: data["results"],
    )


def insertar_cotizaciones(conn, codigo, registros):
    with conn.cursor() as cur:
        for registro in registros:
            fecha = registro["fecha"]
            detalle = registro["detalle"][0]
            venta = detalle["tipoCotizacion"]
            cur.execute(
                """
                INSERT INTO cotizaciones (codigo, fecha, venta, fuente)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo, fecha) DO NOTHING
                """,
                (codigo, fecha, venta, "BCRA"),
            )
    conn.commit()


if __name__ == "__main__":
    fecha_desde = "2014-01-01"
    fecha_hasta = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date().isoformat()

    print(f"Pidiendo datos del BCRA desde {fecha_desde} hasta {fecha_hasta}...")
    registros = obtener_datos_bcra(fecha_desde, fecha_hasta)
    print(f"Se recibieron {len(registros)} registros en total.")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        codigo = obtener_codigo_serie(conn, SERIE_ID)
        insertar_cotizaciones(conn, codigo, registros)
        print("Datos insertados correctamente.")
    finally:
        conn.close()
