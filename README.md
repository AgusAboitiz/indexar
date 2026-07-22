# IndexAR

Conversor de unidades de valor argentino. Permite convertir un monto entre distintas
"unidades" monetarias y de ajuste (peso ajustado por inflación IPC, UVA, dólar oficial,
dólar MEP) entre dos fechas, y expone series históricas de cada una a través de una
API pública.

## Stack

- Python 3.14
- FastAPI
- Uvicorn
- PostgreSQL 16
- Docker Compose (para levantar la base de datos local)
- slowapi (rate limiting)
- cachetools (cache en memoria de resultados de conversión)

## Fuentes de datos

| Serie | Fuente | Datos disponibles desde |
|---|---|---|
| Dólar oficial | BCRA | 2014-04-14 |
| UVA | BCRA | 2016-03-31 |
| Dólar MEP | ArgentinaDatos | 2018-10-29 |
| Inflación mensual (IPC) | ArgentinaDatos | 1943-03-01 |

## Cómo levantar el entorno local

1. Clonar el repositorio:

   ```bash
   git clone <url-del-repo>
   cd indexar
   ```

2. Crear el entorno virtual:

   ```bash
   python3.14 -m venv venv
   ```

3. Activar el entorno virtual:

   ```bash
   source venv/bin/activate       # Linux/macOS/WSL
   venv\Scripts\activate          # Windows (cmd/PowerShell)
   ```

4. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

5. Levantar Postgres con Docker Compose:

   ```bash
   docker compose up -d
   ```

6. Aplicar el esquema y los datos semilla:

   ```bash
   docker exec -i indexar_db psql -U indexar -d indexar < db/schema.sql
   docker exec -i indexar_db psql -U indexar -d indexar < db/seed.sql
   ```

7. Correr los scripts de ingesta (carga las series históricas):

   ```bash
   python ingesta/bcra_dolar.py
   python ingesta/bcra_uva.py
   python ingesta/argentinadatos_mep.py
   python ingesta/argentinadatos_inflacion.py
   ```

8. Levantar la API:

   ```bash
   uvicorn api.main:app --reload
   ```

## Endpoints

### `GET /series`

Lista todas las series disponibles.

Respuesta: array de objetos con `serie_id`, `nombre`, `tipo`, `periodicidad` y
`fuente_default`.

### `GET /series/{serie_id}`

Devuelve los datos históricos de una serie puntual.

Parámetros opcionales de query:

- `desde` (fecha): filtra desde esta fecha (inclusive).
- `hasta` (fecha): filtra hasta esta fecha (inclusive).

Si `serie_id` no existe, responde `404`.

### `GET /convertir`

Convierte un monto entre las distintas unidades (dólar oficial, dólar MEP, UVA e
inflación mensual acumulada) entre dos fechas.

Parámetros de query:

- `monto` (float, requerido)
- `fecha_origen` (fecha, requerido)
- `fecha_destino` (fecha, opcional — si no se envía, usa la fecha de hoy)

## Rate limiting

Los tres endpoints tienen un límite de **60 requests por minuto por IP**.

## Colección de Postman

Hay una colección lista para importar en [`docs/IndexAR.postman_collection.json`](docs/IndexAR.postman_collection.json).

## Limitaciones conocidas

- No hay automatización de actualización periódica de los datos todavía; los scripts
  de ingesta se corren manualmente.
- La contraseña de Postgres está hardcodeada en el código y en `docker-compose.yml`.
  Es válida solo para desarrollo local, no para producción.
- No hay cobertura de dólar oficial previa a 2014.

## Roadmap

- **v1.1:** modo de salario real usando RIPTE como unidad adicional.
- **v2:** comparación regional con Brasil, Chile y Uruguay.
