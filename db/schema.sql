CREATE TABLE series (
    serie_id        TEXT PRIMARY KEY,
    codigo          SERIAL UNIQUE,
    nombre          TEXT NOT NULL,
    tipo            TEXT NOT NULL CHECK (tipo IN ('cotizacion', 'indice')),
    periodicidad    TEXT NOT NULL CHECK (periodicidad IN ('diaria', 'mensual')),
    fuente_default  TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE cotizaciones (
    codigo       INTEGER NOT NULL REFERENCES series(codigo),
    fecha        DATE NOT NULL,
    compra       NUMERIC(14,4),
    venta        NUMERIC(14,4) NOT NULL,
    fuente       TEXT NOT NULL,
    fecha_carga  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (codigo, fecha)
);

CREATE TABLE indices (
    codigo       INTEGER NOT NULL REFERENCES series(codigo),
    fecha        DATE NOT NULL,
    valor        NUMERIC(14,6) NOT NULL,
    fuente       TEXT NOT NULL,
    fecha_carga  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (codigo, fecha)
);

CREATE INDEX idx_cotizaciones_fecha ON cotizaciones (fecha);
CREATE INDEX idx_indices_fecha ON indices (fecha);
