from datetime import date

import psycopg2
import requests

from common import DB_CONFIG, obtener_codigo_serie

SERIE_ID = "inflacion_mensual"
URL = "https://api.argentinadatos.com/v1/finanzas/indices/inflacion"


def obtener_datos():
    response = requests.get(URL)
    response.raise_for_status()
    return response.json()


def primer_dia_del_mes(fecha_str):
    """Convierte una fecha 'YYYY-MM-DD' al primer día de ese mes."""
    fecha = date.fromisoformat(fecha_str)
    return fecha.replace(day=1)


def insertar_indices(conn, codigo, registros):
    with conn.cursor() as cur:
        for registro in registros:
            fecha = primer_dia_del_mes(registro["fecha"])
            valor = registro["valor"]
            cur.execute(
                """
                INSERT INTO indices (codigo, fecha, valor, fuente)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (codigo, fecha) DO NOTHING
                """,
                (codigo, fecha, valor, "ArgentinaDatos"),
            )
    conn.commit()


if __name__ == "__main__":
    print("Pidiendo datos de ArgentinaDatos (inflación mensual)...")
    registros = obtener_datos()
    print(f"Se recibieron {len(registros)} registros en total.")

    conn = psycopg2.connect(**DB_CONFIG)
    try:
        codigo = obtener_codigo_serie(conn, SERIE_ID)
        insertar_indices(conn, codigo, registros)
        print("Datos insertados correctamente.")
    finally:
        conn.close()
