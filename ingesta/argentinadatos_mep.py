import psycopg2
import requests

from common import DB_CONFIG, obtener_codigo_serie

SERIE_ID = "dolar_mep"
URL = "https://api.argentinadatos.com/v1/cotizaciones/dolares/bolsa"


def obtener_datos():
    response = requests.get(URL)
    response.raise_for_status()
    return response.json()


def insertar_cotizaciones(conn, codigo, registros):
    with conn.cursor() as cur:
        for registro in registros:
            fecha = registro["fecha"]
            compra = registro["compra"]
            venta = registro["venta"]
            cur.execute(
                """
                INSERT INTO cotizaciones (codigo, fecha, compra, venta, fuente)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (codigo, fecha) DO NOTHING
                """,
                (codigo, fecha, compra, venta, "ArgentinaDatos"),
            )
    conn.commit()


if __name__ == "__main__":
    print("Pidiendo datos de ArgentinaDatos (dólar MEP)...")
    registros = obtener_datos()
    print(f"Se recibieron {len(registros)} registros en total.")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        codigo = obtener_codigo_serie(conn, SERIE_ID)
        insertar_cotizaciones(conn, codigo, registros)
        print("Datos insertados correctamente.")
    finally:
        conn.close()
