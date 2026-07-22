import requests
import psycopg2
from datetime import datetime
from zoneinfo import ZoneInfo

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "indexar",
    "user": "indexar",
    "password": "indexar_dev_pass",
}

SERIE_ID = "dolar_oficial"
BCRA_URL = "https://api.bcra.gob.ar/estadisticascambiarias/v1.0/Cotizaciones/USD"


def obtener_datos_bcra(fecha_desde, fecha_hasta):
    todos_los_registros = []
    offset = 0
    limit = 1000

    while True:
        params = {
            "fechaDesde": fecha_desde,
            "fechaHasta": fecha_hasta,
            "limit": limit,
            "offset": offset,
        }
        response = requests.get(BCRA_URL, params=params, verify=False)
        if response.status_code != 200:
            print("Error del BCRA:", response.text)
        response.raise_for_status()
        data = response.json()
        registros = data["results"]

        todos_los_registros.extend(registros)
        print(f"  Página con offset={offset}: {len(registros)} registros")

        if len(registros) < limit:
            break

        offset += limit

    return todos_los_registros


def obtener_codigo_serie(conn, serie_id):
    with conn.cursor() as cur:
        cur.execute("SELECT codigo FROM series WHERE serie_id = %s", (serie_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No existe la serie '{serie_id}' en la tabla series")
        return row[0]


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
    fecha_desde = "1992-01-02"
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
