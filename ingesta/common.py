import psycopg2
import requests

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "indexar",
    "user": "indexar",
    "password": "indexar_dev_pass",
}


def obtener_codigo_serie(conn, serie_id):
    """Busca el codigo numérico de una serie por su serie_id."""
    with conn.cursor() as cur:
        cur.execute("SELECT codigo FROM series WHERE serie_id = %s", (serie_id,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"No existe la serie '{serie_id}' en la tabla series")
        return row[0]


def get_paginado(url, params_base, extraer_items, limit=1000):
    """
    Pagina un endpoint del BCRA que usa limit/offset.

    - url: la URL del endpoint.
    - params_base: dict con los parámetros fijos (fechas, etc.), sin limit/offset.
    - extraer_items: función que recibe el JSON completo de una página
      y devuelve la lista de items de esa página (distinto según el endpoint).
    """
    todos_los_items = []
    offset = 0

    while True:
        params = {**params_base, "limit": limit, "offset": offset}
        response = requests.get(url, params=params, verify=False)
        if response.status_code != 200:
            print("Error del BCRA:", response.text)
        response.raise_for_status()
        data = response.json()

        items = extraer_items(data)
        todos_los_items.extend(items)
        print(f"  Página con offset={offset}: {len(items)} registros")

        if len(items) < limit:
            break

        offset += limit

    return todos_los_items
