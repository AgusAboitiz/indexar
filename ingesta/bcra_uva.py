from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2

from common import DB_CONFIG, obtener_codigo_serie, get_paginado

SERIE_ID = "uva"
BCRA_URL = "https://api.bcra.gob.ar/estadisticas/v4.0/Monetarias/31"


def obtener_datos_bcra(fecha_desde, fecha_hasta):
    params_base = {"desde": fecha_desde, "hasta": fecha_hasta}
    return get_paginado(
        BCRA_URL,
        params_base,
        extraer_items=lambda data: data["results"][0]["detalle"],
    )


def insertar_indices(conn, codigo, registros):
    with conn.cursor() as cur:
        for registro in registros:
            fecha = registro["fecha"]
            valor = registro["valor"]
            cur.execute(
                """
                INSERT INTO indices (codigo, fecha, valor, fuente)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo, fecha) DO NOTHING
                """,
                (codigo, fecha, valor, "BCRA"),
            )
    conn.commit()


if __name__ == "__main__":
    fecha_desde = "2016-03-31"  # UVA arranca acá según el BCRA (primerFechaInformada)
    fecha_hasta = datetime.now(ZoneInfo("America/Argentina/Buenos_Aires")).date().isoformat()

    print(f"Pidiendo datos del BCRA desde {fecha_desde} hasta {fecha_hasta}...")
    registros = obtener_datos_bcra(fecha_desde, fecha_hasta)
    print(f"Se recibieron {len(registros)} registros en total.")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        codigo = obtener_codigo_serie(conn, SERIE_ID)
        insertar_indices(conn, codigo, registros)
        print("Datos insertados correctamente.")
    finally:
        conn.close()
